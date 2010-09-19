#!/usr/bin/python
# Copyright (c) 2010 David Moore.
# See LICENSE for details.

from twisted.internet import reactor

from TitleGetter import TitleGetter
from IRCBot import IRCBotFactory

channels = ['###testing']
botnick = 'title345'

titler = TitleGetter(reactor)
irc = IRCBotFactory(channels, botnick)

reactor.connectTCP("irc.freenode.net", 6667, f)

reactor.run()
