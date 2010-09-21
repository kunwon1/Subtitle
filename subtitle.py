#!/usr/bin/python
# Copyright (c) 2010 David Moore.
# See LICENSE for details.

from twisted.internet import reactor

from Credentials import ServerPassword
from TitleGetter import Getter
from URLExtractor import URLExtractor
from IRCBot import IRCBotFactory, IRCBot

class Subtitle(IRCBot):
	password = ServerPassword

	def privmsg(self, user, channel, msg):
		urls = urlfinder.Extract(msg)
		context = {'channel':channel, 'irc':self}
		for url in urls:
			titler.Get(url, context)
		IRCBot.privmsg(self, user, channel, msg)

class SubtitleFactory(IRCBotFactory):
	protocol = Subtitle

	def __init__(self, channels, botnick):
		IRCBotFactory.__init__(self, channels, botnick)
		
class IRCTitler(Getter):
	def __init__(self, reactor):
		Getter.__init__(self, reactor)

	def Output(self, data):
		if data is None:
			return

		title = data[0]
		if not isinstance(title, unicode):
			title = unicode(title, 'utf8', errors='replace')
		title = title.encode("utf-8", "ignore")
		context = data[1]
		channel = context['channel']
		
		### HACK FOR TESTING ###
		if channel == '##news':
			channel = '###testing'
			
		if channel == '##politics':
			channel = '###testing'
		########################
		
		irc = context['irc']
		
		msg = '[ ' + title + ' ]'
		
		irc.msg(channel, msg)
		# Getter.Output(self, data)

channels = ['###testing']
botnick = 'title'

urlfinder = URLExtractor()
titler = IRCTitler(reactor)
irc = SubtitleFactory(channels, botnick)

reactor.connectTCP("irc.freenode.net", 6667, irc)

reactor.run()
