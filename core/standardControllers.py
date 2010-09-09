from mod_python import psp,apache,util,Cookie,Session
from mod_python.util import FieldStorage

import sys
import os
import types
import time
import linecache
import inspect
import re
import pydoc

from cgi import escape

currentPath = os.path.dirname(__file__)+'/'

class PSPErrorHandled(psp.PSP):
	def __str__(self):
		if not isinstance(self.vars['c'],ErrorController):
			try: self.run()
			except:
				ErrorController(self.req,psp=self).getContent().run()
		else: self.run()
		return ""

class StandardController:
	""" Pure generic, reusable controller """

	_filename = None
	_pspPath = currentPath
	_content_type = 'text/html'
	_globalSession = None
	_noshadowdops = False

	def __init__(self, req, createContent=True, parent=None):
		self.req = req
		self.sequence = 0
		self.codebehind = { 'c':self }
		self.even = {}
		self.last = False

		self.parent = parent
		if parent == None or not isinstance(parent,StandardController):
			try: parent = self.req.parent
			except AttributeError: pass

		# internal only
		self._browserVersion = None
		#self._session = None

		if not req: return
		if isinstance(parent,StandardController):
			self.fields = parent.fields
			self.cookieCache = parent.cookieCache
			self.session = parent.session
		else:
			self.fields = util.FieldStorage(req,keep_blank_values=True)
			self.cookieCache = {}
			self.session = session = Session.Session(self.req,lock=False,timeout=3600*12)
			self.req.parent = self

			#from traceback import print_stack
			#f = file('/tmp/trace.txt','a')
			#f.write('self: %s\n' % repr(self))
			#f.write('pid: %d uri: %s\n\n' % (os.getpid(),self.req.unparsed_uri))
			#print_stack(file=f)
			#f.write('\n\n')
			#f.close()
			#del f

		if createContent: self.createContent()
	
	def __str__(self):
		return getContent()

	def getField(self,key,default=None,asStr=True):
		if self.fields.has_key(key):
			value = self.fields[key]
			if type(value) == list: value = value[1]
			if asStr: return str(value)
			else: return value
		else: return default

	def getCookie(self,key,default=None,secret=None,init=False,force=False,expires=None,path=None,cache=True):
		if cache and secret==None and self.cookieCache.has_key(key): return self.cookieCache[key]

		if not (default!=None and init and force):
			cookieType = Cookie.Cookie
			options = {}

			if secret != None:
				cookieType = Cookie.MarshalCookie
				options['secret'] = secret

			cookies = Cookie.get_cookies(self.req, cookieType, **options)
			if cookies.has_key(key):
				cookie = cookies[key]
	
				if type(cookie) is cookieType:
					return cookie.value

		if default!=None and init:
			self.setCookie(key,default,secret=secret,expires=expires,path=path)

		return default

	def setCookie(self,key,value,secret=None,expires=None,path=None):
		cookieType = Cookie.Cookie
		options = {}

		if expires != None: options['expires'] = expires
		if path != None: options['path'] = path
		if secret != None:
			cookieType = Cookie.MarshalCookie
			options['secret'] = secret

		Cookie.add_cookie(self.req, cookieType(key, value, **options))
		if expires==0 and not secret:
			self.cookieCache[key] = None
		elif not secret:
			self.cookieCache[key] = value

	def deleteCookie(self,key,path=None):
		value = self.getCookie(key)
		if value!=None:
			self.setCookie(key,value,expires=0,path=path)

	def getAllFields(self):
		m = {}
		for key in self.fields.keys():
			m[key] = str(self.fields[key])
		return m

	def handleRequest(self):
		content = self.getContent()
		if type(content) in (str,unicode):
			self.req.content_type = self._content_type
			self.req.write(content)
		else:
			try: self.req.content_type = content._content_type
			except: self.req.content_type = self._content_type

			try:
				self.req.write('%s' % content)
			except:
				if not isinstance(self,ErrorController):
					ErrorController(self.req).getContent().run()
				else:
					raise

		return apache.OK

	def preCreate(self): pass
	def createContent(self): pass
	def postCreate(self): pass

	def getContent(self,filename=None,pspPath=None):
		if not filename: filename = self._filename
		if not pspPath: pspPath = self._pspPath
		if not filename:
			return 'Error while attempting to parse psp - No filename set!'
		try:
			if not os.path.isabs(filename):
				filename = pspPath+filename
			return PSPErrorHandled(self.req, filename=filename, vars = self.codebehind )
		except ValueError, e:
			return escape(str(e))
		except apache.SERVER_RETURN, code:
			if code[0] == apache.HTTP_NOT_FOUND:
				return 'Error while parsing psp: %s - file not found!' % self.escape(filename)
			return 'Error while parsing psp: code %s' % code[0]
		except:
			if not isinstance(self,ErrorController):
				return ErrorController(self.req).getContent()
			raise

	def evenOdd(self, reset=False,once=None,seed='default'):
		if reset:
			self.even[seed] = False
		if once:
			if once % 2: return 'even'
			else: return 'odd'
		self.last = self.even[seed] = not self.even.get(seed,self.last)
		if self.even[seed]: return 'even'
		else: return 'odd'
	def parseDate(self, datetimeObject):
		'''
		Takes in a datetime object and returns a date in nice string format.
		
		If input is not a date, the object is returned
		'''
		try:
			datetimeObject = int(datetimeObject)
			datetimeObject = datetime.datetime.fromtimestamp( datetimeObject )
		except:
			pass
		try: return datetimeObject.strftime('%Y-%m-%d')
		except: return datetimeObject
	def newId(self,reset=False):
		if reset: self.sequence = 0
		else: self.sequence += 1
		return self.sequence

	def getId(self):
		return self.sequence
	def __str__(self):
		return str( self.getContent() )

	def shadowdrop(self,content='',begin=None,end=None):
		if not (content or begin or end) or self._noshadowdops: return content
		shadowdrop = ShadowDropController(self.req)
		shadowdrop.content = content
		shadowdrop.begin = content or begin
		shadowdrop.end = content or end
		return shadowdrop.getContent()

	def getClass(self):
		if not self._filename: return ''
		return os.path.basename(self._filename).replace('.','-')
	
	def escape(self,string):
		if type(string)!=type(''):
			return string
		return escape(string)

	#_sessions = []
	#def _regSession(self,sid=None):
		#if sid:
			#self._sessions.append(sid)
		#if self._globalSession and self._sessions:
			#self._globalSession['sessions'] = self._globalSession.get('sessions',[])+self._sessions
			#self._sessions = []

	def getSession(self,globalSession=False):
		#if self.parent:
			#return self.parent.getSession(globalSession=globalSession)

		#session = None
		#if globalSession:
			#assert 0, 'broken, do not use'
			##if not self._globalSession:
				##localSession = self.getSession()
				##session = self._globalSession = Session.Session(self.req,lock=False,sid=localSession.id(),timeout=3600*120)
				### dirty hack
				##session._sid = '5a24b2f10b3e543fcf785819c2af7a29'
				##for key in localSession.keys():
					##if session.has_key(key): session.pop(key)
				##session['create_pid'] = os.getpid()

			##session = self._globalSession
			##self._regSession()
		#else:
			#if self._session == None:
				#self._session = Session.Session(self.req,lock=False,timeout=3600*12)
				#from traceback import print_stack
				#f = file('/tmp/trace.txt','a')
				#f.write('self: %s\n' % repr(self))
				#f.write('pid: %d uri: %s\n\n' % (os.getpid(),self.req.unparsed_uri))
				#print_stack(file=f)
				#f.write('\n\n')
				#f.close()
				#del f
			#session = self._session
			## ugly security
			##assert(session.id() != '5a24b2f10b3e543fcf785819c2af7a29')
			##if session.is_new():
				##session['create_pid'] = os.getpid()
				##self._regSession(session.id())
		##sid = self.getCookie('pysid')
		##session = Session.Session(self.req,lock=False,timeout=3600*12,sid=sid)
		
		##session = Session.Session(self.req)

		#session.load()
		#session.unlock()

		#session['last_pid'] = os.getpid()
		#session.save()

		return self.session

	#def getAllSessions(self):
		#localSession = self.getSession()
		#globalSession = self.getSession(globalSession=True)
		#sessions = self.getSessionValue('sessions',default=[],globalSession=True)

		#activeSessions = [localSession.id()]
		#m = { localSession.id():'x' }

		#l = [globalSession,localSession]
		#for sid in sessions:
			#if not m.has_key(sid):
				#m[sid] = 'x'
				#session = Session.Session(self.req,lock=False,sid=localSession.id())
				#for key in session.keys(): session.pop(key)
				### dirty hack
				#session._sid = sid
				#if session.load():
					#l.append(session)
					#activeSessions.append(sid)
		#self.setSessionValue('sessions',activeSessions,globalSession=True)
		#return l

	def getSessionValue(self,key,default=None,init=False,globalSession=False):
		try:
			value = self.getSession(globalSession=globalSession)[key]
		except:
			value = default
			if init:
				self.setSessionValue(key,value,globalSession=globalSession)
		return value

	def setSessionValue(self,key,value,globalSession=False):
		session = self.getSession(globalSession=globalSession)
		session[key] = value
		session.save()
		return value

	def deleteSessionValue(self,key,globalSession=False):
		session = self.getSession(globalSession=globalSession)
		session.pop(key,None)
		session.save()

	_reGecko = re.compile('\\bGecko/')
	_reGeckoVersion = re.compile('rv:([0-9]*\.[0-9])')
	_reKTML = re.compile('\\KHTML/([0-9]*\.[0-9])')
	_reOpera = re.compile('\\Opera/([0-9]*\.[0-9])')
	_reMSIE = re.compile('\\MSIE ([0-9]*\.[0-9])')
	def getBrowserVersion(self):
		if self._browserVersion:
			return self._browserVersion
		userAgent = self.req.headers_in.get('user-agent')
		engine = userAgent
		version = None
		if userAgent:
			if self._reGecko.search(userAgent):
				engine = 'Gecko'
				result = self._reGeckoVersion.search(userAgent)
				version = 0.0
				if result:
					version = float(result.groups()[0])
			elif self._reKTML.search(userAgent):
				engine = 'KHTML'
				result = self._reKTML.search(userAgent)
				version = 0.0
				if result:
					version = float(result.groups()[0])
			elif self._reOpera.search(userAgent):
				engine = 'Opera'
				result = self._reOpera.search(userAgent)
				version = 0.0
				if result:
					version = float(result.groups()[0])
			elif self._reMSIE.search(userAgent):
				engine = 'MSIE'
				result = self._reMSIE.search(userAgent)
				version = 0.0
				if result:
					version = float(result.groups()[0])

		self._browserVersion = (engine,version)
		return self._browserVersion

