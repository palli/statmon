#!/usr/bin/python

import sys
import time
import copy
import datetime
import os

# Null Logger
class NullLogger:
	def _reset(self): pass
	def _close(self): pass
	def start(self,text='',reset=False): pass
	def format(self, delta):
		""" Format time difference. Returns 'XXXXUU'.
		Where XXXX is the time and UU is the unit type, (m)illi(s)ec, (s)sec, (m)inutes, (h)ours"""

		if delta < 10: dur = '%dms' % (delta * 1000)
		elif delta < 100: dur = '%.1fs ' % delta
		elif delta < 100*60: dur = '%.1fm ' % (delta / 60.0)
		else: dur = '%.1fh ' % (delta / 60.0 / 60.0)
		return dur
	def end(self,text=None,close=False): pass
	def show(self,text=None,prefix=None): pass
	def flush(self): pass

def testXML():
	test = XMLLogger(filename='/tmp/test.xml')

	test.start('root')
	test.start('sub')
	test.show('foo')
	test.end('sub end')
	test.end('root end')
	
	test.start('root')
	test.start('sub')
	test.end('root end',close=True)

	test.start('root2')
	test.start('sub2')
	test.show('foo2')
	test.end('sub end2')
	test.end('root end2')
	
	test.flush()

import xml.dom.minidom
import xml.dom.ext
class XMLLogger(NullLogger):
	def __init__(self,filename):
		self.actions = []
		self.doc = xml.dom.minidom.Document()
		self.root = self.doc.createElement('log')
		self.doc.appendChild( self.root )
		self.actions.append( self.root )
		self.root.setAttribute('orginalStartTime',self._getTimeString())
		self.root.setAttribute('sessionStartTime',self._getTimeString())
		self.filename = filename
		self.entries = 0
		self.success = 0
		self.failed = 0
		self.resumed = 0
		self.flushed = 0
		self.delta = 0.0
	def _getCurrentAction(self,pop=False,close=False):
		while close and len(self.actions) > 2:
			self.actions[-1].setAttribute('endFlag','failed')
			self.actions[-2].setAttribute('endFlag','failed')
			self.end(text='log.end() not called? assuming failure!')
		ret = self.doc
		if self.actions:
			if pop: return self.actions.pop()
			ret = self.actions[-1]
		return ret

	def start(self,text=None,reset=False):
		action = self.doc.createElement('action')
		action.setAttribute('startTime',self._getTimeString())
		if text:
			action.setAttribute('startMsg',text)
		self._getCurrentAction().appendChild( action )
		self.actions.append( action )

	def end(self,text=None,close=False):
		action = self._getCurrentAction(pop=True,close=close)
		action.setAttribute('endTime',self._getTimeString())
		delta = float(action.getAttribute('endTime'))-float(action.getAttribute('startTime'))
		action.setAttribute('deltaTime',self._getTimeString(delta))
		if text:
			action.setAttribute('endMsg',text)
		if not action.hasAttribute('endFlag'):
			action.setAttribute('endFlag','success')
		
		if len(self.actions)<2:
			self.entries += 1
			endFlag = action.getAttribute('endFlag')
			if endFlag == 'success': self.success += 1
			elif endFlag == 'failed': self.failed += 1
			self.delta += delta
		if close:
			self.flush()

	def show(self,text=None,prefix=None):
		if text:
			message = self.doc.createElement('message')
			text = self.doc.createTextNode( text )
			message.appendChild( text )
			if prefix:
				message.setAttribute('prefix',prefix)
			self._getCurrentAction().appendChild( message )

	def _getTimeString(self,ts=None):
		if not ts: ts = time.time()
		return '%020.10f' % ts

	def flush(self):
		if len(self.actions) > 1:
			self.actions[-1].setAttribute('endFlag','failed')
			self.end(text='log.end() not called? flush forced?!',close=True)
			return

		class PsudoStream:
			def __init__(self,file):
				self.file = file
				self.newHead = False
				self.updatingHead = False
				self.newPos = 0
			def write(self,data):
				if self.newHead and data[0:6] == '<?xml ':
					self.file.seek(0)
					self.updatingHead = True
				if 1:
					self.file.write(data)
				if self.updatingHead and data == '>':
					self.updatingHead = False
					self.newHead = False
					self.file.seek(self.newPos,2)
					self.file.write('\t<!-- log flushed -->')
			def read(self,length): return self.file.read(length)
			def close(self): self.file.close()
			def seek(self,pos,whence=0): self.file.seek(pos,whence)

		file = None
		self.filename = str(self.filename)
		if os.path.isfile(self.filename):
			# open existing
			file = PsudoStream(open(self.filename,'rb+'))
		else:
			# create new
			file = PsudoStream(open(self.filename,'wb+'))

		self._update(file)

		xml.dom.ext.PrettyPrint(self.doc,stream=file,indent='\t')
		while self.root.firstChild:
			self.root.removeChild(self.root.firstChild)

		file.close()
	
	def _update(self,file):
		file.seek(0)
		start = file.read(512)
		if start:
			assert(start[0:6] == '<?xml ')
			file.newHead = True
			if len(start) < 512:
				end = start
			else:
				file.seek(-512,2)
				end = file.read(512)
			logEnd = end.rfind('</log>')
			if logEnd > -1:
				file.newPos = logEnd-len(end)

			orginalStartTime = self._getAttribute(start,'orginalStartTime')
			if orginalStartTime != self.root.getAttribute('orginalStartTime'):
				self.root.setAttribute('orginalStartTime',orginalStartTime)
				self.entries += int(self._getAttribute(start,'entries'))
				self.success += int(self._getAttribute(start,'success'))
				self.failed += int(self._getAttribute(start,'failed'))
				self.resumed += int(self._getAttribute(start,'resumed')) + 1
				self.flushed += int(self._getAttribute(start,'flushed'))
				self.delta += delta(self._getAttribute(start,'deltaTime'))

		self.flushed += 1
		self.root.setAttribute('lastFlushTime',self._getTimeString())
		self.root.setAttribute('entries','%06d' % self.entries)
		self.root.setAttribute('success','%06d' % self.success)
		self.root.setAttribute('failed','%06d' % self.failed)
		self.root.setAttribute('resumed','%06d' % self.resumed)
		self.root.setAttribute('flushed','%06d' % self.flushed)
		self.root.setAttribute('deltaTime',self._getTimeString(self.delta))
		assert(self.success+self.failed==self.entries)

	def _getAttribute(self,text,attribute):
		attribute += '=\''
		startPos = text.find(attribute)
		assert(startPos>-1)
		startPos+=len(attribute)
		endPos = text.find('\'',startPos)
		return text[startPos:endPos]

