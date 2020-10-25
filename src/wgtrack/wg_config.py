# -*- coding: utf-8 -*-

"""Class that parses the Wireguard configuration files as Python dictionaries"""

import collections
import logging
import os
import pprint


logger = logging.getLogger(__name__);


class WireguardConfig():
    '''Class for parsing the WireGuard config files'''

    def __init__(self):
        '''Constructor'''
        self.configpath = '/etc/wireguard'
        self.clear_data()

    def clear_data(self):
        '''Clears all data so that it can be set anew'''
        self.data = collections.defaultdict(dict)
        
    def parse_wg_config(self, interface, prefix=''):
        '''Parses the given WireGuard config and stores it'''
        
        def section2dict(section_lines, prefix):
            '''Converts the lines of a section into a dictionary'''
            result = dict()
            for line in section_lines:
                k,_, v = line.partition('=')
                k = k.strip().lower()
                v = v.strip()
                if k == 'allowedips':
                    k = 'allowed-ips'
                    v = v.replace(' ', '').split(',')
                elif k == 'persistentkeepalive':
                    k = 'persistent-keepalive'
                elif k == 'preshared-key':
                    k = 'preshared-key'
                elif k == 'privatekey':
                    k = 'private-key'
                elif k == 'publickey':
                    k = 'public-key'
                v = int(v) if k in ['persistent-keepalive'] else v # convert strings to integers for certain attributes
                result[prefix + k] = v
            return result
        
        # Note: ConfigParser cannot be used since it does not support duplicate "[Peer]" sections; thus do it ourselves
        with open(os.path.join(self.configpath, interface+'.conf'), 'r') as file:
            config = file.readlines()
        config = [ line.strip() for line in config ] # strip newlines, etc.
        config = [ line for line in config if (len(line)>0) and (line[0] not in [';', '#']) ] # strip comments, empty lines, etc.
        config = [ line if line[0] != '[' else line.lower() for line in config ] # section names to lower case
        config.append('[eof]')
        section_isinterface = None
        section_lines = []
        for line in config:
            if line[0] == '[':
                if section_isinterface is not None: # nothing to do on start of first section
                    d = section2dict(section_lines, prefix)
                    if section_isinterface:
                        self.data[interface] = {**d, **self.data[interface]} # merge dictionaries
                        self.data[interface]['peers'] = self.data[interface].get('peers', dict())
                    else:
                        k = d.get(prefix + 'public-key', '[PublicKey missing]')
                        self.data[interface]['peers'][k] = {**d, **self.data[interface]['peers'].get(k, dict())} # merge dictionaries
                # Prepare for reading section further
                section_isinterface = (line == '[interface]')
                section_lines = []
            else:
                section_lines.append(line)

    def retrieve_wireguard_config(self, interfaces, data=None, prefix=''):
        '''Sets the local data based on parsed WireGuard config files'''
        if data is None:
            self.clear_data()
        else:
            self.data = data
        for interface in interfaces:
            try:
                self.parse_wg_config(interface, prefix)
            except FileNotFoundError: # ignore missing config files (interface could have been configured by other means)
                logger.info('No config file found for interface [{0}]'.format(interface))

    @property
    def wgconfig():
        return self.data

    def get_interfaces(self):
        '''Returns the list of interfaces (as an iterator)'''
        return self.data.keys()
        
    def get_interfacedata(self, interface):
        '''Returns the data of the given interface as dictionary'''
        return self.data.get(interface)
        
    def get_peerdata(self, interface):
        '''Returns the data of the peers of the given interface as dictionary'''
        return self.data.get(interface, dict()).get('peers')


if __name__ == '__main__':
    wg = WireguardConfig()
    wg.retrieve_wireguard_config(['wg_1'])
    pprint.pprint(wg.get_interfaces())
    pprint.pprint(wg.get_interfacedata('wg_1'))
    pprint.pprint(wg.get_peerdata('wg_1'))
