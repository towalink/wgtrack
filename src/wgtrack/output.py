# -*- coding: utf-8 -*-

import logging
import socket
import time

from . import atomicwrite


logger = logging.getLogger(__name__)


async def output_status_influx(config, data):
    '''Outputs the status as InfluxDB wire protocol'''
    # https://github.com/influxdata/telegraf/blob/master/docs/DATA_FORMATS_INPUT.md
    # https://docs.influxdata.com/influxdb/v1.7/write_protocols/line_protocol_tutorial/
    filename = config.get('filename', '/var/cache/wg-track_influx.out')
    with atomicwrite.open_for_atomic_write(filename) as f:
      hostname = socket.getfqdn()
      for interface, interfacedata, peer, peerdata in data.peeriterator():
          timestamp = peerdata.get('timestamp')
          if timestamp is None:
              timestamp = time.time()
          timestamp = '{:.0f}'.format(timestamp*1000000000)
          attrs = ['transfer-rx', 'transfer-tx', 'status']
          
          readings = []
          for attr in attrs:
              value = peerdata.get(attr)
              if value is None: # None values shall not be included but these attributes just be omitted
                continue
              value = str(value) # Make sure we're dealing with strings now
              value = value.replace('=','').replace(',','').replace('"','').replace(' ','') # remove any special characters that have meaning in the Influx wire protocol
              attr = attr.replace('-', '_') # Influx convention is to use underscores instead of dashes
              if attr in ['transfer-rx', 'transfer-tx']: #integer values
                if value is not None:
                  value += 'i'
              elif attr in ['status']: #string values
                value = '"' + value + '"'
              reading = '{attr}={value}'.format(attr=attr, value=value)
              readings.append(reading)
          readings = ','.join(readings)    
          reading = 'wireguard,hostname={hostname},interface={interface},peer={peer} {readings} {timestamp}\n'.format(hostname=hostname, interface=interface, peer=peer, readings=readings, timestamp=timestamp)
          f.write(reading)

async def output_status(outputs, data):
    '''Outputs the status information in the requested formats'''
    for output, output_config in outputs.items():
        if output == 'influx':
            await output_status_influx(output_config, data)
        else:
            logger.error('Unknown output [[{0}] specified in config file'.format(output))