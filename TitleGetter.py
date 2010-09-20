#!/usr/bin/python

from twisted.internet import reactor
from twisted.web.client import Agent
from twisted.internet.defer import Deferred
from twisted.internet.protocol import Protocol
from twisted.web.http_headers import Headers
from twisted.python.util import println
from twisted.python.failure import Failure

import sys, re, string, htmlentitydefs

entityPattern = re.compile("&(\w+?);")
decPattern = re.compile("&#(\d+?);")
whitespacePattern = re.compile("\s+")
titlePattern = re.compile(r'<title>(.*?)</title>', re.S | re.I )
cookiePattern = re.compile("^(.+?)=(.*?);")

entityDefs = htmlentitydefs.entitydefs

class Getter(Agent):
	""" A title fetcher """
	
	def __init__(self, reactor):
		Agent.__init__(self, reactor)

	def Get(self, url, context, maxRetries=10):
		""" Start the lookup process for a title.
		
		context dict stores any information that has to
		come back with the response object
		
		context['cookies']:
			type dict
			cookie jar
			
		context['retry_count']:
			type int
			number of retries used so far
			
		context['original_url']:
			type str
			original url, in case we have to retry after
			following redirects
		
		maxRetries defines the maximum number of times
		we retry the fetch after a 4xx or 5xx response code
		
		Returns deferred."""
		
		url = stripNoPrint(url)
		println('Get: ' + url)
		try:
			context['cookies']
		except KeyError:
			context['cookies'] = dict()

		if not 'retry_count' in context:
			context['retry_count'] = 0
		elif context['retry_count'] >= maxRetries:
			println('exceeded max retry count for ' + str(url))
			return
		else:
			context['retry_count'] += 1
		context['original_url'] = url
		
		cookies = ''
		for k in context['cookies']:
			cookies += k + '=' + context['cookies'][k] + '; '
		
		d = self.request('GET', url, Headers({
				'User-Agent': ['Mozilla/5.0 (compatible; Subtitle/0.1)'],
				'Cookie': [cookies]
				}),	None)
		
		def addContext(response):
			response.context = context
			return response

		d.addCallback(addContext)
		d.addCallback(self.__checkResponse)
		d.addCallback(self.__extractTitle)
		d.addErrback(self.__err)
		d.addCallback(self.Output)

	def __checkResponse(self, response):
		""" Checks the response from an http get and
		takes appropriate actions based on that response.
		
		should only be used as a callback attached to deferred
		returned by Get()
		
		Returns response object."""
		
		rcode = str(response.code)
		headers = response.headers
		if headers.hasHeader('set-cookie'):
			cookies = headers.getRawHeaders('set-cookie')
			for c in cookies:
				m = cookiePattern.search(c)
				(k, v) = m.group(1, 2)
				response.context['cookies'][k] = v
		if re.match("2", rcode):
			return response
		elif headers.hasHeader('location'):       # we got a redirect
			self.Get(headers.getRawHeaders('location')[0], response.context)
			return None
		elif re.match("4|5", rcode):
			self.Get(response.context['original_url'], response.context)
			return None
		else:
			print 'got something weird'
			print str(headers)
			return response
		
	def __extractTitle(self, response):
		""" We need to fire another deferred to get the body
		
		this method handles that.
		returns deferred. """
		
		if response is None:
			return
		finished = Deferred()
		response.deliverBody(TitleGetter(finished, response.context))
		return finished
		
	def __err(self, failure):
		println("an error occurred in the title getter:", failure)
		
	def Output(self, data):
		""" default Output method.
		
		Should be overridden, ancestor can be called for debugging
		Should be at the end of the callback chain """
		
		if data is None:
			return
		title, context = data[:2]
		println(title + ' ' + str(context))
		
class TitleGetter(Protocol):
	""" Body handler class
	
	gets the title from the body"""
	
	def __init__(self, finished, context):
		self.context = context
		self.finished = finished
		self.remaining = 1024 * 1024
		self.bodyStr = ''
		self.titleSent = 0

	def dataReceived(self, bytes):
		""" Gets a chunk of data and checks it for a title
		
		if no title, adds the chunk to the bodystring
		
		does not return, if title is found, returns control
		to the callback chain """
		
		if self.remaining:
			chunk = bytes[:self.remaining]
			title = extractTitle(chunk)
			if title and self.titleSent == 0:
				self.titleSent = 1
				self.finished.callback([title, self.context])
			self.bodyStr = self.bodyStr + chunk
			self.remaining -= len(chunk)

	def connectionLost(self, reason):
		""" We've got every byte we're going to get,
		check for title now in case it was split between
		two chunks sent to dataReceived
		
		does not return, if title is found, returns control
		to the callback chain """
		
		title = extractTitle(self.bodyStr)
		if title and self.titleSent == 0:
			self.titleSent = 1
			self.finished.callback([title, self.context])

def extractTitle(body):
	""" Extracts everything between title tags
	
	returns string """
	
	m = titlePattern.search(body)
	if m:
		title = m.group(1)
		title = processTitle(title)
		return title

def processTitle(title):
	""" performs miscellaneous processing on title 
	
	returns string """
	
	title = string.strip(title)
	title = descape_ents(title)
	title = descape_decs(title)
	title = normalizeWhitespace(title)
	return title

def descape_dec(m):
	""" de-escape one html decimal entity 
	
	ex: &#34;

	returns string """
	
	return chr(int(m.group(1)))
	
def descape_ent(m, defs=entityDefs):
	""" de-escape one html named entity
	
	ex: &quot; 
	
	returns string """
	
	try:
		return defs[m.group(1)]
	except KeyError:
		return m.group(0) # use as is
	
def descape_decs(string):
	""" de-escape all decimal entities in a string
	
	returns string """
	
	return decPattern.sub(descape_dec, string)

def descape_ents(string):
	""" de-escape all named entities in a string
	
	returns string """
	
	return entityPattern.sub(descape_ent, string)
	
def stripNoPrint(str):
	""" strips non-printable characters from a string
	
	***this function is incomplete, it works for our
	current needs - obviously there are other non-printable
	characters besides those below ascii 32***
	
	returns string """
	
	results = ""
	for char in str:
		if not int(ord(char)) <= 31:
			results += char
	return results
	
def normalizeWhitespace(str):
	""" replaces sequential whitespaces with a single space
	
	returns string """
	
	str = re.sub(whitespacePattern, ' ', str)
	return str

if __name__ == '__main__':
	g = Getter(reactor)
	for n in sys.argv[1:]:
		g.Get(n, dict())
	reactor.run()
