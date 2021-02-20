# -*- coding: utf-8 -*-

import asyncio
import logging
import socket

from . import datakeeper as dk
from . import output


logger = logging.getLogger(__name__)


class Logic():
    '''Class that contains the business logic of this application'''

    def __init__(self, config, func_enqueue):
        '''Constructor'''
        self.config = config
        self.func_enqueue = func_enqueue
        self.data = dk.DataKeeper(config)

    def initialize_data(self):
        '''Reload the config and status'''
        self.data.initialize()

    async def ping(self, destination, interface, ping6=False):
        '''Asynchronously execute the ping command to chech reachability'''
        command = 'ping'
        if ping6 or (':' in destination):
            command = 'ping6'
        proc = await asyncio.create_subprocess_exec(command, '-q', '-c', '1', '-w', '1', '-W', '1', '-I', interface, destination, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        return proc.returncode

    def is_hostname(self, peername):
        '''Checks whether the provided peer is defined by hostname (in contrast to IP address)'''
        if peername is None:
            return False
        result = not (':' in peername) # ":" indicates an IPv6 address and is not allowed in hostname
        if result: # still a hostname candidate?
            parts = peername.split('.')
            result = (len(parts) != 4) or not (parts[0].isnumeric()) or not (parts[1].isnumeric()) or not (parts[2].isnumeric()) or not (parts[3].isnumeric())
        return result

    def endpoint_is_hostname(self, endpoint):
        '''Checks whether the provided endpoint is defined by hostname (in contrast to IP address)'''
        if endpoint is None:
            return False
        return self.is_hostname(endpoint.rpartition(':')[0]) # rpartition also works with IPv6

    async def do_periodically(self):
        '''Tasks to be executed periodically each cycle (called by scheduler coroutine)'''
        logger.debug('Executing periodic tasks')
        # Updates the WireGuard status information
        self.data.update_status()
        # Get config attributes
        cycles_wait = self.config.cycles_wait
        cycles_checking = self.config.cycles_checking
        cycles_checkperiod = self.config.cycles_checkperiod
        cycles_slowcheckingperiod = self.config.cycles_slowcheckingperiod
        ping_interval = self.config.ping_interval
        ping_failafternum = self.config.ping_failafternum
        # Iterate through all peers of all interfaces and determine new status
        ping_plan = []
        for interface, interfacedata, peer, peerdata in self.data.peeriterator():
            status = peerdata.get('status', 'undefined')
            cycle_counter = peerdata.get('cycle-counter', 0)
            #print(interface, 'Status', status, cycle_counter)
            update_peer = False
            # Act based on current state
            next = 'unchanged'
            if peerdata.get('handshake-status', 'failed') not in ['none', 'failed']:
                if peerdata.get('ping-address') is None:
                    peerdata['ping-address'] = peerdata['allowed-ips'][0].partition('/')[0]
                if ping_interval > 0:
                    if cycle_counter % ping_interval == 0:
                        next = 'ping'                
                if (status == 'undefined') and (next == 'unchanged'):
                    next = 'up:ok'
            elif (status == 'undefined') or (status == 'up:ok'):
                if self.endpoint_is_hostname(peerdata.get('config_endpoint')):
                    next = 'down:waiting' if (cycles_wait > 0) else 'down:checking'
                else: # no further check of peer needed
                    if peerdata.get('endpoint') is None:
                        next = 'disabled'
                    else:
                        next = 'down'
            elif status == 'down:waiting':
                if cycle_counter >= cycles_wait:
                    next = 'down:checking'
            elif status == 'down:checking':
                if cycle_counter >= cycles_checking:
                    next = 'down:backingoff'
                else:
                    if cycle_counter % cycles_checkperiod == 0:
                        update_peer = True
            elif status == 'down:backingoff':
                if cycle_counter >= peerdata['backingoff-limit']:
                    update_peer = True
                    peerdata['cycle-counter'] = 0
                    peerdata['backingoff-limit'] = 2 * peerdata['backingoff-limit']
                    if peerdata['backingoff-limit'] >= cycles_slowcheckingperiod:
                        next = 'down:slowchecking'
            elif status == 'down:slowchecking':
                if cycle_counter >= cycles_slowcheckingperiod:
                    update_peer = True
                    next = 'down:slowchecking'
            elif status == 'down':               
                pass
            elif status == 'disabled':               
                pass
            else:
                logger.critical('Unknown status [{0}]'.format(status))
            # Count cycles
            peerdata['cycle-counter'] = peerdata.get('cycle-counter', 0) + 1
            # Change state as needed
            if next == 'ping':
                if status == 'undefined':
                    peerdata['cycle-counter'] = 0
                    status = 'down:checking'
                ping_plan.append((interface, interfacedata, peer, peerdata))
                next = None
            elif next == 'down:backingoff':
                peerdata['backingoff-limit'] = 2 * cycles_checkperiod
            elif next == 'down:slowchecking':
                peerdata['backingoff-limit'] = None
            elif next == 'unchanged':
                next = None
            if next is not None:
                logger.info('Changing status of [{interface}:{peer}] to [{next}] after {cycle_counter} cycles'.format(interface=interface, peer=peer, next=next, cycle_counter=cycle_counter))
                peerdata['cycle-counter'] = 0
                status = next
            # Update peer if requested
            if update_peer:
                config_endpoint = peerdata.get('config_endpoint')
                logger.debug('Requesting to check for update of [{interface}:{peer}], endpoint [{config_endpoint}]'.format(interface=interface, peer=peer, config_endpoint=config_endpoint))
                await self.func_enqueue('update_peer', { 'interface': interface, 'peer': peer, 'config_endpoint': peerdata.get('config_endpoint'), 'endpoint': peerdata.get('endpoint') })
            #self.data.set(interface, peer, 'status', status)
            peerdata['status'] = status
        # Check reachability by pinging peers
        if len(ping_plan) > 0:
            ping_tasks = []
            for interface, interfacedata, peer, peerdata in ping_plan:
                addr = peerdata['ping-address']
                ping_tasks.append(asyncio.ensure_future(self.ping(addr, interface)))
            await asyncio.gather(*ping_tasks)
            for i, ping_task in enumerate(ping_tasks):
                if ping_task.result() == 0:
                    if ping_plan[i][3]['status'] != 'up:ok':
                        logger.info('Changing status of [{interface}:{peer}] to [up:ok] after successful ping'.format(interface=ping_plan[i][0], peer=ping_plan[i][2]))
                        ping_plan[i][3]['status'] = 'up:ok'
                        ping_plan[i][3]['cycle-counter'] = 0
                    ping_plan[i][3]['ping-failcounter'] = 0
                else:
                    ping_plan[i][3]['ping-failcounter'] = ping_plan[i][3].get('ping-failcounter', 0) + 1
                    if ping_plan[i][3]['ping-failcounter'] >= ping_failafternum:
                        if ping_plan[i][3]['status'] != 'down:waiting':
                            logger.info('Changing status of [{interface}:{peer}] to [down:waiting] after failed ping'.format(interface=ping_plan[i][0], peer=ping_plan[i][2]))
                            ping_plan[i][3]['status'] = 'down:waiting'
                        ping_plan[i][3]['cycle-counter'] = 0
        # Output new status
        await output.output_status(self.config.outputs, self.data)

    def update_peer(self, interface, peer, config_endpoint, endpoint):
        '''Checks whether peer needs to be updated and does it if needed'''
        config_endpoint, _, config_port = config_endpoint.rpartition(':') # rpartition also works with IPv6
        # Endpoint IPv4 has format "1.1.1.1:51712", endpoint IPv6 has format "[2003:db:cf0c:f100:dea6:32ff:fe9a:859d]:51712"; thus split at last colon
        endpoint = endpoint.rpartition(':')[0]
        # Remove leading "[" and trailing "]" in IPv6 case
        endpoint = endpoint.strip('[')
        endpoint = endpoint.strip(']')
        logger.info('Resolving [{0}]'.format(config_endpoint))
        needed_endpoint = None
        try:
            needed_endpoint = socket.getaddrinfo(config_endpoint, 0)[0][4][0] # get ip address
        except socket.gaierror as e:
            # Something like "socket.gaierror: [Errno -3] Try again" can happen here
            logger.warning('Error resolving interface endpoint [{0}]: {1}'.format(config_endpoint, str(e)))            
        if (needed_endpoint is not None) and (needed_endpoint != endpoint):
            logger.info('Changing interface endpoint [{0}] to changed IP [{1}]'.format(config_endpoint, needed_endpoint))        
            if config_port is not None:
                needed_endpoint += ':' + config_port
            self.data.set_endpoint(interface, peer, needed_endpoint)

    async def process_queue(self, item):
        '''Process an item from the event queue (called by queue listener coroutine)'''
        data = item.get('data', dict())
        if item.get('command') == 'update_peer':
            self.update_peer(data['interface'], data['peer'], data['config_endpoint'], data['endpoint'])
        else:
            logger.critical('Unknown command in event [{0}]'.format(item.get('command')))
