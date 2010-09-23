#!/usr/bin/python
# Copyright (c) 2010 David Moore.
# See LICENSE for details.
import psyco
psyco.full()

from twisted.internet import reactor

from Credentials import ServerPassword
from TitleGetter2 import Getter
from URLExtractor import URLExtractor
from IRCBot import IRCBotFactory, IRCBot

import sys

class Subtitle(IRCBot):
	password = ServerPassword

	def privmsg(self, user, channel, msg):
		urls = urlfinder.Extract(msg)
		context = {'channel':channel, 'irc':self}
		for url in urls:
			IRCTitler(url, channel, self)
		IRCBot.privmsg(self, user, channel, msg)

class SubtitleFactory(IRCBotFactory):
	protocol = Subtitle

	def __init__(self, channels, botnick):
		IRCBotFactory.__init__(self, channels, botnick)
		
class IRCTitler(Getter):
	def __init__(self, url, channel, ircObject):
		self.channel = channel
		self.irc = ircObject
		Getter.__init__(self, url)

	def Output(self, title):

		### HACK FOR TESTING ###
		if self.channel == '##news':
			self.channel = '###testing'
			
		# if self.channel == '##politics':
			# self.channel = '###testing'

		########################
		
		msg = '[ ' + title + ' ]'
		
		self.irc.msg(self.channel, msg)
		# Getter.Output(self, title)

channels = ['###testing', '##news', '##politics']
botnick = 'title'

urlfinder = URLExtractor()
irc = SubtitleFactory(channels, botnick)

reactor.connectTCP("irc.freenode.net", 6667, irc)

reactor.run()
