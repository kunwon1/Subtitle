# Copyright (c) 2010 David Moore.
# See LICENSE for details.

from twisted.internet import reactor
from twisted.web.client import HTTPClientFactory, _parse, HTTPPageGetter
from twisted.python.util import println
from twisted.python.failure import Failure
from BeautifulSoup import BeautifulSoup, SoupStrainer

import sys, re, string, htmlentitydefs

ttags = SoupStrainer('title')

entityPattern = re.compile("&(\w+?);")
decPattern = re.compile("&#(\d+?);")
whitespacePattern = re.compile("\s+")
charsetPattern = re.compile(r'charset=([^\s]+)', re.I)

class CustomPageGetter(HTTPPageGetter):
	def dataReceived(self, data):
		try:
			self.detectedDelimiter
		except AttributeError:
			if data.find("\r\n") >= 0:
				self.detectedDelimiter = 1
			else:
				self.detectedDelimiter = 1
				self.delimiter = "\n"
		return HTTPPageGetter.dataReceived(self, data)

class Getter(HTTPClientFactory):
	""" A title fetcher
	
	A new class is instantiated for each title fetch.
	Subclasses HTTPClientFactory. 
	
	Takes one mandatory argument and one optional argument.
	
	url = the url to fetch the title of (mandatory)
	contextFactory = SSL context factory (optional)
	
	output is handled by the callback chain, standard practice is to override
	the Output method, which will be called with the title.  Output will never
	get None as an arg."""
	
	protocol = CustomPageGetter
	
	def __init__(self, url, contextFactory=None, retries=0):

		url = stripNoPrint(url)
		if retries > 0:
			print "Retrying: ", url
		else:
			print "Get: ", url
		self.retries = retries
		self.url = url
		self.charset = None
		scheme, host, port, path = _parse(url)
		HTTPClientFactory.__init__(self, url,
			method='GET', postdata=None, headers=None,
			agent='Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US;' + 
				' rv:1.9.2.10) Gecko/20100914 Firefox/3.6.10')
		if scheme == 'https':
			from twisted.internet import ssl
			if contextFactory is None:
				contextFactory = ssl.ClientContextFactory()
			reactor.connectSSL(host, port, self, contextFactory)
		else:
			reactor.connectTCP(host, port, self)
		
		self.deferred.addCallbacks(self.getCharset, self.Err)
		self.deferred.addCallbacks(self.getTitle, self.Err)

	def getCharset(self, body):
		"""This is inserted in the callback chain before getTitle to get any
		data we'll need for the actual title extraction. Currently just gets
		and stores charset.
		
		returns the body it's passed, unmodified"""
		
		h = self.response_headers

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
		if body is None:
			return
		if not self.charset is None:
			soup = BeautifulSoup(
				body, fromEncoding=self.charset, parseOnlyThese=ttags)
		else:
			soup = BeautifulSoup(body, parseOnlyThese=ttags)
		try:
			soup.title.string
		except AttributeError:
			print 'Got no title from soup: ', self.url
			return
		title = soup.title.string
		if not title is None:
			title = string.strip(title)
			title = descape_ents(title)
			title = descape_decs(title)
			title = normalizeWhitespace(title)
			title = title.encode("utf-8", "ignore")
			if not title is None:
				self.Output(title)
			else:
				print 'Got no title for url after string processing: ', self.url
		else:
			print 'Found no title string for url: ', self.url

	def Output(self, title):
		""" default Output method.
		
		Should be overridden, ancestor can be called for debugging
		Should be at the end of the callback chain """

		print title
		
	def Err(self, fail):
		""" error handler """
		
		print 'Error in the titlegetter for url ' + self.url + ' - ' + str(fail)

def descape_dec(m):
	""" de-escape one html decimal entity 
	
	ex: &#34;

	returns string """
	
	return unichr(int(m.group(1)))
	
def descape_ent(m, defs=htmlentitydefs.name2codepoint):
	""" de-escape one html named entity
	
	ex: &quot; 
	
	returns string """

	try:
		return unichr(defs[m.group(1)])
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
