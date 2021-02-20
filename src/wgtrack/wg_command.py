# -*- coding: utf-8 -*-

"""Class that uses the 'wg show' command to get the status of WireGuard as Python dictionaries"""


import collections
import logging
import pprint
import shlex
import subprocess
import time


logger = logging.getLogger(__name__);


class WireguardCommand():
    '''Class for parsing the output of WireGuard's dump command'''

    def __init__(self, interface='all'):
        '''Constructor'''
        self.interface = interface
        self.clear_data()

    def clear_data(self):
        '''Clears all data so that it can be set anew'''
        self.data = collections.defaultdict(dict)

    def check_handshake(self, latest_handshake, persistent_keepalive):
        '''Checks whether handshake succeeded as expected'''
        if latest_handshake == 0: # no handshake took place successfully yet
            return None, 'none'
        if persistent_keepalive == None: # convert this parameter to an integer
            persistent_keepalive = 0
        delta = int(time.time()) - latest_handshake # delta in seconds
        # Based on a forum: 2 minutes + keepalive + 2s (error margin)
        # However, this does not seem to match https://www.wireguard.com/papers/wireguard.pdf
        if delta <= 120:
            handshake_status = 'ok'
        elif delta <= 135: # 135 is used by the WireGuard reresolve-dns.sh script
            handshake_status = 'pending'
        elif delta <= 180:
            handshake_status = 'retrying'
        else:
            handshake_status = 'failed'
        return delta, handshake_status

    def execute(self, command, suppressoutput=False, suppresserrors=False):
        '''Execute a command'''
        args = shlex.split(command);
        nsp = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE);
        out, err = nsp.communicate();
        if err is not None:
            err = err.decode('utf8');
            if not suppresserrors and (len(err) > 0):
                logger.error(err);
        out = out.decode('utf8');
        if not suppressoutput and (len(out) > 0):
            print(out);       
        nsp.wait();
        return out, err;

    def execute_wg_set(self, interface, peer, attr, value, suppressoutput=True, suppresserrors=False):
        '''Execute the WireGuard command to set the provided attribute'''
        command = 'wg set "{0}"'.format(interface)
        if peer is not None:
            command += ' peer "{0}"'.format(peer)
        command += ' {0} "{1}"'.format(attr, value)
        try:
            out, err = self.execute(command, suppressoutput, suppresserrors)
            if len(err) > 0:
                logger.error('Error executing WireGuard set command: {0}'.format(err))
            else:
                return out
        except Exception as e:
            logger.error('Exception when execution WireGuard set command failed: [{0}]'.format(e))
        return None

    def execute_wg_show(self, suppressoutput=True, suppresserrors=False):
        '''Return the output of "wg show <if> all"'''
        try:
            out, err = self.execute('wg show {0} dump'.format(self.interface), suppressoutput, suppresserrors)
            if len(err) > 0:
                logger.error('Error executing WireGuard command: {0}'.format(err))
            else:
                return out
        except FileNotFoundError:
            logger.error('WireGuard command not found in search path. Is WireGuard installed on this system?')
        return None
        
    def parse_wg_output(self, output):
        '''Parses the given output of the WireGuard command and stores it'''
        if output is None:
            return
        previous_interface = ''
        for line in output.splitlines():
            items = [item for item in line.split('\t')]
            if self.interface == 'all':
                interface = items.pop(0)
            else:
                interface = self.interface
            if interface != previous_interface: # new section with interface information?
                previous_interface = interface
                items = dict(zip(['private-key', 'public-key', 'listen-port', 'fwmark'], items))
                if items['fwmark'] == 'off':
                    items['fwmark'] = None
                items['listen-port'] = int(items['listen-port'])
                if items['private-key'] == '(none)':
                    items['private-key'] = None
                if items['public-key'] == '(none)':
                    items['public-key'] = None
                self.data[interface] = {**self.data.get(interface, dict()), **items} # merge dictionaries
                self.data[interface]['peers'] = self.data[interface].get('peers', dict()) # make sure that peers dictionary exists
            else: # peer
                peer = items.pop(0)
                peerdata = dict(zip(['preshared-key', 'endpoint', 'allowed-ips', 'latest-handshake', 'transfer-rx', 'transfer-tx', 'persistent-keepalive'], items))
                peerdata['allowed-ips'] = peerdata['allowed-ips'].split(',')
                if peerdata['preshared-key'] == '(none)':
                    peerdata['preshared-key'] = None
                if peerdata['persistent-keepalive'] == 'off':
                    peerdata['persistent-keepalive'] = None
                peerdata = { k: int(v) if (k in ['latest-handshake', 'transfer-rx', 'transfer-tx', 'persistent-keepalive']) and (v is not None) else v
                             for k, v in peerdata.items() } # numeric strings to integer
                peerdata['latest-handshake-seconds'], peerdata['handshake-status'] = self.check_handshake(peerdata['latest-handshake'], peerdata['persistent-keepalive'])    
                peerdata['timestamp'] = time.time()
                self.data[interface]['peers'][peer] = {**self.data[interface]['peers'].get(peer, dict()), **peerdata} # merge dictionaries

    def retrieve_wireguard_data(self, data=None):
        '''Sets the local data based on output of WireGuard command to be executed'''
        output = self.execute_wg_show()
        if data is None:
            self.clear_data()
        else:
            self.data = data
        self.parse_wg_output(output)

    @property
    def wgdata():
        return self.data

    def get_interfaces(self,):
        '''Returns the list of interfaces (as an iterator)'''
        return self.data.keys()
        
    def get_interfacedata(self, interface):
        '''Returns the data of the given interface as dictionary'''
        return self.data.get(interface)
        
    def get_peerdata(self, interface):
        '''Returns the data of the peers of the given interface as dictionary'''
        return self.data.get(interface, dict()).get('peers')


if __name__ == '__main__':
    wg = WireguardCommand('all')
    wg.retrieve_wireguard_data()
    pprint.pprint(wg.get_interfaces())
    pprint.pprint(wg.get_interfacedata('wg_1'))
    pprint.pprint(wg.get_peerdata('wg_1'))
