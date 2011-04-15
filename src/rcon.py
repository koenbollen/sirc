#!/usr/bin/env python

from xdrlib import *
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

    def unpackhelper(self,fmt,data):
        size = calcsize(fmt)
        return unpack(fmt, data[:size]), data[size:]

    def command(self,command):
        if self.connectstate:
            self.rawsend(command)
            return self.rawread()
        else:
            return False

    def rawsend(self,string1,string2='',command=EXECCOMMAND):

        self.packet = string1+"\x00"+string2+"\x00"
        self.packet = pack('LL',self.requestId,command)+self.packet
        self.packet = pack('L',len(self.packet))+self.packet
        self.s.send(self.packet)
        self.requestId += 1

    def rawread(self):
        self.packets = []
        self.buffer = ''
        self.s.settimeout(1)
        while True:
            try:
                chunk = self.s.recv(4096)
            except socket.timeout:
                break

            if chunk == "":
                break

            responseId = unpack('L',chunk[1:5][::-1])
            commandResponse = unpack('L',chunk[5:9][::-1])

            self.buffer = [ responseId,commandResponse ]

        return self.buffer

    def connect(self):
        self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.s.connect((self.host,self.port))
        self.rawsend(self.rcon,'',AUTH)
        response = self.rawread()
        print response
        if response[1][0] != 2:
            self.s.close()
            self.connectstate = False
            return False
        else:
            self.connectstate = True
            return True

if __name__ == "__main__":
    x = rconConnection('145.92.203.100',27115,'byt3m3')
    if x.connect():
        print "Yay!"
        x.command('status')
    else:
        print "Nay!"
