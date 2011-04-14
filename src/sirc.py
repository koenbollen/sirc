#!/usr/bin/env python
# [si]rc

import model

if __name__ == "__main__":
    model.metadata.bind.echo = False
    model.setup_all(True)
    channels = model.Channel.query.all()
    if len(channels) < 1:
        print "no channels, creating.."
        c = model.Channel( name=u"#test" )
        c.admins.append( model.Admin( mask=u"Kaji!koen@koen.it" ) )
        model.session.commit()
        channels = model.Channel.query.all()
    for c in channels:
        print c, c.admins, c.servers

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
