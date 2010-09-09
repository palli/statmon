
from utils import DefaultDict

class SmartList(list):
	def __init__(self,settings):
		for setting in settings:
			self.append(setting)
	def __getattr__(self,key):
		l = []
		for item in self:
			l.append( eval('i.%s' % key,{'i':item},{}))
		if len(l)==1: return l[0]
		return SmartList(l)
	
	def __call__(self,*arg,**keywords):
		l = []
		for item in self:
			l.append( item(**keywords) )
		if len(l)==1: return l[0]
		return SmartList(l)

class Config:
	_sortKey = 0
	_debug = False
	class __Default:
		def __init__(self,value=None,description=None):
			self.value = value
			self.description = description

	def __init__(self,key=None,value=None,description=None,unregistered=False,parent=None):
		filename = None
		if key and key.split('.')[-1] == 'xml':
			filename = key
			key = None

		self._key = key
		self._default = Config.__Default()
		self._value = value
		self._description = description
		self._noneValueOk = None
		self._obscure = None # for hidding sensitive information, e.g. logins

		self._unregistered = unregistered # was created by XML load

		self._sortKey = Config._sortKey # for XML constancy -- e.g. to be able to
		Config._sortKey += 1 # keep same creation order when using dict

		self._subSettings = {}
		self._parent = parent

		if filename: self.loadXML(filename)

	def setValue(self,value=None,noneValueOk=None):
		if noneValueOk != None:
			self._noneValueOk = noneValueOk
		self._value = value

	def getValue(self,defaultOverride=None,noneValueOk=None):
		if noneValueOk == None:
			noneValueOk = self._noneValueOk
		if noneValueOk or self._value != None: return self._value
		if defaultOverride != None: return defaultOverride
		return self._default.value

	def setDescription(self,description)	: self._description = description
	def setDefaultDescription(self,description)	: self._default.description = description
	def setDefaultValue(self,default)		: self._default.value = default
	def setNoneValueOk(self,noneValueOk)	: self._noneValueOk = noneValueOk
	def setObscure(self,obscure)			: self._obscure = obscure
	
	def getDescription(self):
		if not self._description: return self._default.description
		return self._description
	def getDefaultValue(self)				: return self._default.value
	def getNoneValueOk(self)				: return self._noneValueOk
	def getObscure(self)					: return self._obscure

	def __getattr__(self,key):
		if Config._debug and not key[0:2] != '__': print key
		assert(key[0:2] != '__')
		return SmartList(self._get('.'+key,index=None))

	def __setattr__(self,key,value):
		if key[0:1] == '_':
			self.__dict__[key] = value
			return

		assert(not isinstance(value,Config)) # TODO: implement
		self._get('.'+key).setValue(value)

	#def __getitem__(self,index):
		#if self._debug: print '__getitem__(self=%s,index=%s)' % (repr(self._key),repr(index))
		#return self._parent.__get(path='.'+self._key,index=index)

	def __eq__(self,value):
		return self.getValue() == value
	def __gt__(self,other):
		return self.getValue() > other
	def __lt__(self,other):
		return self.getValue() < other

	def __str__(self):
		return str(self.getValue())

	def __call__(self): return repr(self)
	def __repr__(self):
		if self._subSettings:
			return repr(self._subSettings.keys())
		return repr(self.getValue())

	def getAll(self,obscure=None):
		all = {}

		all['subSettings'] = {}
		for key,settings in self._subSettings.items():
			all['subSettings'][key] = []
			for setting in settings:
				all['subSettings'][key].append( setting.getAll(obscure=obscure) )

		if obscure == None:
			obscure = self._obscure
		setting = DefaultDict(None)

		if self._key != None:
			all['key'] = self._key
		if self._value != None:
			all['value'] = self._value
			if obscure:
				all['value'] = (len(self._value)+1)*'*'
		if self._default != None:
			all['default'] = self._default
		if self._description != None:
			all['description'] = self._description
		if self._noneValueOk != None:
			all['noneValueOk'] = self._noneValueOk
		if self._obscure != None:
			all['obscure'] = self._obscure
		if self._sortKey != None:
			all['sortKey'] = self._sortKey

		if self._unregistered != None:
			all['unregistered'] = self._unregistered

		return all

	def registerSetting(self,path,default=None,description=None):
		setting = self._get(path,create=True)
		if default:
			setting._default.value = default
		if description:
			setting._default.description = description

	def _defaultLink(self,zero):
		self._default = zero._default
		self._unregistered = zero._unregistered
		settings = map(lambda x: x[0], zero._subSettings.values())
		settings.sort(lambda x,y: x._sortKey-y._sortKey)
		for zeroSetting in settings:
			if not zeroSetting._unregistered:
				setting = self._get(path='.'+zeroSetting._key,create=True)
				setting._defaultLink(zeroSetting)

	def _get(self,path=None,create=False,unregistered=False,index=0):
		if self._debug: print '__call__(self=%s,path=%s,create=%s,unregistered=%s,index=%s)' % (repr(self._key),repr(path),repr(create),repr(unregistered),index)
		if path==None:
			return self.getValue()

		assert(path and type(path) == str)
		splitPath = path.split('.')
		key = splitPath[0]
		path = splitPath[1:]

		if path:
			key = path[0]
			newPath = '.'.join(path)
			assert(create or self._subSettings.has_key(key))
			if create:
				setting = Config(key=key,unregistered=unregistered,parent=self)
				if not self._subSettings.has_key(key):
					assert(index==0)
					self._subSettings[key] = [setting]
				elif len(self._subSettings[key]) > index:
					self._subSettings[key][index]._sortKey = setting._sortKey
				else:
					assert(index==len(self._subSettings[key]))
					self._subSettings[key].append(setting)

				zero = self._subSettings[key][0]
				if not zero._unregistered and self._subSettings[key][index]._unregistered and index:
					self._subSettings[key][index]._defaultLink(zero)

			if index==None:
				return self._subSettings[key]
			return self._subSettings[key][index]._get(newPath,create=create,unregistered=unregistered)
		else:
			assert(create or self._key == key)
			if create and not self._key:
				self._key = key
			return self

	def saveXML(self,filename=None,comments=False,indent='\t'):
		import xml.dom.minidom
		doc = xml.dom.minidom.Document()

		self.saveXML_v1(doc,comments=comments)

		import xml.dom.ext,sys
		file = sys.stdout
		if filename: file = open(filename,'w')

		for child in doc.childNodes:
			if child.nodeType == child.ELEMENT_NODE:
				child.setAttribute('version','1.2')
				break

		xml.dom.ext.PrettyPrint(doc,stream=file,indent=indent)

	def saveXML_v1(self,doc=None,parent=None,comments=True):
		element = doc.createElement(self._key)
		
		root = parent
		if not parent: root = doc
		
		if comments and self._description:
			root.appendChild( doc.createComment(self.getDescription()) )

		root.appendChild( element )

		if self.getValue() or self._noneValueOk:
			value = self.getValue()
			element.appendChild(doc.createTextNode(str(value)))

		if self._subSettings:
			subSettings = reduce(lambda x,y: x+y, self._subSettings.values())
			subSettings.sort(lambda x,y: x._sortKey-y._sortKey)
	
			for setting in subSettings:
				setting.saveXML_v1(doc=doc,parent=element,comments=comments)


	def loadXML(self,filename):
		import xml.dom.minidom
		doc = xml.dom.minidom.parse(filename)
		element = None
		comment = None
		for child in doc.childNodes:
			if child.nodeType == child.ELEMENT_NODE:
				element = child
			elif child.nodeType == child.COMMENT_NODE:
				comment = child.data
		if not element: return
		self._key = element.tagName

		version = element.getAttribute('version')

		if version == '1.0' or version == '1.2':
			self.loadXML_v1(doc,element,comment=comment)
		elif version == '':
			self.loadXML_v0(doc,element)
		else:
			assert(0) # unknown version
		
		return self

	def loadXML_v1(self,doc,element,parent=None,comment=None,number=None):
		path = str(element.tagName)
		if parent: path = str(parent.tagName) + '.' + path

		index = 0
		if number != None: index = number[path]
		setting = self._get(path,create=True,unregistered=True,index=index)
		if number != None: number[path] += 1

		if comment:
			setting.setDescription(comment)
			comment = None

		number = DefaultDict(0)
		data = []
		for child in element.childNodes:
			if child.nodeType == child.TEXT_NODE:
				data.append(child.data)
			elif child.nodeType == child.COMMENT_NODE:
				comment = child.data
			elif child.nodeType == child.ELEMENT_NODE:
				setting.loadXML_v1(doc,child,element,comment,number)
				comment = None

		if data:
			try:
				setting.setValue(eval('\n'.join(data),{},{}))
			except:
				value = '\n'.join(data).strip()
				if value: setting.setValue(value)

	def loadXML_v0(self,doc,element):
		for child in element.childNodes:
			if child.nodeType == child.ELEMENT_NODE:
				if child.firstChild and child.firstChild.nodeType == child.TEXT_NODE:
					setFunc = None
					if child.tagName == 'description':
						setFunc = self.setDefaultDescription
					elif child.tagName == 'default':
						setFunc = self.setDefaultValue
					elif child.tagName == 'value':
						setFunc = self.setValue
					elif child.tagName == 'noneValueOk':
						setFunc = self.setNoneValueOk
					elif child.tagName == 'obscure':
						setFunc = self.setObscure
					if setFunc:
						dataType = 'str'
						if child.hasAttribute('type'):
							dataType = child.getAttribute('type')
						data = child.firstChild.data
						value = eval('%s(%s)' % (dataType,data),{},{})
						setFunc(value)
				if child.tagName == 'subSettings':
					number = DefaultDict(0)
					for settingElement in child.childNodes:
						if settingElement.nodeType == settingElement.ELEMENT_NODE and settingElement.tagName != 'subSettings':
							path = str(element.tagName) + '.' + str(settingElement.tagName)
							setting = self._get(path,create=True,unregistered=True,index=number[path])
							number[path] += 1
							setting.loadXML_v0(doc=doc,element=settingElement)

