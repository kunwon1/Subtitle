#!/usr/bin/python

from twisted.internet import reactor
from twisted.web.client import getPage
from twisted.python.util import println

import sys, re, string, htmlentitydefs, logging

titlePattern = re.compile(r'<title>(.*?)</title>', re.S | re.I )
entityPattern = re.compile("&(\w+?);")
decPattern = re.compile("&#(\d+?);")
whitespacePattern = re.compile("\s+")

logging.basicConfig(filename='error.log', level=logging.DEBUG)

class Getter:
	""" A title fetcher """
	
	def __init__(self, url):
		"""TODO"""
		
		url = stripNoPrint(url)
		getPage(url).addCallbacks(self.getTitle, self.__err)


	def getTitle(self, body):
		"""TODO"""
	
		m = titlePattern.search(body)
		if m:
			title = m.group(1)
			title = string.strip(title)
			title = descape_ents(title)
			title = descape_decs(title)
			title = normalizeWhitespace(title)
			self.Output(title)

	def Output(self, title):
		""" default Output method.
		
		Should be overridden, ancestor can be called for debugging
		Should be at the end of the callback chain """
		
		if title is None:
			return None
		print title
	
	def __err(fail):
		logging.debug('Error in the titlegetter:')
		logging.debug(str(fail))

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
