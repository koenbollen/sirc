# [si]rc

from elixir import *
#from sqlalchemy import UniqueConstraint
from sqlalchemy import or_

metadata.bind = "sqlite:///sirc.db"
metadata.bind.echo = True

class User(Entity):
    using_options(tablename='user',inheritance='multi')
    mask = Field(Unicode(512)) # nick!user@hostname

    def __repr__(self):
        return '<User "{0}">'.format(self.mask)

class Owner(User):
    using_options(tablename='owner',inheritance='multi')

    def __repr__(self):
        return '<Owner "{0}">'.format(self.mask)

class Admin(User):
    using_options(tablename='admin',inheritance='multi')
    channel = ManyToOne("Channel")

    def __repr__(self):
        return '<Admin "{0}">'.format(self.mask)

class Channel(Entity):
    using_options(tablename='channel')

    name = Field(Unicode(32))
    key = Field(Unicode(32))
    admins = OneToMany("Admin")
    servers = OneToMany("Server")

    def __repr__(self):
        return '<Channel "{0}">'.format(self.name)

class Server(Entity):
    using_options(tablename='server')

    name = Field(Unicode(32))
    host = Field(Unicode(64))
    port = Field(Integer)
    rcon = Field(Unicode(255))
    config = Field(Unicode(64))
    servertype = Field(Enum( u"normal", u"tv" ))
    channel = ManyToOne("Channel")
    selected = Field(Boolean,default=False)

    def __str__(self):
        is_tv = " (tv)" if self.servertype == "tv" else ""
        return "{name} {host}:{port}{is_tv}".format(
                is_tv=is_tv,**self.__dict__
            )

    def __repr__(self):
        r = '<Server "{0}" ({1}:{2})'.format(self.name,self.host,self.port)
        if self.servertype and self.servertype != "normal":
            r += " {0}".format(self.servertype)
        return r+">"

    @classmethod
    def search(cls, text, ch=None):
        text = unicode("%{0}%".format(text))
        query = Server.query.filter(
                or_(Server.name.like(text),Server.host.like(text))
            )
        if ch is not None:
            query = query.filter(Server.channel==ch)
        return query

    @classmethod
    def select(cls, ch ):
        return Server.query.filter_by(channel=ch).filter(Server.selected==True)

def test():
    create = False
    if len(Admin.query.all()) <= 0:
        create = True
    c = Channel( name="#sirc_test" )
    a = Admin(mask="Kaji!koen@xkcd.nl.smurfnet.ch")
    c.admins.append( a )
    s = Server( name="dummy",
            host="localhost", port=27015,
            rcon="not so secret", config="file://default.cfg"
        )
    c.servers.append(s)
    if create:
        print "committing.."
        session.commit()

if __name__ == "__main__":
    setup_all(True)
    test()

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
