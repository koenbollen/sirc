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
            self.rawsend(self.command)
            return self.rawread()
        else:
            return False

    def rawsend(self,string1,string2='',command=EXECCOMMAND):

        self.packet = string1+"\x00"+string2+"\x00"
        self.packet = pack('L',command)+self.packet
        self.packet = pack('L',self.requestId)+self.packet
        self.packet = pack('L',len(self.packet))+self.packet
        self.s.send(self.packet)

        ## Debug code (remove later)

        print "Length :",len(self.packet)
        print "Content:",self.packet
        print "Req. ID:",self.requestId

        self.requestId += 1

    def rawread(self):
        self.packets = []
        self.buffer = ''
        if len(self.buffer) == 0:
            chunk = self.s.recv(4)
            if not chunk:
                return False
            length = unpack('L',chunk)[0]

            ## Debug code (remove later)

            print "Length :",length

        while (len(self.buffer)<(length-4)):
            chunk = self.s.recv(4096)
            self.buffer += chunk

        ## Unpacking starts here
  
        content = unpack('LLss',self.buffer)

        print content

        return content

    def connect(self):
        self.s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.s.connect((self.host,self.port))
        self.rawsend(self.rcon,'',AUTH)
        response = self.rawread()
        if response[1] != AUTH_RESPONSE:
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
    else:
        print "Nay!"
