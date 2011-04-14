# [si]rc

from elixir import *

metadata.bind = "sqlite:///sirc.db"
metadata.bind.echo = True

class User(Entity):
    using_options(inheritance='multi')
    mask = Field(Unicode(512)) # nick!user@hostname

    def __repr__(self):
        return '<User "{0}">'.format(self.mask)

class Owner(User):
    using_options(inheritance='multi')

    def __repr__(self):
        return '<Owner "{0}">'.format(self.mask)

class Admin(User):
    using_options(inheritance='multi')
    channel = ManyToOne("Channel")

    def __repr__(self):
        return '<Admin "{0}">'.format(self.mask)

class Channel(Entity):
    name = Field(Unicode(32))
    key = Field(Unicode(32))
    admins = OneToMany("Admin")
    servers = OneToMany("Server")

    def __repr__(self):
        return '<Channel "{0}">'.format(self.name)

class Server(Entity):
    host = Field(Unicode(32))
    port = Field(Integer)
    rcon = Field(Unicode(255))
    config = Field(Unicode(64))
    servertype = Field(Enum( u"normal", u"tv" ))
    channel = ManyToOne("Channel")

    def __repr__(self):
        r = '<Server "{0}:{1}"'.format(self.host,self.port)
        if self.servertype and self.servertype != "normal":
            r += " {0}".format(self.servertype)
        return r+">"

def test():
    a = Admin(mask="nick!user@example.com")
    c = Channel( name="#sirc_test", key="secret" )
    c.admins.append( a )
    s = Server(
            host="localhost", port=27015,
            rcon="also a secret", config="local://default.cfg"
        )
    #c.servers.append(s)

# vim: expandtab tabstop=4 softtabstop=4 shiftwidth=4 textwidth=79:
