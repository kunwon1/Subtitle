# Copyright (c) 2010 David Moore.
# See LICENSE for details.

import re

class URLExtractor:
	def __init__(self):
		self.re = re.compile( r'(https?://\S+)', re.I )
		
	def Extract(self, text):
		urls = self.re.findall(text)
		return urls