# Simple 'flow' logger
class Logger(NullLogger):
	"""Simple 'flow' logger, mostly for unit testing to observ flow and duration of
	operations in real time. Call start(msg) at start of operation and end() at
	completeion"""
	
	def __init__(self):
		Logger._reset(self)

	def _reset(self):
		self.width = 50
		self.timers = []
		self.indent = 0
		self.length = 0
		self.unflushed = False

	def start(self, text,reset=False):
		"""Call at start of operation with short description of operation about to start"""
		if reset: self._reset()

		self.timers.append(time.time())
		if self.unflushed: self.output( '\n' )
		text = '| ' * self.indent + text
		self.output(text)
		sys.stdout.flush()
		self.indent += 1
		self.length = len(text)
		self.unflushed = True

		if(self.length > self.width):
			self.output('\n')
			self.unflushed = False
			#self.show("start() description too long !!", '!!' )

	def end(self, text = '',close=False):
		"""Call at end of operation with option short description of operation result"""

		self.indent -= 1

		if close and self.indent != 0:
			if self.unflushed: self.indent = 0
			self.output('| ' * self.indent + ' *** failed to call end() - ?! ***\n')
			self.indent = 0
			self.unflushed = False
			#self.timers = self.timers[:1]

		delta = time.time() - self.timers.pop()
		duration = self.format(delta)

		if not self.unflushed:
			prefix = '| ' * self.indent + ' `' + '-' * (self.width - 2 * self.indent) + '>'
		else: prefix = "%s>" % ('-' * (self.width+1-self.length))

		if text: text = '- ' + text
		self.output( "%s done (%6s) %s\n" % (prefix, duration, text) )
		self.unflushed = False

		if close: self._close()

	def show(self, text, prefix = '*'):
		"""For printing long or intermediate results of an operation"""
		
		if self.unflushed: self.output('\n')
		self.output( "%s%s %s\n" % ('| ' * self.indent, prefix, text) )

		self.unflushed = False
	def output(self, message):
		print message,
	def flush(self):
		self.file.flush()

class FileLogger(Logger):
	def __init__(self,filename):
		Logger.__init__(self)
		self.filename = filename
		self._open()
	def _open(self):
		self.file = file(self.filename, 'a')
	def output(self,message):
		self.file.write(message)
	def _reset(self):
		self._close()
		Logger._reset(self)
		self._open()
	def _close(self):
		self.file.close()

def StringToBool(string,default=False,empty=False,none=False,true=True,false=False):
	if string == None: return none
	if default == None: default = string
	if empty == None: empty = string

	if string not in (unicode,str):
		try: string = bool(int(string))
		except: pass
		try: string = str(string)
		except: return default

	string = string.lower()
	if not string: return empty
	if string in ('1','true','yes','on','enable'): return true
	if string in ('0','false','no','off','disable'): return false

	return default

class BytesToText:
	__fixed = False
	__showUnit = True
	__base = 1024
	__units = ['Y','Z','E','P','T','G','M','K','']
	__digits = None
	def __init__(self,value,fixed=None,showUnit=None,base=None,digits=None):
		try:
			value = int(value)

			if fixed == None: fixed = self.__fixed
			if showUnit == None: showUnit = self.__showUnit
			if base == None: base = self.__base
			if digits == None: digits = self.__digits
			if base not in (1024,1000): showUnit = False
			if not showUnit and not fixed: fixed = True
			unit = copy.deepcopy(self.__units)

			if fixed or fixed == '':
				if digits == None: digits = 0
				if fixed in unit:
					while unit[-1] != fixed:
						value /= float(base)
						unit.pop()
			else:
				if digits == None: digits = 2
				value = float(value)/float(base)
				unit.pop()
				while value >= 1000:
					value /= float(base)
					unit.pop()

			self.__value = ('%%1.%df' % digits) % value

			if showUnit:
				unit = unit.pop()
				if base == 1024 and unit: base = 'i'
				else: base = ''
				self.__value += ' %s%sB' % (unit,base)
		except:
			self.__value = 'NaN'
	def __str__(self):
		return self.__value
	def __repr__(self):
		return self.__value
	
	def setFixed(cls,fixed): cls.__fixed = fixed
	setFixed = classmethod(setFixed)
	def getFixed(cls): return cls.__fixed
	getFixed = classmethod(getFixed)

	def setShowUnit(cls,on=True): cls.__showUnit = on
	setShowUnit = classmethod(setShowUnit)
	def getShowUnit(cls): return cls.__showUnit
	getShowUnit = classmethod(getShowUnit)

	def setBase(cls,base=1024):
		try: cls.__base = int(base)
		except: cls.__base = 1024
	setBase = classmethod(setBase)
	def getBase(cls): return cls.__base
	getBase = classmethod(getBase)

	def setPrecision(cls,digits):
		try: cls.__digits = max(0,min(66,int(digits)))
		except: cls.__digits = None
	setPrecision = classmethod(setPrecision)
	def getPrecision(cls): return cls.__digits
	getPrecision = classmethod(getPrecision)

def timestamp(datetime):
	return int ( time.mktime( datetime.utctimetuple() ) )

def day():
	return datetime.timedelta(days=1)

class DefaultDict(dict):
		"""Dictionary with a default value for unknown keys."""
		def __init__(self, default):
				self.default = default

		def __getitem__(self, key):
				if key in self: 
						return self.get(key)
				else:
						## Need copy in case self.default is something like []
						return self.setdefault(key, copy.deepcopy(self.default))

		def __copy__(self):
				copy = DefaultDict(self.default)
				copy.update(self)
				return copy

def generateHash(key):
	"""Simple CRC based hash algorithm to help generate unique names"""
	hash = 1315423911
	for i in key:
		hash ^= ((hash << 5) + ord(i) + (hash >2))
	return (hash & 0x7FFFFFFF)

# TODO: use format function to get correct locale?
_weekDays = [
	'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday',
]
def dayOfWeek(date):
	return _weekDays[date.weekday()]

singularMap = {
	'' 		: '', 		# .. 1 item[] ..
	's' 	: '',		# .. 1 item[] ..
	'has' 	: 'has',	# .. [has] 1 item ..
	'have'	: 'has', 	# .. [has] 1 item ..
	'is'	: 'is',		# .. 1 item [is] ..
	'are'	: 'is',		# .. 1 item [is] ..
}
pluralMap = {
	'' 		: 's', 		# .. 2 item[s] ..
	's' 	: 's',		# .. 2 item[s] ..
	'has' 	: 'have', 	# .. [have] 2 items ..
	'have'	: 'have', 	# .. [have] 2 items ..
	'is'	: 'are',	# .. 2 items [are] ..
	'are'	: 'are',	# .. 2 items [are] ..
}

def getPluralMap(items):
	m = {}
	if len(items) == 1:
		return singularMap
	else:
		return pluralMap

def getDeltaString(timedelta):
	return str(timedelta).split(',')[0]

def getCurrentUser():
	from os import geteuid
	from pwd import getpwuid
	return getpwuid( geteuid() )[0]

def getCurrentGroup():
	from os import getegid
	from grp import getgrgid
	return getgrgid( getegid() )[0]

def main():
	"""Unit tests for utils.py"""

	l = Logger()
	
	l.start("Begin Logger Self Test")
	
	l.start("Task 1 - No Result")
	l.end()
	
	l.start("Task 2 - Simple Result")
	l.end("result: 100")
	
	l.start("Task 3 - Intermediate Results")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.end("ipsum: 5")
	
	l.start("Task 4 - With Sub Tasks")
	l.start("Sub Task 1 - No Result")
	l.end()
	
	l.start("Sub Task 2 - Simple Result")
	l.end("result: 100")
	
	l.start("Sub Task 3 - Intermediate Results")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.end("ipsum: 5")
	
	l.end()

	l.start("Task 5 - With Sub Tasks & Intermediate Result")
	l.show("Lorem ipsum dolor sit amet.")
	l.start("Sub Task 1 - No Result")
	l.end()
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.start("Sub Task 2 - Simple Result")
	l.end("result: 100")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.start("Sub Task 3 - Intermediate Results")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.show("Lorem ipsum dolor sit amet.")
	l.end("ipsum: 5")
	
	l.end("result: 200")
	
	l.start("Task 6 - With Long Operation Description, Lorem")
	l.end()

	l.start("Task 7 - With Longer Operation Description, Lorem")
	l.end()
	
	for i in [1,100,1000,1024]:
		for x in [1,10,100,1000,1024,10000,1024**2,0.5*1024**3,1024**3]:
			val = int(i*x)
			l.start("BytesToText(%d)" % val)
			l.end('%10s' % str(BytesToText(val)))

	l.end()

	l.start("Reset",reset=True)
	l.start("Fails")
	l.end("failed?",close=True)
	
	l.start("Reset",reset=True)
	l.start("Fails")
	l.start("Fails")
	l.show("About to Fail..")
	l.end("failed?",close=True)
	
	testXML()

if __name__ == '__main__': main()
