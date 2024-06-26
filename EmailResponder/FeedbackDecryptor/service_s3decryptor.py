#!/usr/bin/env python

# Copyright (c) 2012, Psiphon Inc.
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

import signal
import threading
import sys
import time

import logger
import s3decryptor


def _do_exit(signum, frame):
    logger.log('Shutdown signalled')
    s3decryptor.terminate = True
    # Give the workers time to shut down cleanly
    sys.exit(0)


def main():
    logger.log('Starting up')

    signal.signal(signal.SIGTERM, _do_exit)

    try:
        s3decryptor.go()
    except Exception:
        logger.exception()

    logger.log('Shutting down')


if __name__ == '__main__':
    main()
