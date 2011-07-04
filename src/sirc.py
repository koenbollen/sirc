#!/usr/bin/env python
# [si]rc

from collections import namedtuple
from functools import wraps
from irclib import *
from time import sleep
import logging
import model
import re
import shlex
import sqlalchemy

import commands

logging.basicConfig(level=logging.DEBUG,format="%(levelname)s: %(message)s")

ServerInfo = namedtuple("ServerInfo","host port nickname username password ssl")

class SIrc(object):

    regex = re.compile( r"^(?:@(?P<server>[\.\w]+))?!(?P<command>\w+)" )

    def __init__(self, serverinfo ):
        self.info = serverinfo
        self.running = False
        self.irc = IRC()
        self.connection = self.irc.server()
        self.irc.add_global_handler("all_events", self.dispatcher, -10)

    def dispatcher(self, c, e ):
        m = "on_" + e.eventtype()
        if hasattr(self, m):
            getattr(self, m)(c, e)


    def connect(self ):
        logging.info( "Connecting to {0}".format(self.info.host) )
        self.connection.connect(
                self.info.host, self.info.port, self.info.nickname,
                self.info.password, self.info.username, "[si]rc bot",
                None,None,self.info.ssl
            )

    def on_endofmotd(self, c, e ):
        logging.debug( "endofmotd received, joining.. " +
                str(len(model.Channel.query.all())) )
        for ch in model.Channel.query.all():
            logging.info( "joining {0}".format(ch.name) )
            if ch.key and len(ch.key)>0:
                c.join( ch.name, ch.key )
            else:
                c.join( ch.name )

    def start(self ):
        self.running = True
        self.connect()
        self.irc.process_forever()

    def stop(self, reason=None):
        self.running = False
        self.connection.disconnect(reason)

    def on_disconnect(self, c, e ):
        if not self.running:
            return
        sleep(1)
        self.connect()

    def on_privmsg(self, c, e ):
        try:
            admin = model.Admin.query.filter_by(mask=unicode(e.source())).one()
        except sqlalchemy.orm.exc.NoResultFound:
            logging.warning( "privmsg received from unregistered user: " + e.source() )
            c.privmsg(nm_to_n(e.source()), "user not registered." )
            return
        e._target = nm_to_n( e.source() )
        return self.on_pubmsg(c, e, admin.channel )


    def on_pubmsg(self, c, e, ch=None ):
        if not ch:
            try:
                ch = model.Channel.query.filter_by(name=unicode(e.target())).one()
            except sqlalchemy.orm.exc.NoResultFound:
                c.privmsg(e.target(), "channel not registered!")
                return
        line = e.arguments()[0]
        try:
            argv = shlex.split(line)
        except ValueError:
            argv = line.split()
        match = SIrc.regex.search( argv[0] )
        if not match:
            return
        try:
            server = match.group("server")
        except IndexError:
            server = None
        if server:
            server = model.Server.search(server, ch).first()
        else:
            server = model.Server.select( ch ).first()
        command = match.group("command")
        if hasattr(commands, command):
            funk = getattr(commands, command)
            result = None
            try:
                result = funk(c, e, ch, server, command, argv)
            except Exception, e:
                logging.error( "error while executing {0}: {1}"
                        .format( command, e ) )
                if logging.root.level == logging.DEBUG:
                    print "-"*40
                    import traceback
                    traceback.print_exc()
                    print "-"*40
                return
            logging.debug( "command '{0}' executed, by {1} on {2}"
                    .format(command, e.source(),repr(server)) )
            if result and isinstance(result, basestring):
                for line in result.strip().splitlines():
                    c.privmsg(e.target(), line)


# command utils:

def ridretstr1_cb(c, e, rid, ret, str1):
    if str1 and isinstance(str1, basestring):
        for line in str1.strip().splitlines():
            c.privmsg( e.target(), line )

# command decorators:

def server_required(func):
    @wraps(func)
    def _server( c, e, channel, server, command, argv ):
        if not server:
            c.privmsg(e.target(), "server required, please @specify or !select")
            return
        return func( c, e, channel, server, command, argv )
    return _server

def private(func):
    @wraps(func)
    def _private( c, e, channel, server, command, argv ):
        if not e.eventtype().startswith( "priv" ):
            c.privmsg(e.target(), "private only command: " + command )
            return
        return func( c, e, channel, server, command, argv )
    return _private

def admin(func):
    @wraps(func)
    def _admin( c, e, channel, server, command, argv ):
        try:
            a = model.Admin.query.filter_by(
                    channel=channel,
                    mask=unicode(e.source())
                ).one()
        except sqlalchemy.orm.exc.NoResultFound:
            c.privmsg(e.target(), "access deNIED for command: " + command )
            return
        return func( c, e, channel, server, command, argv )
    return _admin




if __name__ == "__main__":
    model.metadata.bind.echo = False
    model.setup_all(True)
    inst = SIrc( ServerInfo("xkcd.nl.smurfnet.ch",6697,"koenbot","koen",None,True) )
    try:
        inst.start()
    except KeyboardInterrupt:
        print "quit"
        inst.stop("KeyboardInterrupt")
        sleep(1)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