def testReg(l,config,path=None,default=None,description=None):
	l.start('''config.registerSetting(*p)''')
	p = {}

	if path != None:
		l.show('''p['path'] = %s''' % path)
		p['path'] = path
	if default != None:
		l.show('''p['default'] = %s''' % default)
		p['default'] = default
	if description != None:
		l.show('''p['description'] = %s''' % description)
		p['description'] = description

	config.registerSetting(**p)
	l.end()

def testGetValue(l,config,path=None,create=None,unregistered=None,defaultOverride=None,noneValueOk=None,wanted=None):
	l.start('''config(**p1).getValue(**p2)''')
	p1 = {}
	if path != None:
		l.show('''p1['path'] = %s''' % path)
		p1['path'] = path
	if create != None:
		l.show('''p1['create'] = %s''' % create)
		p1['create'] = create
	if unregistered != None:
		l.show('''p1['unregistered'] = %s''' % unregistered)
		p1['unregistered'] = unregistered

	p2 = {}
	if defaultOverride != None:
		l.show('''p2['defaultOverride'] = %s''' % defaultOverride)
		p2['defaultOverride'] = defaultOverride
	if noneValueOk != None:
		l.show('''p2['noneValueOk'] = %s''' % noneValueOk)
		p2['noneValueOk'] = noneValueOk
	value = config._get(**p1).getValue(**p2)

	assert(value == wanted)
	l.end('value = %s' % repr(value))

	return value

