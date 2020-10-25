# -*- coding: utf-8 -*-

import configparser
import logging


class Config(configparser.ConfigParser):
    '''ConfigParser with application-specific helper methods/properties defining defaults'''
    
    def __init__(self, configfile=None):
        '''Constructor'''
        super().__init__()
        if configfile is not None:
            self.read(configfile)
        
    def read(self, configfile):
        '''Read config, make sure general section exists, and remember filename'''
        super().read(configfile)
        if not self.has_section('general'):
            self.add_section('general')
        self['general']['configfile'] = configfile

    @property
    def cycle_time(self):
        return float(self['general'].get('cycle_time', 30))

    @property
    def cycles_wait(self):
        return int(self['general'].get('cycles_wait', 2))
    
    @property
    def cycles_checking(self):
        return int(self['general'].get('cycles_checking', 4))

    @property
    def cycles_checkperiod(self):
        return int(self['general'].get('cycles_checkperiod', 2))

    @property
    def cycles_slowcheckingperiod(self):
        return int(self['general'].get('cycles_slowcheckingperiod', 20))

    @property
    def ping_interval(self):
        return int(self['general'].get('ping_interval', 2))

    @property
    def ping_failafternum(self):
        return int(self['general'].get('ping_failafternum', 2))

    @property
    def loglevel(self):
        return int(self['general'].get('loglevel', logging.INFO))

    @loglevel.setter
    def loglevel(self, value):
        if value is not None:
            self['general']['loglevel'] = str(value)

    @property
    def outputs(self):
        return { k[7:]: self[k] for k in self.sections() if k.startswith('output:') }
