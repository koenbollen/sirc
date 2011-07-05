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
import util


logging.basicConfig(level=logging.DEBUG,format="%(levelname)s: %(message)s")

ServerInfo = namedtuple("ServerInfo","host port nickname username password ssl")

class SIrc(object):

    def __init__(self, serverinfo ):
        self.info = serverinfo
        self.running = False
        self.irc = IRC()
        self.connection = self.irc.server()
        self.irc.add_global_handler("all_events", self.dispatcher, -10)
        self.known_nick = self.info.nickname

    def dispatcher(self, c, e ):
        m = "on_" + e.eventtype()
        if hasattr(self, m):
            getattr(self, m)(c, e)

    def connect(self ):
        logging.info( "Connecting to {0}".format(self.info.host) )
        self.connection.connect(
                self.info.host, self.info.port, self.info.nickname,
                self.info.password, self.info.username,
                "[si]rc bot, (by Koen Bollen)",
                None, None, self.info.ssl
            )

    def on_endofmotd(self, c, e ):
        self.known_nick = e.target()
        logging.debug( "endofmotd received, joining.. " +
                str(len(model.Channel.query.all())) )
        for ch in model.Channel.query.all():
            logging.info( "joining {0}".format(ch.name) )
            if ch.key and len(ch.key)>0:
                c.join( ch.name, ch.key )
            else:
                c.join( ch.name )

    def on_nick(self, c, e ):
        old = self.known_nick
        self.known_nick = e.target()
        logging.info( "nick changed from {0} to {1}".format(old,
            self.known_nick) )

    def on_join(self, c, e ):
        if nm_to_n( e.source() ) == self.known_nick:
            c.privmsg( e.target(), "[si]rc bot, reporting for duty!" )

    def start(self ):
        self.running = True
        self.connect()
        self.irc.process_forever()

    def stop(self, reason=""):
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
        try:
            ch = admin.selectchannel(e)
        except ValueError, ee:
            c.privmsg(nm_to_n(e.source()), ee.args[0] )
            return
        except TypeError:
            return
        return self.on_pubmsg(c, e, ch )

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
        match = util.regex.search( argv[0] )
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
        import commands
        if logging.root.level >= logging.DEBUG:
            reload(commands)
        if command in commands.__all__:
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