class ShadowDropController(StandardController):
	_filename = 'psp/shadowdrop.psp'

class BlankController(StandardController):
	_filename = 'psp/blank.psp'

class Frame:
	def __init__(self,lnum,file,func,params,code,dump):
		self.lnum = lnum
		self.file = file
		self.func = func
		self.params = params
		self.code = code
		self.dump = dump

class CodeLine:
	def __init__(self,lnum,code,mark):
		self.lnum = lnum
		self.code = code
		self.mark = mark

class ErrorController(StandardController):
	_filename = 'psp/error.psp'
	_context = 5
	''' how many context lines of code to display for every frame '''
	
	
	# TODO fix this RE, too complex and not reliable
	#_varFind = '''(^|<[^>]*>[^'"<\w]*|'[^']*'[^'"<\w]*|[^'"<\w]*|"[^"]*"[^'"<\w]*)%s([^\w]|$)'''
	# Slightly better, but lacks " cases and start \w
	_varFind = '''(<[^>]*>[^'<]*|'[^'<]*'|[^'<])%s([^\w]*)'''
	
	def __init__(self, req, createContent=True, parent=None, psp=None):
		StandardController.__init__(self, req=req, createContent=createContent, parent=parent)
		self.psp = psp

	def createContent(self):
		(etype, evalue, etb) = sys.exc_info()

		if type(etype) is types.ClassType:
			etype = etype.__name__

		self.etype = escape(str(etype))
		self.evalue = escape(str(evalue))

		self.exception = []
		if type(evalue) is types.InstanceType:
			for name in dir(evalue):
				if name[:1] == '_': continue
				value = pydoc.html.repr(getattr(evalue, name))
				self.exception.append('%s = %s' % (name, value))

		self.frames = []

		records = inspect.getinnerframes(etb, self._context)
		for frame, file, lnum, func, lines, index in records:
			if file:
				file = os.path.abspath(file)


			args, varargs, varkw, locals = inspect.getargvalues(frame)
			params = ''
			if func != '?':
					
				#params = inspect.formatargvalues(args, varargs, varkw, locals)
				
				paramList = []
				
				#longname = '%s = ??' % escape(name)
				try:
					for arg in args:
						longname = '%s = %s' % (pydoc.html.repr(locals[arg]), escape(arg))
						acronym = '<acronym title="%s">%s</acronym>' % ( longname, arg)
						paramList.append(acronym)
					if varargs:
						longname = '%s *%s' % (pydoc.html.repr(locals[varargs]), escape(varargs))
						acronym = '<acronym title="%s">*%s</acronym>' % ( longname, varargs)
						paramList.append(acronym)
					if varkw:
						longname = '%s **%s' % (pydoc.html.repr(locals[varkw]), escape(varkw))
						acronym = '<acronym title="%s">**%s</acronym>' % ( longname, varkw)
						paramList.append(acronym)
					params = '(' + ', '.join(paramList) + ')'
				except:
					pass
			
			highlight = {}
			def reader(lnum=[lnum]):
				highlight[lnum[0]] = 1
				try: return linecache.getline(file, lnum[0])
				finally: lnum[0] += 1
			vars = self.scanvars(reader, frame, locals)

			codeLines = []
			if index is not None:
				i = lnum - index
				for line in lines:
					mark = ''
					if i in highlight: mark='highlight'

					code = CodeLine(
						lnum=i,
						code=escape(line.rstrip('\n\r')),
						mark=mark,
					)
					codeLines.append(code)
					i += 1

			dumpMap = {}
			for name, where, value in vars:
				longname = '%s = ??' % escape(name)
				try:
					if not where or name.find(where) == 0:
						longname = '%s = %s' % (escape(name), pydoc.html.repr(value))
					else: longname = '%s:%s = %s' % (escape(where), escape(name), pydoc.html.repr(value))
				except: pass
				
				if not dumpMap.has_key(name): dumpMap[name] = []
				dumpMap[name].append(longname)

			keys = dumpMap.keys()
			keys.sort(lambda a, b: len(b)-len(a))
			dump = []
			for key in keys:
				used = False
				#for codeLine in codeLines:
					#textFind = re.compile( self._varFind % key)
					#if textFind.search( codeLine.code ):
						##acronym = '<acronym title="%s">%s</acronym>' % ( ', '.join(dumpMap[key]), key)
						##textRep = r'\1%s\2' % acronym
						##codeLine.code = textFind.sub( textRep, codeLine.code )
						#used = True
				if not used or 1:
					for d in dumpMap[key]:
						dump.append(d)

			obj = Frame(
				lnum=lnum,
				file=escape(file),
				func=escape(str(func)),
				params=params,
				code=codeLines,
				dump=dump,
			)
			self.frames.append(obj)

	def lookup(self,name, frame, locals):
		"""Find the value for a given name in the given environment."""
		if name in locals:
			return 'local', locals[name]
		if name in frame.f_globals:
			return 'global', frame.f_globals[name]
		if '__builtins__' in frame.f_globals:
			builtins = frame.f_globals['__builtins__']
			if type(builtins) is type({}):
				if name in builtins:
					return 'builtin', builtins[name]
			else:
				if hasattr(builtins, name):
					return 'builtin', getattr(builtins, name)
		return None, []

	def scanvars(self,reader, frame, locals):
		"""Scan one logical line of Python and look up values of variables used."""
		import tokenize, keyword
		vars, lasttoken, parent, prefix, value = [], None, None, '', []
		for ttype, token, start, end, line in tokenize.generate_tokens(reader):
			if ttype == tokenize.NEWLINE: break
			if ttype == tokenize.NAME and token not in keyword.kwlist:
				if lasttoken == '.':
					if parent is not []:
						value = getattr(parent, token, [])
						vars.append((prefix + token, prefix, value))
				else:
					where, value = self.lookup(token, frame, locals)
					vars.append((token, where, value))
			elif token == '.':
				prefix += lasttoken + '.'
				parent = value
			else:
				parent, prefix = None, ''
			lasttoken = token
		return vars
