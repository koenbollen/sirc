#!/usr/bin/env python

from struct import *
from socket import *
import socket

EXECCOMMAND = 2
AUTH = 3
RESPONSE = 0
AUTH_RESPONSE = 2

class rconConnection(object):


    def __init__(self,host,port,rcon):
        self.host = host
        self.port = port
        self.rcon = rcon
        self.requestId = 1
        self.connectstate = False

    def command(self,command):
        self.command = command
        if connectstate:
            rawsend(self.command)
            return self.rawread()
        else:
            return False

    def rawsend(self,string1,string2='',command=EXECCOMMAND):
        self.command = command
        self.packet = string1+"\x00"+string2+"\x00"
        self.packet = pack('LL', self.requestId, self.command)+self.packet
        self.packet = pack('L', len(self.packet))+self.packet
        self.s.send(self.packet)
        print self.packet
        self.requestId += 1

    def rawread(self):
        return
        data = ""
        while True:
            chunk = self.s.recv(4096)
            if not chunk:
                break
            data += chunk
        return data

    def connect(self):
        self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.s.connect((self.host,self.port))
        self.rawsend(self.rcon,'',AUTH)
        self.data = self.rawread()
        if self.data[0]['CommandResponse'] != AUTH_RESPONSE:
            s.close()
            return False
        else:
            return True

if __name__ == "__main__":
    x = rconConnection('145.92.203.100',27115,'byt3m3')
    x.connect()
