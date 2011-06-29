#!/usr/bin/env python
#

"""A single thread that queries and maintains information on source servers.
"""

from Queue import Queue
from time import time
import logging
import select
import socket
import struct
import threading
from util import *

RESPONSE_PING = 0x6A
RESPONSE_INFO = 0x49

class QueryThread(threading.Thread):
    """
    A single thread that maintains server information for steam source servers.

    Keeps info up-to-date.
    """
    threadcount=0

    def __init__(self, interval=60 ):
        threading.Thread.__init__(self)
        self.daemon = True
        self.name = "QueryThread-{0}".format(QueryThread.threadcount)
        QueryThread.threadcount += 1

        self.running = False
        self.interval = interval

        self.sock = None
        self.bufsize = 1400
        self.timeout = self.interval/10.0

        self.lock = threading.Lock()
        self.queue = []
        self.wait = []
        self.cache = {}

    def run(self ):
        """internal"""
        self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
        self.running = True
        while self.running:
            rfds, _, _ = select.select( [self.sock], [], [], self.timeout )
            for fd in rfds:
                if fd != self.sock: # should not happen
                    continue
                raw, addr = self.sock.recvfrom( self.bufsize )
                logging.debug( "recvieved {0!r} from {1!r}".format(raw[:5], addr) )
                self.handle( addr, raw )
            else:
                self.lock.acquire()

                threshold = time()-self.interval
                for s in self.wait:
                    if s[0] > threshold:
                        break
                    self.queue.append( s[1] )
                    self.wait.remove(s)

                localqueue = self.queue
                self.queue = []

                self.lock.release()

                for addr in localqueue:
                    self.request( addr )

    def enqueue(self, pair ):
        try:
            pair = socket.gethostbyname(pair[0]), int(pair[1])
        except (IndexError, TypeError, ValueError), e:
            raise TypeError, "invalid host/port pair: " + e.args[0]

        self.lock.acquire()
        self.queue.append( pair )
        self.lock.release()

    def __getitem__(self, pair ):
        try:
            pair = socket.gethostbyname(pair[0]), int(pair[1])
        except (IndexError, TypeError, ValueError), e:
            raise TypeError, "invalid host/port pair: " + e.args[0]

        if pair not in self.cache:
            self.enqueue( pair )
            raise KeyError, "host/port pair not yet cached, sent to queue"

        return dict(self.cache[ pair ])

    def __repr__(self ):
        return repr(self.cache)

    def request(self, addr ):
        """internal"""
        logging.debug( "sending query request to {0!r}".format(addr) )

        now = time()
        self.sock.sendto( "\xff\xff\xff\xffTSource Engine Query\0", addr )

        server = self.cache.get(addr,{})
        server['_gnip'] = now
        self.cache[addr] = server

    def handle(self, addr, raw ):
        """internal"""

        packettype, raw = unpack( "<l", raw )
        if packettype != -1:
            raise NotImplemented, "splitpackets"

        server = self.cache.get(addr,{})

        responsetype, raw = unpack( "<B", raw )
        if responsetype == RESPONSE_INFO:
            if "_gnip" in server:
                ping = time()-server['_gnip']
                server['_gnip'] = 0
            elif 'ping' in server:
                ping = server['ping']
            else:
                ping = 0
            version, raw = unpack( "<B", raw )
            name, raw = unstring( raw )
            mapname, raw = unstring( raw )
            gamedir, raw = unstring( raw )
            game, raw = unstring( raw )
            appid, raw = unpack( "<h", raw )
            (players, maxplayers, numbots), raw = unpack( "<BBB", raw )
            self.cache[addr] = {'name': name, 'mapname': mapname, 'gamedir':
                    gamedir, 'game': game, 'players': players, 'ping': ping,
                    'maxplayers': maxplayers, 'numbots': numbots}

            self.wait.append( (time(), addr) )


if __name__ != "__main__":
    thread = QueryThread()
    thread.start()

if __name__ == "__main__":
    import sys
    from time import sleep
    from pprint import pprint

    logging.basicConfig(level=logging.DEBUG,format="%(levelname)s: %(message)s")

    qthread = QueryThread(interval=5) # testing interval of 5 seconds.
    qthread.start()
    sleep(0.1)

    if len(sys.argv) < 2:
        sys.argv.append( "localhost:27015" )
    for host,port in [arg.split(":",1) for arg in sys.argv[1:]]:
        qthread.enqueue( (host.strip(), int(port)) )

    sleep(1)
    pprint( qthread )
    qthread.join(20)
    pprint( qthread )

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
