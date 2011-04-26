#!/usr/bin/env python

import struct
from socket import *
from Queue import Queue
import socket
import logging
import threading

EXECCOMMAND = 2
AUTH = 3
RESPONSE = 0
AUTH_RESPONSE = 2

def nomnom( fmt, raw ):
    size = struct.calcsize( fmt )
    res = struct.unpack( fmt, raw[:size] )
    if len(res) == 1:
        res = res[0]
    return res, raw[size:]

def nomstr( raw ):
    size = raw.index('\0')
    return raw[:size], raw[size+1:]

class RconConnection(threading.Thread):

    def __init__(self,host,port,rcon):
        threading.Thread.__init__(self, name="rcon-{0}:{1}".format(host,port))
        self.daemon = True
        self.host = host
        self.port = port
        self.rcon = rcon
        self.packets = {}
        self.cond = threading.Condition()
        self.rid = 0
        self.connectstate = False
        self.sock = None

    def command(self,command):
        if self.connectstate:
            return self.send(command)
        else:
            return False

    def send(self,string1,string2='',command=EXECCOMMAND):
        self.rid += 1
        packet = string1+"\x00"+string2+"\x00"
        packet = struct.pack('<II',self.rid,command)+packet
        packet = struct.pack('<I',len(packet))+packet
        self.sock.send(packet)
        return self.rid

    def run(self ):
        while True:
            self.rawread()

    def rawread(self):
        try:
            raw = self.sock.recv(4)
            if len(raw) > 0:
                size, raw = nomnom("<L", raw)
                raw = self.sock.recv(size)
                rid, raw = nomnom( "<L", raw )
                ret, raw = nomnom( "<L", raw )
                str1, raw = nomstr(raw)
                self.cond.acquire()
                if rid not in self.packets:
                    self.packets[rid] = Queue()
                self.packets[rid].put( (ret, str1) )
                self.cond.notifyAll()
                self.cond.release()
        except:
            pass

    def getresponse(self, rid, timeout=None ):
        self.cond.acquire()
        if rid not in self.packets:
            self.cond.wait(timeout)
        if rid not in self.packets:
            return None, None
        packet = self.packets[rid].get()
        del self.packets[rid]
        self.cond.release()
        return packet

    def parsepayload(self,packets):
        return packets[0][2].split('\n')

    def connect(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.connect((self.host,self.port))
        self.start()
        auth_rid = self.send(self.rcon,'',AUTH)
        ret,s = self.getresponse( auth_rid, 1 )
        ret,s = self.getresponse( auth_rid, 1 )
        if ret != 2:
            self.sock.close()
            self.connectstate = False
            return False
        else:
            self.connectstate = True
            return True

    @property
    def status(self ):
        rid = self.command( "status" )
        _, str1 = self.getresponse( rid )
        info = {}
        for line in str1.splitlines():
            if ":" in line:
                key,value = line.split(":", 1)
                info[key.strip().lower()] = value.strip()
        return info

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    myserver = RconConnection('145.92.203.100',27115,'lubm4t3')
    myserver.connect()

    print myserver.status

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