def testSetValue(l,config,path=None,create=None,unregistered=None,value=None,noneValueOk=None):
	l.start('''config(**p1).setValue(**p2)''')

	p1 = {}
	if path != None:
		l.show('''p1['path'] = %s''' % path)
		p1['path'] = path
	if create != None:
		l.show('''p1['create'] = %s''' % create)
		p1['create'] = create
	if unregistered != None:
		l.show('''p1['unregistered'] = %s''' % unregistered)
		p1['unregistered'] = unregistered

	p2 = {}
	if value != None:
		l.show('''p2['value'] = %s''' % value)
		p2['value'] = value
	if noneValueOk != None:
		l.show('''p2['noneValueOk'] = %s''' % noneValueOk)
		p2['noneValueOk'] = noneValueOk
	value = config._get(**p1).setValue(**p2)

	l.end()

def main():
	"""Unit tests for config.py"""
	from utils import Logger
	l = Logger()
	l.start('Starting Unit Tests for Config')

	l.start('config = Config()')
	global config
	config = Config()
	l.end()
	
	testReg(l,config,'root',description='Root Item')
	testGetValue(l,config,'root')
	testSetValue(l,config,'root',value='foo')
	testGetValue(l,config,'root',wanted='foo')

	testReg(l,config,'.root.sub1',description='Sub-Root Item 1')
	testGetValue(l,config,'.root.sub1')
	testSetValue(l,config,'.root.sub1',value='foo')
	testGetValue(l,config,'.root.sub1',wanted='foo')

	rootConfig = config.root
	testReg(l,rootConfig,'.sub2',description='Sub-Root Item 2')
	testGetValue(l,rootConfig,'.sub2')
	testSetValue(l,rootConfig,'.sub2',value='foo')
	testGetValue(l,rootConfig,'.sub2',wanted='foo')

	subConfig2 = rootConfig.sub2
	testReg(l,subConfig2,'.sub2sub',description='Sub-Sub-Root Item 1')
	testGetValue(l,subConfig2,'.sub2sub')
	testSetValue(l,subConfig2,'.sub2sub',value='foo')
	testGetValue(l,subConfig2,'.sub2sub',wanted='foo')

	typesConfig = rootConfig._get('.types',create=True)
	testReg(l,typesConfig,'.typeNoneType',description = 'Test Setting - None Type')
	testReg(l,typesConfig,'.typeStr',description = 'Test Setting - Str Type',default='Blabla')
	testReg(l,typesConfig,'.typeInt',description = 'Test Setting - Int Type',default=123)
	testReg(l,typesConfig,'.typeFloat',description = 'Test Setting - Float Type',default=1.23)
	testReg(l,typesConfig,'.typeBool',description = 'Test Setting - Bool Type',default=True)
	testReg(l,typesConfig,'.typeList',description = 'Test Setting - List Type',default=[1,'a',None])
	testReg(l,typesConfig,'.typeDict',description = 'Test Setting - Dict Type',default={'a':1,'b':'a','c':None})
	testReg(l,rootConfig,'.types',description = 'Test Types')

	global before
	before = config.getAll()

	l.start("""config.saveXML('config.xml')""")
	config.saveXML('config.xml')
	l.end()

	l.start('newConfig = Config()')
	newConfig = Config()
	l.end()

	l.start("""newConfig.loadXML('config.xml')""")
	newConfig.loadXML('config.xml')
	l.end()

	global after
	after = newConfig.getAll()

	newTypesConfig = newConfig.root.types
	testGetValue(l,newTypesConfig,'.typeNoneType')
	testGetValue(l,newTypesConfig,'.typeStr',wanted='Blabla')
	testGetValue(l,newTypesConfig,'.typeInt',wanted=123)
	testGetValue(l,newTypesConfig,'.typeFloat',wanted=1.23)
	testGetValue(l,newTypesConfig,'.typeBool',wanted=True)
	testGetValue(l,newTypesConfig,'.typeList',wanted=[1,'a',None])
	testGetValue(l,newTypesConfig,'.typeDict',wanted={'a':1,'b':'a','c':None})

	l.start("""newConfig.saveXML('newConfig.xml')""")
	newConfig.saveXML('newConfig.xml')
	l.end()

	l.start("""system('diff config.xml newConfig.xml')""")
	import os
	code = os.system('diff config.xml newConfig.xml')
	assert(code == 0)
	l.end('code = %d' % code)

	l.start("""system('rm -f config.xml newConfig.xml')""")
	import os
	code = os.system('rm -f config.xml newConfig.xml')
	assert(code == 0)
	l.end('code = %d' % code)

	l.end()

if __name__ == '__main__': main()
else:
	config = Config()
	config.registerSetting('config')
