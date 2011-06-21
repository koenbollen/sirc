# [si]rc - Asynchronous source RCON tool.

import Queue as queue
from util import *
import logging
import select
import socket
import struct
import threading
import time

COMMAND = 2
AUTH = 3

S_DISCONNECTED  = 0
S_CONNECTING    = 1
S_AUTHENICATING = 2
S_CONNECTED     = 4

class RCONError( BaseException ):
    def __init__(self, msg, server=None ):
        self.args = (msg,)
        self.server = server

class RCON(threading.Thread):
    """

    States:
     - disconnected
     - connecting
     - authenticating
     - waiting
    """

    timeout = 5
    retries = 5
    tryinterval = .1

    interval = 0.05

    def __init__(self, host, port, rcon ):
        threading.Thread.__init__(self,name="rcon-{0}:{1}".format(host,port))
        self.daemon = True

        self.addr = host, int(port)
        self.rconpass = rcon

        self.sock = None
        self.state = "disconnected"
        self.nextrid = 1
        self.lock = threading.Lock()

        self.results = {}
        self.resultcondition = threading.Condition()
        self.sendqueue = queue.PriorityQueue()
        self.callbacks = {}
        self.start()

    def run(self ):
        while True:
            if self.state != "connected":
                time.sleep( RCON.interval )
                continue

            try:
                task = self.sendqueue.get(timeout=RCON.interval)
            except queue.Empty:
                pass
            else:
                try:
                    self._send( task[1], COMMAND, task[0] )
                except Exception, e:
                    self.sendqueue.put(task)
                    self._startconnect(True)
                else:
                    self.sendqueue.task_done()

            try:
                rfds,_,_ = select.select([self.sock],[],[],RCON.interval)
                if self.sock in rfds:
                    raw = self._recv()
                    self._handle( *raw )

            except Exception, e:
                print e
                self._startconnect(True)

    def __repr__(self ):
        return "<RCON {addr[0]}:{addr[1]} {state}>".format( **self.__dict__ )

    def connect(self ):
        """Connect to the server.

        Try and create a connection to the specified host and port, try and
        authenticate.
        Retry when failed to connect a few times and set state.
        """
        if self.state != "disconnected":
            return
        self.state = "connecting"

        logging.debug( "connecting to {addr[0]}:{addr[1]}"
                .format(**self.__dict__) )

        trycount = 0
        while True:
            self.state = "connecting"
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.settimeout( RCON.timeout )
                self.sock.connect( self.addr )

                self.state = "authenticating"
                _, auth_rid = self._send( self.rconpass, AUTH )

                rid, ret, str1 = self._recv()
                if rid != auth_rid or ret != 0:
                    raise RCONError( "Invalid authentication reply.", self )

                rid, ret, str1 = self._recv()
                if rid != auth_rid or ret != 2:
                    raise RCONError(
                            "failed to authenticate, invalid rconpass", self )

                self.state = "connected"
                logging.info( "connected and authenticated to {addr[0]}:{addr[0]}"
                    .format(**self.__dict__) )
                return

            except RCONError:
                self.sock.close()
                self.state = "failed"
                raise
            except Exception, e:
                if trycount < RCON.retries:
                    self.sock.close()
                    self.state = "waiting"
                    time.sleep( trycount  * RCON.tryinterval )
                    trycount += 1
                    continue
                self.sock.close()
                self.state = "failed"
                raise

    def _startconnect(self, force=False):
        logging.debug( "reconnect called for {addr[0]}:{addr[1]}"
                .format(**self.__dict__) )
        if self.state != "disconnected":
            if not force:
                return
            self.state = "waiting"
            self.sock.close()
            self.sock = None
            self.state = "disconnected"
        t = threading.Thread(target=self.connect,
                name="rcon-connect-{0[0]}:{0[1]}".format(self.addr))
        t.daemon = True
        t.start()

    def poke(self, ):
        if self.state == "disconnected":
            self._startconnect()


    def _send(self, str1, command=COMMAND, rid=None ):
        """internal

        Send a packet with two strings and a command code to the server and
        return the number of bytes sent and the request ID (rid).
        """

        if self.state not in ("connected", "authenticating"):
            raise IOError( "sending packet w/o connection?" )

        if rid is None:
            self.lock.acquire()
            try:
                rid = self.nextrid
                self.nextrid += 1
            finally:
                self.lock.release()

        data = "{0}\0\0".format(str1)

        packet = struct.pack( "<lll", len(data)+8, rid, command )
        packet += data

        nbytes = self.sock.send( packet )
        #print repr(packet), len(packet), nbytes, len(data)+8

        return nbytes, rid

    def _recv(self ):
        """internal

        Receive a packet from the server and return the request ID, return
        code and two strings.
        """

        if self.state not in ("connected", "authenticating"):
            raise IOError( "receiving packet w/o connection?" )

        sizehead = self.sock.recv( 4 )
        if len(sizehead) != 4:
            raise IOError( "no packet header received." )

        size, _ = unint( sizehead )

        raw = ""
        left = size
        while len(raw) < size:
            chunk = self.sock.recv( size-len(raw) )
            if not len(chunk):
                raise IOError( "unexpected hangup from server" )
            raw += chunk

        rid, raw = unint( raw )
        ret, raw = unint( raw )
        str1, raw = unstring( raw )

        return rid, ret, str1

    def _handle(self, rid, ret, str1 ):
        """"internal"""
        self.resultcondition.acquire()
        try:
            if rid not in self.results:
                self.results[rid] = queue.Queue()
            self.results[rid].put( (ret, str1) )
            if self.results[rid].empty():
                del self.results[rid]
            self.resultcondition.notifyAll()
        finally:
            self.resultcondition.release()

        if rid in self.callbacks:
            cb = self.callbacks[rid]
            del self.callbacks[rid]
            t = threading.Thread(
                    target=cb, args=(rid, ret, str1),
                    name="rcon-callback-{0}".format(rid)
                )
            t.daemon = True
            t.start()

    def execute(self, command, cb=None ):
        """Set a command on the send queue and return the request ID.

        If cb is a function(rid,ret,str1) it will be called when reply is
        received (in a new thread).
        """
        self.poke()

        self.lock.acquire()
        try:
            rid = self.nextrid
            self.nextrid += 1
        finally:
            self.lock.release()

        if cb:
            self.callbacks[rid] = cb

        self.sendqueue.put( (rid, command) )
        return rid

    def rcon(self, command, timeout=None ):
        """execute given command and wait and return the result."""
        rid = self.execute( command )
        ret, str1 = self.getresult( rid, timeout )
        return str1.strip()


    def getresult(self, rid, timeout=None ):
        self.poke()
        self.resultcondition.acquire()
        if rid not in self.results:
            self.resultcondition.wait(timeout)
        if rid not in self.results:
            return None, None
        ret, str1 = self.results[rid].get_nowait()
        self.results[rid].task_done()
        self.resultcondition.release()
        return ret, str1


glock = threading.Lock()
manage = {}
def create( host, port, rcon ):
    try:
        host, port = socket.gethostbyname(host), int(port)
    except (IndexError, TypeError, ValueError), e:
        raise TypeError, "invalid host/port pair: " + e.args[0]

    glock.acquire()
    try:
        if (host,port) in manage:
            return manage[host,port]
        manage[host,port] = RCON(host,port,rcon)
        return manage[host,port]
    finally:
        glock.release()


if __name__ == "__main__":
    import os
    import sys
    from time import sleep
    from pprint import pprint
    from getpass import getpass

    logging.basicConfig(level=logging.DEBUG,format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        sys.argv.append( "localhost:27015" )
    addrs = [arg.split(":",1) for arg in sys.argv[1:]]

    for host, port in addrs:
        name = "{0}:{1}".format(host,port)
        try:
            rcon = os.environ["P"+name.replace(".","").replace(":","")]
        except KeyError:
            rcon = getpass( "rcon password for {0}: ".format(name) )
        s = RCON( host, int(port), rcon )
        s.connect()
        print s

        r = s.rcon( "stats", 4 )
        print r
        print

        def cb( rid, ret, str1 ):
            print str1
        s.execute( "help", cb=cb )


    time.sleep(10)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
