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
cookiePattern = re.compile("^(.+?)=([^;]+);?")
charsetPattern = re.compile(r'charset=([^\s]+)', re.I)
domainPattern = re.compile(r'^(https?://[^/]+)', re.I)
metaCharsetPattern = re.compile(
	"meta http-equiv=\"content-type\".+?charset=([^\s]+)", re.I)

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
			
		context['charset']:
			type str
			charset received from server, so we can convert
			to utf-8
			
		context ['domain']:
			type str
			stores the scheme and domain portion of the url
			in case we get a relative redirect
		
		maxRetries defines the maximum number of times
		we retry the fetch after a 4xx or 5xx response code
		
		Returns deferred."""
		
		url = stripNoPrint(url)
		println('Get: ' + url)
		
		m = domainPattern.search(url)
		context['domain'] = m.group(1)
		
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
		if headers.hasHeader('content-type'):
			ctype = [headers.getRawHeaders('content-type')][0][0]
			m = charsetPattern.search(ctype)
			if not m is None:
				response.context['charset'] = m.group(1)
		if headers.hasHeader('set-cookie'):
			cookies = headers.getRawHeaders('set-cookie')
			print str(cookies) + "\n\n"
			for c in cookies:
				m = cookiePattern.search(c)
				(k, v) = m.group(1, 2)
				response.context['cookies'][k] = v
		if rcode.startswith('2'):
			return response
		elif headers.hasHeader('location'):       # we got a redirect
			location = headers.getRawHeaders('location')[0]
			domain = response.context['domain']
			if not location.startswith('http'):
				if not domain.startswith('/'):
					location = domain + '/' + location
				else:
					location = domain + location
			self.Get(location, response.context)
			return None
		elif rcode.startswith('4') or rcode.startswith('5'):
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
			return None
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
			return None
		title, context = data[:2]
		print title + ' ' + str(context)
		
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
			title = self.extractTitle(chunk)
			charset = getCharsetFromMetaTag(chunk)
			if not charset is None:
				self.context['charset'] = charset
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
		
		title = self.extractTitle(self.bodyStr)
		charset = getCharsetFromMetaTag(self.bodyStr)
		if not charset is None:
			self.context['charset'] = charset
		if title and self.titleSent == 0:
			self.titleSent = 1
			self.finished.callback([title, self.context])

	def extractTitle(self, body):
		""" Extracts everything between title tags
	
		returns string """
	
		m = titlePattern.search(body)
		if m:
			title = m.group(1)
			try:
				self.context['charset']
			except KeyError:
				pass
			else:
				c = self.context['charset']
				c = c.lower()
				if not c.startswith('utf8') and not c.startswith('utf-8'):
					title = unicode(
						title, self.context['charset'], errors='replace')
				else:
					title = unicode(title, 'utf8', errors='replace')
			if not isinstance(title, unicode):
				title = unicode(title, 'utf8', errors='replace')
			title = processTitle(title)
			title = title.encode("utf-8", "ignore")
			return title
			
def getCharsetFromMetaTag(str):
	""" looks for a meta http-equiv content-type tag
	and gets the charset from it
	
	returns string"""
	m = metaCharsetPattern.search(str)
	if m:
		charset = m.group(1)
		return charset

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
	
	return unichr(int(m.group(1)))
	
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
