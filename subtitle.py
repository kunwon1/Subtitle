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

maxRetries = 5

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
	def __init__(self, url, channel, ircObject, contextFactory=None, retries=0):
		self.channel = channel
		self.irc = ircObject
		Getter.__init__(self, url,
			contextFactory=contextFactory, retries=retries)

	def Output(self, title):

		### HACK FOR TESTING ###
		if self.channel == '##news':
			self.channel = '###testing'
		########################
		
		msg = '[ ' + title + ' ]'
		
		self.irc.msg(self.channel, msg)
		# Getter.Output(self, title)
		
	def Err(self, fail):
		if self.retries >= maxRetries:
			print 'exceeded maxRetries for ', self.url
		else:
			retryCount = self.retries + 1
			reactor.callLater(retryCount, IRCTitler, self.url,
				self.channel, self.irc, contextFactory=None, retries=retryCount)
			return None
		
		Getter.Err(self, fail)

channels = ['###testing', '##news', '##politics', '##politics-spam']
try:
	channels
except:
	channels = ['###testing']
botnick = 'title'

urlfinder = URLExtractor()
irc = SubtitleFactory(channels, botnick)

reactor.connectTCP("irc.freenode.net", 6667, irc)

reactor.run()
