# [si]rc - Asynchronous source RCON tool.

from decorators import *
import functools
from textwrap import dedent
import logging
import model
import sqlalchemy
import time

__all__ = [
        "list", "select",
        "add", "set", "delete",
        "stats", "status", "rcon",
        "error", "help"
    ]



def list( c, e, channel, server, command, argv ):
    """List servers in this channel"""
    reply = "Servers:\n"
    for s in channel.servers:
        reply += str(s) + "\n"
    return reply

@admin
def select( c, e, channel, server, command, argv ):
    """Show or select the active server of this channel"""
    if len(argv) > 1:
        new = model.Server.search( argv[1], channel ).first()
        if not new:
            return "no such file, directory or server: " + str(argv[1])
        for s in channel.servers:
            s.selected = False
        new.selected = True
        model.session.commit()
        return "now selected: " + str(new)
    current = model.Server.select(channel).first()
    return "selected: " + str(current)

@admin
@private
def add( c, e, channel, server, command, argv ):
    """
    Add a server to this channel

    only available as a private message due to the rcon password.
    """
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

@admin
@server_required
def set( c, e, channel, server, command, argv ):
    """Set/change properties of a server."""
    valid = ("name", "host", "port", "rcon", "config", "servertype")
    alias = {"hostname": "host",
            "portnumber": "port",
            "password": "rcon",
            "pass": "rcon",
            "cfg": "config",
            "type": "servertype"}

    reply = ""
    if len(argv) < 2:
        reply = "usage: [@server]!edit ["
        reply += "=value] [".join(valid) + "=value]"
        return reply

    tokens = []
    compl = []
    for a in argv[1:]:
        if len(a) > 1 and "=" in a:
            tokens.extend( a.split("=", 1) )
        elif a != "=":
            tokens.append( a )
    tokens = filter( lambda x: len(x)>0, tokens)
    while tokens:
        l = tokens.pop(0)
        r = tokens.pop(0)
        if l in alias:
            l = alias[l]
        ok = True
        if l not in valid:
            ok = False
        elif not hasattr(server,l):
            ok = False
        if not ok:
            reply += "no server property: {0}\n".format(l)
            continue
        if l == "rcon" and not e.eventtype().startswith( "priv" ):
            reply += "not setting rcon password in public channel\n"
            continue
        server.__setattr__(l,r)
        compl.append(l)
    model.session.commit()
    if len( compl )>0:
        reply += "succesfully set for '{0}': ".format(server.name) + ", ".join(compl)
    return reply.strip()

@admin
@server_required
def delete( c, e, channel, server, command, argv ):
    """
    Delete the selected server.

    For confirmation you are required to execute
    the command twice.
    """
    now = time.time()
    try:
        t = model.Server.delete_cache[channel.id,server.id]
    except KeyError:
        t = 0
    if now-t > 5:
        model.Server.delete_cache[channel.id,server.id] = now
        reply = "Please confirm deletion of server '{0}'".format(server)
        reply += " (same command again within 5 seconds)"
        return reply
    else:
        name = str(server)
        server.delete()
        model.session.commit()
        return "{0} deleted.".format(name)


@server_required
def stats( c, e, channel, server, command, argv ):
    """Display the command 'stats' on selected server."""
    r= server.connection.execute( "stats",
            cb=functools.partial( _ridretstr1_cb, c, e ) )

@server_required
def status( c, e, channel, server, command, argv ):
    """Display query info about the selected server."""
    try:
        info = server.info
    except KeyError:
        return "please wait"
    try:
        n = info['name']
    except KeyError:
        return "no status available"
    reply = "'{name}' playing {mapname} ({players} players)".format(**info)
    if info['password'] == 0x01:
        reply += " password protected"
    return reply

@admin
@server_required
def rcon( c, e, channel, server, command, argv ):
    """Execute a raw rcon command at the selected server."""
    r= server.connection.execute( " ".join(argv[1:]),
            cb=functools.partial( _ridretstr1_cb, c, e ) )

def error( c, e, channel, server, command, argv ):
    return "3 / 0 = {0}".format( 3 / 0 )

def help( c, e, channel, server, command, argv ):
    """Show available commands"""
    import commands
    if len(argv)>1:
        cmd = argv[1].lstrip("!")
        if cmd not in __all__:
            return "no such command or directory: " + cmd
        func = getattr(commands, cmd)
        doc = dedent(func.__doc__ or "no help available.. read source")
        return doc.strip()

    result = {}
    maxlen = 0
    for c in sorted(__all__):
        func = getattr(commands,c)
        if not hasattr( func, "__call__" ):
            continue
        if func.__doc__ is None:
            doc = "n/a"
        else:
            doc = func.__doc__.strip()
        if "\n\n" in doc:
            doc = doc.split("\n\n",1)[0].strip()
        result[c] = (doc, func)
        if len(c) > maxlen:
            maxlen = len(c)
    reply = "Available commands:\n"
    for c in sorted(result.keys()):
        reply += " !{0:<{1}} : {2}\n".format(c,maxlen,result[c][0])
    reply += "type !help <command> for more info"
    return reply


def _ridretstr1_cb(c, e, rid, ret, str1):
    if str1 and isinstance(str1, basestring):
        for line in str1.strip().splitlines():
            c.privmsg( e.target(), line )



# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
