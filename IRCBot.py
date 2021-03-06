# Copyright (c) 2010 David Moore.
# See LICENSE for details.

from twisted.words.protocols import irc
from twisted.internet import reactor, protocol

import time

class IRCBot(irc.IRCClient):
	"""An IRC bot."""
	
	def connectionMade(self):
		self.nickname = self.factory.botnick
		irc.IRCClient.connectionMade(self)
		print "[connected at %s]" % time.asctime(time.localtime(time.time()))

	def connectionLost(self, reason):
		irc.IRCClient.connectionLost(self, reason)
		print "[disconnected at %s]" % time.asctime(time.localtime(time.time()))

	# callbacks for events

	def signedOn(self):
		"""Called when bot has succesfully signed on to server."""
		
		print "[Signed on at %s]" % time.asctime(time.localtime(time.time()))
		for channel in self.factory.channels:
			self.join(channel)

	def privmsg(self, user, channel, msg):
		"""This will get called when the bot receives a message."""
		user = user.split('!', 1)[0]
		
		if channel == self.nickname:
			print "PRIV: <%s> %s" % (user, msg)
			return

	def action(self, user, channel, msg):
		"""This will get called when the bot sees someone do an action."""
		user = user.split('!', 1)[0]

		if channel == self.nickname:
			print "PRIV: * %s %s" % (user, msg)
			return

	def alterCollidedNick(self, nickname):
		"""
		Generate an altered version of a nickname that caused a collision in an
		effort to create an unused related name for subsequent registration.
		"""
		return nickname + '1'

class IRCBotFactory(protocol.ClientFactory):
	"""A factory for IRCBots.

	A new protocol instance will be created each time we connect to the server.
	"""

	# the class of the protocol to build when new connection is made
	protocol = IRCBot

	def __init__(self, channels, botnick):
		self.channels = channels
		self.botnick = botnick

	def clientConnectionLost(self, connector, reason):
		"""If we get disconnected, reconnect to server."""
		connector.connect()

	def clientConnectionFailed(self, connector, reason):
		print "connection failed:", reason
		reactor.callLater(90, connector.connect())

if __name__ == '__main__':
	# create factory protocol and application
	channels = ['###testing']
	botnick = 'title'
	
	f = IRCBotFactory(channels, botnick)

	# connect factory to this host and port
	reactor.connectTCP("irc.freenode.net", 6667, f)

	# run bot
	reactor.run()
