## Copyright (c) 2012, Psiphon Inc.
## All rights reserved.
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

<%!
  import yaml
  from operator import itemgetter
  import utils
%>

<%
  sys_info = data['SystemInformation']
  server_responses = data['ServerResponseCheck']
  diagnostic_history = data['DiagnosticHistory']
  status_history = data['StatusHistory']
%>

<style>
  th {
    text-align: right;
    padding-right: 0.3em;
  }

  .good {
    color: green;
  }

  .warn {
    color: orange;
  }

  .bad {
    color: red;
  }

  .status-entry, .diagnostic-entry {
    margin-bottom: 0.3em;
  }

  .status-latter-line {
    margin-left: 2em;
  }

  .timestamp {
    font-size: 0.8em;
    font-family: monospace;
  }

  .status-entry-id, .diagnostic-entry-msg {
    font-weight: bold;
  }

  .priority-info {
    color: green;
  }

  .priority-error {
    color: red;
  }

  .diagnostic-entry-msg {
    color: purple;
  }

  hr {
    width: 80%;
    border: 0;
    background-color: lightGray;
    height: 1px;
  }

  /* Make integers easier to visually compare. */
  .intcompare {
    text-align: right;
    font-family: monospace;
  }

  .server-response-checks .separated th,
  .server-response-checks .separated td {
    border-top: dotted thin gray;
  }
</style>

##
## System Info
##

<h1>System Info</h1>

## Display more human-friendly field names
<%def name="sys_info_key_map(key)">
  <%
  map = {
          'BRAND': 'Brand',
          'CPU_ABI': 'CPU ABI',
          'MANUFACTURER': 'Manufacturer',
          'MODEL': 'Model',
          'TAGS': 'Tags',
          'VERSION__CODENAME': 'Ver. Codename',
          'VERSION__RELEASE': 'OS Version',
          'VERSION__SDK_INT': 'SDK Version',
          'isRooted': 'Rooted',
          'CLIENT_VERSION': 'Client Version',
          'PROPAGATION_CHANNEL_ID': 'Prop. Channel',
          'SPONSOR_ID': 'Sponsor'
        }
  %>
  % if key in map:
    ${map[key]}
  % else:
    ${key}
  % endif
</%def>

<%def name="sys_info_row(key, val)">
  <tr>
    <th>${sys_info_key_map(key)}</th>
    <td>${val}</td>
  </tr>
</%def>

<h2>Build Info</h2>
<table>
  % for k, v in sorted(sys_info['Build'].items()):
    ${sys_info_row(k, v)}
  % endfor
  ${sys_info_row('isRooted', sys_info['isRooted'])}
</table>

<h2>Psiphon Info</h2>
<table>
  % for k, v in sorted(sys_info['psiphonEmbeddedValues'].items()):
    ${sys_info_row(k, v)}
  % endfor
</table>

##
## Server Response Checks
##

<%def name="server_response_row(entry, last_timestamp)">
  <%
    # Put a separator between entries that are separated in time.
    timestamp_separated_class = ''
    if last_timestamp and 'timestamp' in entry:
        if (entry['timestamp'] - last_timestamp).total_seconds() > 20:
            timestamp_separated_class = 'separated'

    ping_class = 'good'
    ping_str = '%dms' % entry['responseTime']
    if not entry['responded'] or entry['responseTime'] < 0:
        ping_class = 'bad'
        ping_str = 'none'
    elif entry['responseTime'] > 2000:
        ping_class = 'warn'
  %>
  <tr class="${timestamp_separated_class}">
    <th>${entry['ipAddress']}</th>
    <td class="intcompare ${ping_class}">${ping_str}</td>
    <td class="timestamp">${entry['timestamp'] if 'timestamp' in entry else ''}</td>
  </tr>
</%def>

<h1>Server Response Checks</h1>
<table class="server-response-checks">
  <% last_timestamp = None %>
  % for entry in server_responses:
    ${server_response_row(entry, last_timestamp)}
    <% last_timestamp = entry['timestamp'] if 'timestamp' in entry else None %>
  % endfor
</table>

##
## Status History and Diagnostic History
##

<%def name="status_history_row(entry, last_timestamp)">
  <%
    timestamp_diff_secs, timestamp_diff_str = utils.get_timestamp_diff(last_timestamp, entry['timestamp'])

    # These values come from the Java definitions for Log.VERBOSE, etc.
    PRIORITY_CLASSES = {
        2: 'priority-verbose',
        3: 'priority-debug',
        4: 'priority-info',
        5: 'priority-warn',
        6: 'priority-error',
        7: 'priority-assert' }
    priority_class = ''
    if 'priority' in entry and entry['priority'] in PRIORITY_CLASSES:
        priority_class = PRIORITY_CLASSES[entry['priority']]
  %>

  ## Put a separator between entries that are separated in time.
  % if timestamp_diff_secs > 10:
    <hr>
  % endif

  <div class="status-entry">
    <div class="status-first-line">
      <span class="timestamp">${utils.timestamp_display(entry['timestamp'])} [+${timestamp_diff_str}s]</span>

      <span class="status-entry-id ${priority_class}">${entry['id']}</span>

      <span class="format-args">
        % if entry['formatArgs'] and len(entry['formatArgs']) == 1:
          ${entry['formatArgs'][0]}
        % elif entry['formatArgs'] and len(entry['formatArgs']) > 1:
          ${repr(entry['formatArgs'])}
        %endif
        </span>
    </div>

    % if entry['throwable']:
      <div class="status-latter-line">
        <pre>${yaml.dump(entry['throwable'], default_flow_style=False)}</pre>
      </div>
    %endif
  </div>
</%def>

<%def name="diagnostic_history_row(entry, last_timestamp)">
  <%
    timestamp_diff_secs, timestamp_diff_str = utils.get_timestamp_diff(last_timestamp, entry['timestamp'])
  %>

  ## Put a separator between entries that are separated in time.
  % if timestamp_diff_secs > 10:
    <hr>
  % endif

  <div class="diagnostic-entry">
    <span class="timestamp">${utils.timestamp_display(entry['timestamp'])} [+${timestamp_diff_str}s]</span>

    <span class="diagnostic-entry-msg">${entry['msg']}</span>

    ## We special-case some of the common diagnostic entries
    % if entry['msg'] == 'ConnectingServer':
      <span>${entry['data']['ipAddress']}</span>
    % elif entry['msg'] == 'ServerResponseCheck':
      <%
        ping_class = 'good'
        ping_value = int(entry['data']['responseTime'])
        ping_str = '%dms' % ping_value
        if entry['data']['responded'] == 'No' or ping_value < 0:
          ping_class = 'bad'
          ping_str = 'none'
        elif ping_value > 2000:
          ping_class = 'warn'
      %>
      <span class="intcompare ${ping_class}">${ping_str}</span>
      <span>${entry['data']['ipAddress']}</span>
    % else:
      <span>${repr(entry['data'])}</span>
    % endif
  </div>
</%def>

<h1>Status History</h1>
<%
  last_timestamp = None

  # We want the diagnostic entries to appear inline chronologically with the
  # status entries, so we'll merge the lists and process them together.
  status_diagnostic_history = status_history
  if diagnostic_history:
      status_diagnostic_history += diagnostic_history
  status_diagnostic_history = sorted(status_diagnostic_history,
                                     key=itemgetter('timestamp'))
%>
% for entry in status_diagnostic_history:
  % if 'formatArgs' in entry:
    ${status_history_row(entry, last_timestamp)}
  % else:
    ${diagnostic_history_row(entry, last_timestamp)}
  % endif
  <% last_timestamp = entry['timestamp'] %>
% endfor
