# [si]rc - Asynchronous source RCON tool.

from functools import wraps
from irclib import *
import sqlalchemy
import model

def server_required(func):
    """This command requires a selected server."""
    @wraps(func)
    def _server( c, e, channel, server, command, argv ):
        if not server:
            c.privmsg(e.target(), "server required, please @specify or !select")
            return
        return func( c, e, channel, server, command, argv )
    return _server

def private(func):
    """This command can only be used with privmsgs."""
    @wraps(func)
    def _private( c, e, channel, server, command, argv ):
        if not e.eventtype().startswith( "priv" ):
            c.privmsg(e.target(), "private only command: " + command )
            return
        return func( c, e, channel, server, command, argv )
    return _private

def admin(func):
    """Command only for admins."""
    @wraps(func)
    def _admin( c, e, channel, server, command, argv ):
        try:
            a = model.Admin.query.filter_by(
                    mask=unicode(e.source())
                ).one()
            if channel not in a.channels:
                raise sqlalchemy.orm.exc.NoResultFound
        except sqlalchemy.orm.exc.NoResultFound:
            c.privmsg(
                    e.target(),
                    "access deNIED for {0}: {1}".format(
                        nm_to_n(e.source()), command)
                )
            return
        return func( c, e, channel, server, command, argv )
    return _admin

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
