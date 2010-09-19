#!/usr/bin/python

from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.http_headers import Headers
from twisted.python.util import println

from string import strip
import sys
import re

class Getter(Agent):
	def __init__(self, reactor):
		Agent.__init__(self, reactor)

	def Get(self, url, context):
		d = self.request(
			'GET', url,
			Headers({'User-Agent': [
				'Mozilla/5.0 (compatible; Subtitle/0.1)']}),
			None)
		
		def addContext(response):
			response.context = context
			return response

		d.addCallback(addContext)
		d.addCallback(self.__extractTitle)
		d.addErrback(self.__err)
		d.addCallback(self.Output)

	def __extractTitle(self, response):
		finished = Deferred()
		response.deliverBody(TitleGetter(finished, response.context))
		return finished
		
	def __err(self, failure):
		println("an error occurred", failure)
		
	def Output(self, data):
		title = data[0]
		context = data[1]
		println(title + ' ' + str(context))
		
class TitleGetter(Protocol):
	def __init__(self, finished, context):
		self.context = context
		self.finished = finished
		self.remaining = 1024 * 1024
		self.titlePattern = re.compile(
			r'<title>(.*?)</title>', re.S | re.I )
		self.bodyStr = ''
		self.titleSent = 0

	def dataReceived(self, bytes):
		if self.remaining:
			chunk = bytes[:self.remaining]
			title = self.__extractTitle(chunk)
			if title and self.titleSent == 0:
				self.titleSent = 1
				self.finished.callback([title, self.context])
			self.bodyStr = self.bodyStr + chunk
			self.remaining -= len(chunk)

	def connectionLost(self, reason):
		title = self.__extractTitle(self.bodyStr)
		if title and self.titleSent == 0:
			self.titleSent = 1
			self.finished.callback([title, self.context])
		
	def __extractTitle(self, body):
		m = self.titlePattern.search(body)
		if m:
			title = m.group(1)
			title = strip(title)
			return title
			
if __name__ == '__main__':
	g = Getter(reactor)
	for n in sys.argv[1:]:
		g.Get(n, 'context data')
	reactor.run()
