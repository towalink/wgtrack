#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import textwrap

from . import exechelper


def is_root():
    """Returns whether this script is run with user id 0 (root)"""
    return os.getuid() == 0
    
def check_wg():
    """Check whether the wg tool is present"""
    return os.path.isfile('/usr/bin/wg')

def get_startupscript_openrc():
    """Get an openrc startup script for wgtrack"""
    template = r'''
        #!/sbin/openrc-run
        
        depend() {
            need net
        }
        
        name=$RC_SVCNAME
        command="wgtrack"
        command_args=""
        pidfile="/run/$RC_SVCNAME.pid"
        command_background="yes"
        stopsig="SIGTERM"
        start_stop_daemon_args="--stdout /var/log/wgtrack.log --stderr /var/log/wgtrack.err"
        '''
    template = textwrap.dedent(template).lstrip()
    return template

def get_startupscript_systemd():
    """Get a systemd service for wgtrack"""
    template = r'''
        [Unit]
        Description=wgtrack service
        After=network-online.target
        Wants=network-online.target
        
        [Service]
        Type=simple
        ExecStart=wgtrack
        StandardOutput=append:/var/log/wgtrack.log
        StandardError=inherit
        
        [Install]
        WantedBy=multi-user.target
        '''
    template = textwrap.dedent(template).lstrip()
    return template

def install_startupscript_openrc():
    """Install a startup script for wgtrack to /etc/init.d"""
    filename = '/etc/init.d/wgtrack'
    with open(filename, 'w') as f:
        f.write(get_startupscript_openrc())
    os.chmod(filename, 0o700)

def install_startupscript_systemd(eh):
    """Install a systemd service for wgtrack"""
    if os.path.isdir('/etc/systemd/system'):
        with open('/etc/systemd/system/wgtrack.service', 'w') as systemd_file:
            systemd_file.write(get_startupscript_systemd())  
        eh.execute('systemctl daemon-reload', suppressoutput=True, suppresserrors=True)
        return True
    else:
        return False

def setup_environment(install=True):
    """Environment setup assistant"""
    if not is_root():
        print('Error: this needs to be done as root user. Aborting.')
        exit(1)
    eh = exechelper.ExecHelper()
    if install:
        if not check_wg():
            print('Error: Wireguard (wg) is not available on this system. Aborting.')
            exit(1)
        if eh.os_id == 'alpine':
            # Create and install openrc startup script
            install_startupscript_openrc()
        else:
            # Create and install systemd service
            if not install_startupscript_systemd(eh):
                print('Error: this is neither running on Alpine nor has systemd been found')
                exit(1)
        eh.start_service('wgtrack')
        eh.enable_service('wgtrack')
    else:    
        eh.disable_service('wgtrack')
        eh.stop_service('wgtrack')
        try:
            if eh.os_id == 'alpine':
                os.remove('/etc/init.d/wgtrack')
            else:
                os.remove('/etc/systemd/system/wgtrack.service')
                eh.execute('systemctl daemon-reload', suppressoutput=True, suppresserrors=True)
        except FileNotFoundError:
            pass


if __name__ == '__main__':
    setup_environment()
