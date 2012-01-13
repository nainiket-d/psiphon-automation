#!/usr/bin/python
#
# Copyright (c) 2011, Psiphon Inc.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import re
import textwrap
import gzip
import csv
import datetime
import collections
import time
import psycopg2

import psi_ssh
import psi_ops
import psi_ops_stats_credentials


HOST_LOG_FILENAME_PATTERN = 'psiphonv.log*'
LOCAL_LOG_ROOT = os.path.join(os.path.abspath('.'), 'logs')
PSI_OPS_DB_FILENAME = os.path.join(os.path.abspath('.'), 'psi_ops_stats.dat')


# Stats database schema consists of one table per event type. The tables
# have a column per log line field.
#
# The entire log line is considered to be unique. This is how we handle pulling
# down the same log file again: duplicate lines are discarded. This logic also
# handles the unlikely case where our SFTP pull happens in the middle of a
# log rotation, in which case we may pull the same log entries down twice in
# two different file names.
#
# The uniqueness assumption depends on a high resolution timestamp as it's
# likely that there will be multiple handshake events in the same second on
# the same server from the same region and client build.

# Example log file entries:

'''
2011-06-28T13:14:04.000000-07:00 host1 psiphonv: started 192.168.1.101
2011-06-28T13:15:59.000000-07:00 host1 psiphonv: handshake 192.168.1.101 CA DA77176D642E66FB 1F277F0BD58BB84D 1
2011-06-28T13:15:59.000000-07:00 host1 psiphonv: discovery 192.168.1.101 CA DA77176D642E66FB 1F277F0BD58BB84D 1 192.168.1.102 0
2011-06-28T13:16:00.000000-07:00 host1 psiphonv: download 192.168.1.101 CA DA77176D642E66FB 1F277F0BD58BB84D 2
2011-06-28T13:16:06.000000-07:00 host1 psiphonv: connected 192.168.1.101 CA DA77176D642E66FB 1F277F0BD58BB84D 2 10.1.0.2
2011-06-28T13:16:12.000000-07:00 host1 psiphonv: disconnected 10.1.0.2
'''

# Log line parser looks for space delimited fields. Every log line has a
# timestamp, host ID, and event type. The schema array defines the additional
# fields expected for each valid event type.

LOG_LINE_PATTERN = '([\dT\.:\+-]+) ([\w-]+) psiphonv: (\w+) (.+)'

LOG_ENTRY_COMMON_FIELDS = ('timestamp', 'host_id')

LOG_EVENT_TYPE_SCHEMA = {
    'started' :         ('server_id',),
    'handshake' :       ('server_id',
                         'client_region',
                         'propagation_channel_id',
                         'sponsor_id',
                         'client_version'),
    'discovery' :       ('server_id',
                         'client_region',
                         'propagation_channel_id',
                         'sponsor_id',
                         'client_version',
                         'discovery_server_id',
                         'client_unknown'),
    'connected' :       ('server_id',
                         'client_region',
                         'propagation_channel_id',
                         'sponsor_id',
                         'client_version',
                         'relay_protocol',
                         'session_id'),
    'failed' :          ('server_id',
                         'client_region',
                         'propagation_channel_id',
                         'sponsor_id',
                         'client_version',
                         'relay_protocol',
                         'error_code'),
    'download' :        ('server_id',
                         'client_region',
                         'propagation_channel_id',
                         'sponsor_id',
                         'client_version'),
    'disconnected' :    ('relay_protocol',
                         'session_id'),
    'status' :          ('relay_protocol',
                         'session_id')}


def iso8601_to_utc(timestamp):
    localized_datetime = datetime.datetime.strptime(timestamp[:26], '%Y-%m-%dT%H:%M:%S.%f')
    timezone_delta = datetime.timedelta(
                                hours = int(timestamp[-6:-3]),
                                minutes = int(timestamp[-2:]))
    return (localized_datetime - timezone_delta).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def process_stats(host, servers, db_cur, error_file):

    print 'process stats from host %s...' % (host.id,)

    server_ip_address_to_id = {}
    for server in servers:
        server_ip_address_to_id[server.ip_address] = server.id

    line_re = re.compile(LOG_LINE_PATTERN)

    # Download each log file from the host, parse each line and insert
    # log entries into database.

    directory = os.path.join(LOCAL_LOG_ROOT, host.id)
    for filename in os.listdir(directory):
        if re.match(HOST_LOG_FILENAME_PATTERN, filename):
            with open(os.path.join(directory, filename)) as file:
                print 'processing %s...' % (filename,)
                for line in file.read().split('\n'):
                    match = line_re.match(line)
                    if (not match or
                        not LOG_EVENT_TYPE_SCHEMA.has_key(match.group(3))):
                        err = 'unexpected log line pattern: %s' % (line,)
                        error_file.write(err + '\n')
                        continue
                    # Note: We convert timestamps here to UTC so that they can all be rationally compared without
                    #       taking the timezone into consideration. This eases matching of outbound statistics
                    #       (and any other records that may not have consistent timezone info) to sessions.
                    timestamp = iso8601_to_utc(match.group(1))
                    host_id = match.group(2)
                    event_type = match.group(3)
                    event_values = match.group(4).split()
                    event_fields = LOG_EVENT_TYPE_SCHEMA[event_type]
                    if len(event_values) != len(event_fields):
                        err = 'invalid log line fields %s' % (line,)
                        error_file.write(err + '\n')
                        continue
                    field_names = LOG_ENTRY_COMMON_FIELDS + event_fields
                    field_values = [timestamp, host_id] + event_values
                    # Replace server IP addresses with server IDs in
                    # stats to keep IP addresses confidental in reporting.
                    assert(len(field_names) == len(field_values))
                    for index, name in enumerate(field_names):
                        if name.find('server_id') != -1:
                            field_values[index] = server_ip_address_to_id[
                                                    field_values[index]]
                    # SQL injection note: the table name isn't parameterized
                    # and comes from log file data, but it's implicitly
                    # validated by hash table lookups
                    command = 'insert into %s (%s) select %s where not exists (select 1 from %s where %s)' % (
                                    event_type,
                                    ', '.join(field_names),
                                    ', '.join(['%s']*len(field_values)),
                                    event_type,
                                    ' and '.join(['%s = %%s' % x for x in field_names]))

                    db_cur.execute(command, field_values + field_values)


if __name__ == "__main__":

    start_time = time.time()

    psinet = psi_ops.PsiphonNetwork.load_from_file(PSI_OPS_DB_FILENAME, lock_file=True)

    db_conn = psycopg2.connect(
        'dbname=%s user=%s password=%s' % (
            psi_ops_stats_credentials.POSTGRES_DBNAME,
            psi_ops_stats_credentials.POSTGRES_USER,
            psi_ops_stats_credentials.POSTGRES_PASSWORD))

    # Note: truncating error file
    error_file = open('process_stats.err', 'w')

    hosts = psinet.get_hosts()
    servers = psinet.get_servers()

    try:
        for host in hosts:
            db_cur = db_conn.cursor()
            process_stats(host, servers, db_cur, error_file)
            db_cur.close()
            db_conn.commit()
    finally:
        error_file.close()
        db_conn.close()

    print 'elapsed time: %fs' % (time.time()-start_time,)