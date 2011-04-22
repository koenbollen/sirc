#!/usr/bin/env python
#

import logging
import model
import sirc
import sqlalchemy


def list( c, e, channel, server, command, argv ):
    logging.debug( "!list " + repr(argv) )
    return repr(channel.servers)


@sirc.admin
@sirc.private
def add( c, e, channel, server, command, argv ):
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
        model.Server.query.filter_by( channel=channel, name=argv[1] ).all()
        return "server '{0}' exists!".format(argv[1])
    except sqlalchemy.orm.exc.NoResultFound:
        s = None
    s = model.Server( channel=channel, **info )
    model.session.commit()
    return "server '{0}' created!".format(s.name)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
