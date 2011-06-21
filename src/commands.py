#!/usr/bin/env python
#

import logging
import model
import sirc
import sqlalchemy
import functools


def list( c, e, channel, server, command, argv ):
    """List servers in this channel"""
    reply = "Servers:\n"
    for s in channel.servers:
        reply += str(s) + "\n"
    return reply

@sirc.admin
@sirc.private
def add( c, e, channel, server, command, argv ):
    """Add a server to this channel"""
    args = ("name", "host", "port", "rcon", "servertype")
    if len(argv) < 5:
        return "usage: !add name host port rcon [normal|tv]"
    if len(argv) < 6:
        args = args[:5]
    else:
        if argv[5] != "tv":
            argv[5] = "normal"
    argv = map(unicode, argv)
    info = dict(zip(args,argv[1:]))
    try:
        ss = model.Server.query.filter_by( channel=channel, name=argv[1] ).all()
        if len(ss) > 0:
            return "server '{0}' exists!".format(argv[1])
    except sqlalchemy.orm.exc.NoResultFound:
        s = None
    s = model.Server( channel=channel, **info )
    channel.servers.append( s )
    model.session.commit()
    return "server '{0}' created!".format(s.name)

@sirc.admin
def select( c, e, channel, server, command, argv ):
    """Show or select the active server of this channel"""
    if len(argv) > 1:
        new = model.Server.search( argv[1], channel ).first()
        for s in channel.servers:
            s.selected = False
        new.selected = True
        model.session.commit()
        return "now selected: " + str(new)
    current = model.Server.select(channel).first()
    return "selected: " + str(current)


@sirc.server_required
def stats( c, e, channel, server, command, argv ):
    """Display the command 'stats' on selected server."""
    r= server.connection.execute( "stats",
            cb=functools.partial( sirc.ridretstr1_cb, c, e ) )

def help( c, e, channel, server, command, argv ):
    """Show available commands"""
    import commands
    result = {}
    maxlen = 0
    for c in filter(lambda x: not x.startswith("_"), dir(commands)):
        func = getattr(commands,c)
        if not hasattr( func, "__call__" ):
            continue
        result[c] = (func.__doc__, func)
        if len(c) > maxlen:
            maxlen = len(c)
    reply = "Available commands:\n"
    for c in sorted(result.keys()):
        reply += " !{0:<{1}} : {2}\n".format(c,maxlen,result[c][0])
    return reply


# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
