#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""wgtrack.py: A tool for tracking WireGuard tunnels and updating endpoints on changing DNS mappings"""

"""
Towalink
Copyright (C) 2020 Dirk Henrici

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

You can be released from the requirements of the license by purchasing
a commercial license.
"""

__author__ = "Dirk Henrici"
__license__ = "AGPL3" # + author has right to release in parallel under different licenses
__email__ = "towalink.wgtrack@henrici.name"


import getopt
import logging
import os
import sys

from . import config
from . import eventprocessor


def usage():
    """Show information on command line arguments"""
    print('Usage: %s [-?|--help] [-l|--loglevel debug|info|error] [-c|--config <config file>]' % sys.argv[0])
    print('Track WireGuard tunnels')
    print()
    print('  -?, --help                        show program usage')
    print('  -l, --loglevel debug|info|error   set the level of debug information')
    print('                                    default: info')
    print('  -c, --config <config file>        location of the configuration file')
    print('                                    default: /etc/wgtrack.conf')
    print()
    print('Example: %s --loglevel debug --config /etc/alternative_wgtrack.conf' % sys.argv[0])
    print()

def show_usage_and_exit():
    """Show information on command line arguments and exit with error"""
    print()
    usage()
    sys.exit(2)

def parseopts():
    """Check and parse the command line arguments"""
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'c:l:?', ['help', 'conf=', 'loglevel='])
    except getopt.GetoptError as ex:
        # print help information and exit:
        print(ex)  # will print something like "option -a not recognized"
        show_usage_and_exit()
    configfile = '/etc/wgtrack.conf'
    loglevel = None
    for o, a in opts:
        if o in ('-?', '--help'):
            show_usage_and_exit()
        elif o in ('-c', '--config'):
            if os.path.isfile(a):
                configfile = a
            else:
                print('the specified configfile is not present')
                show_usage_and_exit()
        elif o in ('-l', '--loglevel'):
            a = a.lower()
            if a == 'debug':
              loglevel = logging.DEBUG
            elif a == 'info':
              loglevel = logging.INFO
            elif a == 'error':
              loglevel = logging.ERROR
            else:
                print('invalid loglevel')
                show_usage_and_exit()
        else:
            assert False, 'unhandled option'
    if len(args) > 0:
        print('unexpected command line arguments')
        show_usage_and_exit()
    return configfile, loglevel

def main():
    '''Application entry point'''
    configfile, loglevel = parseopts()
    cfg = config.Config(configfile)
    cfg.loglevel = loglevel # set loglevel if not None
    logging.basicConfig(format='%(asctime)s %(levelname)s %(module)s: %(message)s', level=cfg.loglevel)
    eventprocessor.run(cfg)


if __name__ == "__main__":
    main()
