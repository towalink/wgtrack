# -*- coding: utf-8 -*-

import asyncio
import concurrent
import logging
import pprint
import signal
import socket
import time

from . import logic


logger = logging.getLogger(__name__);


class EventProcessor():
    '''Class for providing event processing for the application (uses an asyncio event loop)'''

    def __init__(self, config):
        '''Constructor'''
        self.config = config
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue(loop=self.loop)
        self.logic = logic.Logic(config, self.enqueue)

    def handle_hup(self, signum, frame):
        '''Handle the SIGHUP signal'''
        logger.info('Signal "SIGHUP" received; reloading config')
        self.logic.initialize_data()

    def handle_exception(self, loop, context):
        '''Handler for exceptions in coroutines'''
        if isinstance(context.get('exception'), asyncio.CancelledError):
            logger.debug('Async event loop cancelled')
        else:
            logging.error('Caught exception: [{e}] [{m}] [{f}]'.format(e=context.get('exception', ''), m=context.get('message'), f=context.get('future')))

    def eventloop(self):
        '''Run the event processing loop'''
        #self.loop.set_debug(logger.getEffectiveLevel() <= logging.DEBUG) # in case of INFO, WARN, ERROR,... do not go into debug mode
        try:        
            self.loop.set_exception_handler(self.handle_exception)
            self.loop.run_until_complete(self.run_async())            
        finally:
            for task in asyncio.Task.all_tasks():
                task.cancel()
            self.loop.run_until_complete(self.loop.shutdown_asyncgens())
            self.loop.close()

    async def handle_message(self, reader, writer):
        '''Process incoming messages/commands'''
        data = await reader.read(100)
        message = data.decode()
        message = message.strip()
        addr = writer.get_extra_info('peername')
        logger.info(f'Received {message!r} from {addr!r}')
        if message == 'quit':
            raise KeyboardInterrupt
        #logger.debug(f'Sending: {message!r}')
        #writer.write(data)
        #await writer.drain()
        writer.close()

    async def run_periodically(self, cycle_time):
        '''Schedules tasks periodically each "cycle_time" (interval in seconds)'''
        while True:
            start = time.time()
            await self.logic.do_periodically()
            remaining_time = cycle_time - (time.time() - start)
            if remaining_time <= 0:
                logger.warning('Periodic tasks took longer than the cycle time; increase cycle time')
            await asyncio.sleep(remaining_time)

    async def enqueue(self, command, data):
        '''Enqueues an item in the event queue'''
        await self.queue.put({'command': command, 'data': data})

    async def serve_queue(self):
        '''Serve the event queue asynchronously'''
        while True:
            item = await self.queue.get()
            await self.logic.process_queue(item)

    async def run_async(self):
        '''Asynchronously executed code'''
        # Periodic tasks
        cycle_time = self.config.cycle_time
        task_periodic = asyncio.ensure_future(self.run_periodically(cycle_time))
        # Work queue
        task_queue =  asyncio.ensure_future(self.serve_queue())
        # Listener for receiving commands
        #THIS IS WORKING BUT CURRENTLY NOT NEEDED
        #server = await asyncio.start_server(self.handle_message, '127.0.0.1', 8888)    
        #addr = server.sockets[0].getsockname()
        #print(f'Serving on {addr}')
        #task_server = asyncio.ensure_future(server.serve_forever())
        task_server = asyncio.ensure_future(asyncio.sleep(1)) # TEMPORARY REPLACEMENT
        # Wait for all tasks to finish
        await asyncio.gather(task_periodic, task_queue, task_server)


def run(config):
    '''Creates an instance and runs it'''
    evt = EventProcessor(config)
    signal.signal(signal.SIGHUP, evt.handle_hup)
    evt.eventloop()


if __name__ == '__main__':
    run()
