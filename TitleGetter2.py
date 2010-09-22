#!/usr/bin/python

from twisted.internet import reactor
from twisted.web.client import HTTPClientFactory, _parse
from twisted.python.util import println

import sys, re, string, htmlentitydefs, logging

titlePattern = re.compile(r'<title>(.*?)</title>', re.S | re.I )
entityPattern = re.compile("&(\w+?);")
decPattern = re.compile("&#(\d+?);")
whitespacePattern = re.compile("\s+")
charsetPattern = re.compile(r'charset=([^\s]+)', re.I)

logging.basicConfig(filename='error.log', level=logging.DEBUG)

class Getter(HTTPClientFactory):
	""" A title fetcher
	
	A new class is instantiated for each title fetch.
	Sublcasses HTTPClientFactory. 
	
	Takes one mandatory argument and one optional argument.
	
	url = the url to fetch the title of (mandatory)
	contextFactory = SSL context factory (optional)
	
	output is handled by the callback chain, standard practice is to override
	the Output method, which will be called with the title.  Output will never
	get None as an arg."""
	
	def __init__(self, url, contextFactory=None):
		
		url = stripNoPrint(url)
		scheme, host, port, path = _parse(url)
		HTTPClientFactory.__init__(self, url,
			method='GET', postdata=None, headers=None,
			agent='Mozilla/5.0 (compatible; Subtitle/0.3)')
		if scheme == 'https':
			from twisted.internet import ssl
			if contextFactory is None:
				contextFactory = ssl.ClientContextFactory()
			reactor.connectSSL(host, port, self, contextFactory)
		else:
			reactor.connectTCP(host, port, self)
		
		self.deferred.addCallbacks(self.getCharset, self.__err)
		self.deferred.addCallbacks(self.getTitle, self.__err)

	def getCharset(self, body):
		"""This is inserted in the callback chain before getTitle to get any
		data we'll need for the actual title extraction. Currently just gets
		and stores charset.
		
		returns the body it's passed, unmodified"""
		
		h = self.response_headers
		self.charset = None

		if h.has_key('content-type'):
			for item in h['content-type']:
				m = charsetPattern.search(item)
				if not m is None:
					self.charset = m.group(1)
			
		return body
		
	def getTitle(self, body):
		"""Shouldn't be called directly. Called in the callback chain from
		__init__. 
		
		Gets page body as arg, searches for, and normalizes title.
		
		Converts to unicode from whichever encoding is specified by the
		content-type response header, removes undesirable whitespace, de-escapes
		entities, and stuffs it all back into a bytestring
		
		returns bytestring """

		m = titlePattern.search(body)
		if m:
			title = m.group(1)
			if not self.charset is None:
				c = self.charset.lower()
				if not c.startswith('utf8') and not c.startswith('utf-8'):
					title = unicode(title, self.charset, errors='replace')
				else:
					title = unicode(title, 'utf8', errors='replace')
			if not isinstance(title, unicode):
				title = unicode(title, 'utf8', errors='replace')

			title = string.strip(title)
			title = descape_ents(title)
			title = descape_decs(title)
			title = normalizeWhitespace(title)
			title = title.encode("utf-8", "ignore")
			if not title is None:
				self.Output(title)

	def Output(self, title):
		""" default Output method.
		
		Should be overridden, ancestor can be called for debugging
		Should be at the end of the callback chain """

		print title
		
	def __err(self, fail):
		""" error logging and output
		
		logs errors and outputs them w/print"""
		
		logging.debug('Error in the titlegetter:')
		logging.debug(str(fail))
		print 'Error in the titlegetter: ' + str(fail)

def descape_dec(m):
	""" de-escape one html decimal entity 
	
	ex: &#34;

	returns string """
	
	return unichr(int(m.group(1)))
	
def descape_ent(m, defs=htmlentitydefs.entitydefs):
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
	for n in sys.argv[1:]:
		Getter(n)
	reactor.run()
