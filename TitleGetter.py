#!/usr/bin/python

from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.http_headers import Headers
from twisted.python.util import println
from twisted.python.failure import Failure

import sys, re, string, htmlentitydefs

class Getter(Agent):
	def __init__(self, reactor):
		self.cookiePattern = re.compile("^(.+?)=(.+?);")
		Agent.__init__(self, reactor)

	def Get(self, url, context):
		url = stripNoPrint(url)
		try:
			context['cookies']
		except KeyError:
			context['cookies'] = dict()

		if not 'retry_count' in context:
			context['retry_count'] = 0
		elif context['retry_count'] >= 10:
			println('exceeded retry count for ' + str(url))
			return
		else:
			context['retry_count'] += 1
		context['original_url'] = url
		
		cookies = ''
		for k in context['cookies']:
			cookies += k + '=' + context['cookies'][k] + '; '
		
		d = self.request(
			'GET', url,
			Headers({'User-Agent': [
				'Mozilla/5.0 (compatible; Subtitle/0.1)'],
				'Cookie': [cookies]}),
			None)
		
		def addContext(response):
			response.context = context
			return response

		d.addCallback(addContext)
		d.addCallback(self.__checkResponse)
		d.addCallback(self.__extractTitle)
		d.addErrback(self.__err)
		d.addCallback(self.Output)

	def __checkResponse(self, response):
		rcode = str(response.code)
		headers = response.headers
		if headers.hasHeader('set-cookie'):
			cookies = headers.getRawHeaders('set-cookie')
			for c in cookies:
				m = self.cookiePattern.search(c)
				(k, v) = m.group(1, 2)
				println(k + "=" + v)
				response.context['cookies'][k] = v
		if re.match("2", rcode):
			return response
		elif headers.hasHeader('location'):       # we got a redirect
			location = headers.getRawHeaders('location')
			self.Get(location[0], response.context)
			return None
		elif re.match("4", rcode):
			self.Get(response.context['original_url'], response.context)
			return None
		else:
			print 'got something weird'
			print str(headers)
			return response
		
	def __extractTitle(self, response):
		if response is None:
			return None
		finished = Deferred()
		response.deliverBody(TitleGetter(finished, response.context))
		return finished
		
	def __err(self, failure):
		println("an error occurred in the title getter:", failure)
		
	def Output(self, data):
		if data is None:
			return
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
		self.entityPattern = re.compile("&(\w+?);")
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
			title = self.__processTitle(title)
			return title
			
	def __processTitle(self, title):
		title = string.strip(title)
		title = descape_ents(title)
		title = descape_decs(title)
		return title

entityPattern = re.compile("&(\w+?);")
decPattern = re.compile("&#(\d+?);")

def descape_dec(m):
	return chr(int(m.group(1)))
	
def descape_decs(string):
	return decPattern.sub(descape_dec, string)

def descape_entity(m, defs=htmlentitydefs.entitydefs):
    try:
        return defs[m.group(1)]
    except KeyError:
        return m.group(0) # use as is

def descape_ents(string):
    return entityPattern.sub(descape_entity, string)
	
def stripNoPrint(str):
	results = ""
	for char in str:
		if not int(ord(char)) <= 31:
			results += char
	return results

if __name__ == '__main__':
	g = Getter(reactor)
	for n in sys.argv[1:]:
		g.Get(n, dict())
	reactor.run()
