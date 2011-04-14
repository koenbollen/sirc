#!/usr/bin/env python

from socket import *

class rconConnection(object):

    def __init__(self,host,port,rcon):
        self.host = host
        self.port = port
        self.rcon = rcon

    def command(self,command):
        self.command = command

    def connect(self):
		s = socket(AF_INET,SOCK_STREAM)
        s.setsockopt(SOL_SOCKET,SO_REUSEADDR,1)
        
def __main__(self):
    
