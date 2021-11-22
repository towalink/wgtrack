# -*- coding: utf-8 -*-

"""Class for executing commands on the system"""

import logging
import shlex
import subprocess


logger = logging.getLogger(__name__);


class ExecHelper(object):
    """Class for executing commands on the system"""
    _os_id = None # cache for storing the detected operating system family identifier
    
    @property
    def os_id(self):
        if self._os_id is None:
            with open('/etc/os-release', 'r') as f:            
                line = True            
                while line:                
                    line = f.readline()
                    parts = line.partition('=')
                    if parts[0] == 'ID':
                        self._os_id = parts[2].strip()
                        break
        return self._os_id
    
    def execute(self, command, suppressoutput=False, suppresserrors=False):
        """Execute a command"""
        args = shlex.split(command)
        nsp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = nsp.communicate()
        if err is not None:
            err = err.decode('utf8')
            if not suppresserrors and (len(err) > 0):
                logger.error(err)
        out = out.decode('utf8')
        if not suppressoutput and (len(out) > 0):
            print(out)
        nsp.wait()
        return out, err, nsp.returncode

    def service_is_active(self, service):
        """Checks whether the given service is active on the system"""
        command = f'systemctl status "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
            # ret: (0: active)(3: not active)(4: service not found)
        except Exception as e:
            logger.error(f'Exception when checking for active service: [{e}]')
            return False
        return (ret==0)

    def start_service(self, service):
        """Starts the given service"""
        if self.os_id == 'alpine':
            command = f'rc-service "{service}" start'
        else:
            command = f'systemctl start "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
        except Exception as e:
            logger.error(f'Exception when starting service: [{e}]')

    def stop_service(self, service):
        """Stops the given service"""
        if self.os_id == 'alpine':
            command = f'rc-service "{service}" stop'
        else:
            command = f'systemctl stop "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
        except Exception as e:
            logger.error(f'Exception when stopping service: [{e}]')

    def reload_service(self, service):
        """Reloads the given service"""
        if self.os_id == 'alpine':
            command = f'rc-service "{service}" restart'
        else:
            command = f'systemctl reload "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
        except Exception as e:
            logger.error(f'Exception when reloading service: [{e}]')

    def restart_service(self, service):
        """Restarts the given service"""
        if self.os_id == 'alpine':
            command = f'rc-service "{service}" restart'
        else:
            command = f'systemctl restart "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
        except Exception as e:
            logger.error(f'Exception when reloading service: [{e}]')

    def enable_service(self, service):
        """Enables the given service"""
        if self.os_id == 'alpine':
            command = f'rc-update add "{service}"'
        else:
            command = f'systemctl enable "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
        except Exception as e:
            logger.error(f'Exception when enabling service: [{e}]')

    def disable_service(self, service):
        """Disable the given service"""
        if self.os_id == 'alpine':
            command = f'rc-update del "{service}"'
        else:
            command = f'systemctl disable "{service}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
        except Exception as e:
            logger.error(f'Exception when disabling service: [{e}]')

    def run_wgquick(self, task, interface):
        """Runs "wg-quick <task> <interface>"""
        command = f'wg-quick {task} "{interface}"'
        try:
            out, err, ret = self.execute(command, suppressoutput=True, suppresserrors=True)
            if ret > 0:
                logger.error(err)
                raise Exception('wg-quick returned an error')
        except Exception as e:
            logger.error(f'Exception when running wg-quick: [{e}]')


if __name__ == '__main__':
    eh = ExecHelper()
    print(eh.service_is_active('ssh'))
    print(eh.service_is_active('autossh-ssh1'))
    print(eh.service_is_active('salt-minion'))
