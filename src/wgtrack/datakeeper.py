# -*- coding: utf-8 -*-

"""Class that maintains the data (attributes and values of interfaces and peers) and makes it accessible"""

import collections
import enum
import logging
import os
import pprint

from . import wg_config
from . import wg_command


logger = logging.getLogger(__name__);


class DataKeeper():
    '''Class for maintaing and accessing the data (attributes and values of interfaces and peers)'''

    def __init__(self, config):
        '''Constructor'''
        self.cfg = config
        self.configfile = config['general']['configfile']        
        self.initialize()

    def initialize(self):
        '''Reads the config and initializes the data structures'''
        # WireGuard command for status information
        self.wgcmd = wg_command.WireguardCommand()
        self.wgcmd.retrieve_wireguard_data()
        self.data = self.wgcmd.data
        # WireGuard config files
        self.wgcfg = wg_config.WireguardConfig()
        self.wgcfg.retrieve_wireguard_config(self.get_interfaces(), self.data, 'config_')
        # Merge config file content into data tree
        self.cfg.read(self.configfile)
        for section in self.cfg.sections():
            if section == 'general':
                for k, v in self.cfg[section].items():
                    self.data[k] = v
            elif section.startswith('interface:'):
                for k, v in self.cfg[section].items():
                    self.data[section][k[10:]] = v
        
    def get(self, interface, peer, attr, default=None):
        '''Gets data matching the specified interface, peer, and attribute (None is allowed for each parameter to get all)'''
        if interface is None:
            if peer is not None:
                raise ValueError('Peer provided but not interface')
            value = self.data
        else:
            value = self.data.get(interface, dict())
            if (attr is not None) or (peer is not None):
                value = value.get(attr if peer is None else 'peers', dict())
                if peer is not None:
                    value = value.get(peer, dict())
                    if attr is not None:
                        value = value.get(attr, default)
        return value    

    def set(self, interface, peer, attr, value):
        '''Sets the value of an attribute matching the specified interface and peer (None is allowed for these)'''
        if (attr is None) or (value is None):
                raise ValueError('Attribute and value need to be provided')
        if interface is None:
            if peer is not None:
                raise ValueError('Peer provided but not interface')
            self.data[attr] = value
        else:
            if peer is None:
                self.data[interface][attr] = value
            else:
                self.data[interface]['peers'][peer][attr] = value
            
    def decrement(self, interface, peer, attr):
        '''Decreases the value of the specified attribute'''
        self.set(interface, peer, attr, self.get(interface, peer, attr, 0) - 1)
            
    def get_interfaces(self):
        '''Returns the list of interfaces (as an iterator)'''
        return self.data.keys()

    def peeriterator(self):
        '''Returns the peer data (as a generator)'''
        for interface, data in self.data.items():
            if isinstance(data, collections.abc.Mapping): # is it a dictionary?
                interfacedata = { k: v for k, v in data.items() if k != 'peers' }
                for peer, peerdata in data.get('peers', dict()).items():
                    yield interface, interfacedata, peer, peerdata

    def update_status(self):
        '''Updates the WireGuard status data'''
        self.wgcmd.retrieve_wireguard_data(self.data)

    def set_endpoint(self, interface, peer, endpoint):
        '''Updates the endpoint of the specified WireGuard peer'''
        return self.wgcmd.execute_wg_set(interface, peer, 'endpoint', endpoint)


if __name__ == '__main__':
    pass
