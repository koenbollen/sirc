#!/usr/bin/env python
# [si]rc

import model
from irclib import *
from time import sleep
from collections import namedtuple
import sqlalchemy
import logging

logging.basicConfig(level=logging.DEBUG)


ServerInfo = namedtuple("ServerInfo","host port nickname username password ssl")

class SIrc(object):
    def __init__(self, serverinfo ):
        self.info = serverinfo
        self.irc = IRC()
        self.connection = self.irc.server()
        self.irc.add_global_handler("all_events", self.dispatcher, -10)

    def dispatcher(self, c, e ):
        m = "on_" + e.eventtype()
        if hasattr(self, m):
            getattr(self, m)(c, e)


    def connect(self ):
        self.connection.connect(
                self.info.host, self.info.port, self.info.nickname,
                self.info.password, self.info.username, "[si]rc bot",
                None,None,self.info.ssl
            )

    def on_endofmotd(self, c, e ):
        for ch in model.Channel.query.all():
            logging.debug( "joining {0}".format(ch.name) )
            c.join( ch.name )

    def start(self ):
        self.connect()
        self.irc.process_forever()

    def on_disconnect(self, c, e ):
        sleep(1)
        self.connect()

    def on_pubmsg(self, c, e ):
        try:
            ch = model.Channel.query.filter_by(name=unicode(e.target())).one()
        except sqlalchemy.orm.exc.NoResultFound:
            c.privmsg(e.target(), "channel not registered!")
            return
        c.privmsg(e.target(), "Admins on this channel: "+repr(ch.admins) )

    def on_privmsg(self, c, e ):
        from pprint import pprint
        print e.source(), ":", e.arguments()

if __name__ == "__main__":
    model.metadata.bind.echo = False
    model.setup_all(True)
    inst = SIrc( ServerInfo("xkcd.nl.smurfnet.ch",6697,"koenbot","koen",None,True) )
    inst.start()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
