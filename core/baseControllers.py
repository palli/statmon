#!/usr/bin/python

from environment import logger,getTempPath
from utils import DefaultDict,BytesToText,StringToBool
import os, datetime

from mod_python import apache

from standardControllers import StandardController,BlankController,ErrorController,currentPath
from inputControllers import InputController

from tableControllers import TableController,TH,CVSTableController

rootPath=currentPath

def setRootPath(path):
	global rootPath
	rootPath=os.path.abspath(path)+'/'

_themes = []
try:
	files = os.listdir(currentPath+'/css')
	for file in files:
		if file.startswith('color-theme'):
			_themes.append((file.replace('color-theme-','').replace('.css',''),'css/'+file))
except:
	_themes.append(('default','css/color-theme-default.css'))

class DialogController(StandardController):
	_filename = 'psp/dialog.psp'
	_title = ''
	_text = ''
	def createContent(self):
		dialogTable = TableController(self.req,'dialog',self._title,showHeaders=False)
		dialogTable.addHeader(TH('text', 'text',TH.HTML,sorted=False,sortable=False))
		dialogTable.addRow(text=self._text)
		self.dialogTable = dialogTable.getContent()

class ForbiddenController(DialogController):
	_title = 'Access Forbidden'
	_text = '''<span style="font-weight: bold;">You do not have access to this page!</span><br/>
	<br/>
	If you believe you should have access to this page please contact the site administrator with full details of the task you are trying to carry out.<br/>
	<br/><a href="#" onClick="history.back();return false">Go Back</a>'''

class NotFoundController(DialogController):
	_title = 'Page not Found'
	_text = '''<span style="font-weight: bold;">The requested page was not found!</span><br/>
	<br/>
	If you believe this is an error please contact the site administrator with full details of the task you are trying to carry out.<br/>
	<br/><a href="#" onClick="history.back();return false">Go Back</a>'''

class BaseController(InputController):
	"""Controller with generic nav/content template"""

	_title = 'Base Controller'
	_navTitle = None
	_filename = 'psp/base.psp'
	_highlightController = None
	_status = None

	def __init__(self, req,createContent=True,parent=None):
		self._alerts = []
		self._splitAlerts = 1
		self._extraSheets = []
		self._exportTable = None

		# used in psp
		self.injectedContent = ''
		self.content = None
		self.overrideContent = None
		self.inputHidden = True
		self.inputBox = None

		InputController.__init__(self,req,parent=parent)

		if isinstance(parent,BaseController):
			# safe time and increase consistency
			self.now = self.parent.now
			self.weekago = self.parent.weekago
			self.yesterday = self.parent.yesterday
			self.today = self.parent.today
			self.testAlerts = self.parent.testAlerts
			self.debugAlerts = self.parent.debugAlerts
		else:
			self.now = datetime.datetime.now()
			self.today = datetime.datetime( *self.now.timetuple()[0:3] )
			self.weekago = self.today-datetime.timedelta(days=7)
			self.yesterday = self.today-datetime.timedelta(days=1)
			self.today = self.today
			self.testAlerts = StringToBool(self.getField('testAlerts'))
			self.debugAlerts = StringToBool(self.getField('debugAlerts'))
			BytesToText.setFixed(StringToBool(self.getField('fixedUnit'),default=None,empty=None,none=None))
			BytesToText.setShowUnit(StringToBool(self.getField('showUnit',True),default=True,none=None))
			BytesToText.setBase(self.getField('baseUnit'))
			BytesToText.setPrecision(self.getField('precisionUnit'))
			try: self.testAlerts = int(self.testAlerts)
			except: pass
			homePrefix = self.getHomePrefix()
			baselayout = self.getBaseLayout()
			self.addStyleSheet(homePrefix+'css/outer-baselayout.css','outer','baselayout','screen',active=baselayout=='outer')
			self.addStyleSheet(homePrefix+'css/inner-baselayout.css','inner','baselayout','screen',active=baselayout=='inner')
			self.addStyleSheet(homePrefix+'css/print-baselayout.css','print','baselayout','print')

			self.addStyleSheet(homePrefix+'css/core.css','std','core')

			theme = self.getColorTheme()
			for name,file in _themes:
				self.addStyleSheet(homePrefix+file,name,'color-theme',active=theme==name)

			shadows = self.getShadows()
			if shadows:
				self.addStyleSheet(homePrefix+'css/half-shadows.css','half','shadows',active=shadows=='half')
				self.addStyleSheet(homePrefix+'css/full-shadows.css','full','shadows',active=shadows=='full')
				StandardController._noshadowdops = False
			else:
				StandardController._noshadowdops = True

		if not createContent: return

		self.preCreate()
		self.createContent()
		self.postCreate()

	def createContent(self):
		# prevent recursion, if createContent has not been overriden
		if isinstance(self.parent,BaseController): return

		self._pspPath = currentPath

		self.header = HeaderController(self.req,parent=self)
		self.footer = FooterController(self.req,parent=self)

		self.nav = NavController(self.req,parent=self)
		Content = self.overrideContent
		if not Content:
			Content = self.nav.getActiveController()

		try: self.content = Content(self.req,parent=self)
		except:
			self.content = ErrorController(self.req,parent=self)
		
		if self.findExportTable(self.getField('exportTable'),self.content):
			return

		self.nav.updateItem(self.content)

		if isinstance(self.content,InputController) and self.content.hasInputs():
			self.inputHidden = StringToBool(self.getField('filterhide',self.inputHidden))
			self.inputBox = InputController.getContent(self.content,filename=InputController._filename,pspPath=InputController._pspPath)
			self.inputHidden = min(self.inputHidden,self.content.inputHidden,not self.content.hasBadInput)
		if isinstance(self.content,BaseController):
			if self.content._filename == self._filename and self.content._pspPath == self._pspPath:
				# prevent unreadable errors if filename not overriden
				self.content._filename = None

			self._extraSheets += self.content._extraSheets

		#self.testpop = PopUpMenuController(self.req,'eisbock.basis.is',pop=PU.DOWN_RIGHT,items=['eisbock.basis.is','maibock.basis.is','doppelbock.basis.is'])

		self.header.title = self.getTitle()
		self.header.inputBox = self.inputBox
		self.header.inputHidden = self.inputHidden

	def getContent(self,filename=None,pspPath=None):
		if self._exportTable:
			self._exportTable.__class__ = CVSTableController
			return self._exportTable
		return InputController.getContent(self,filename,pspPath)

	def findExportTable(self,exportTable,object):
		if type(object) == list: items = object
		elif type(object) == dict: items = object.values()
		else: items = vars(object).values()

		for item in items:
			if isinstance(item,TableController):
				item.setExportable(True)
				if exportTable and item.getName() == exportTable:
					self._exportTable = item
					return True
			elif type(item) in (list,dict) and self.findExportTable(exportTable,item):
				return True
		return False

	def getControllerByURI(self,notFound=NotFoundController,forbidden=ForbiddenController,overrideFound=None):
		filename=os.path.abspath(self.req.filename+self.req.path_info)
		if _uri2Controller[filename]:
			items = _uri2Controller[filename]
			for item in items:
				if item.accessLevel and not self.getAccessLevel() & item.accessLevel:
					continue
				if item.controller:
					if overrideFound != None: return overrideFound
					return item.controller
			return forbidden
		return NotFoundController

	def getSuffix(self,cwd=None):
		if not cwd: cwd = currentPath
		prefix = os.path.commonprefix((cwd,rootPath))
		rootSuffix = rootPath.replace(prefix,'')
		#cwdSuffix = cwd.replace(prefix,'')
		suffix = rootSuffix+(self.req.filename+self.req.path_info).replace(rootPath,'')
		return ('../'*suffix.count('/'))+suffix

	def getHomePrefix(self,cwd=None):
		if not cwd: cwd = currentPath
		prefix = os.path.commonprefix((cwd,rootPath))
		rootSuffix = rootPath.replace(prefix,'')
		cwdSuffix = cwd.replace(prefix,'')
		suffix = rootSuffix+(self.req.filename+self.req.path_info).replace(rootPath,'')
		return ('../'*suffix.count('/'))+cwdSuffix

	def homePrefixIt(self,string,cwd=None):
		return os.path.normpath(self.getHomePrefix(cwd)+string)

	def getBasepath(self):
		uri=os.path.dirname(self.req.parsed_uri[apache.URI_PATH])
		path=os.path.abspath(uri+'/'+self.getHomePrefix()+'/..')
		return path

	def getControllerURI(self,controller,fail=None,homePrefix=True):
		if not _controller2URI.has_key(controller) and fail:
			return fail

		assert(_controller2URI.has_key(controller) and _controller2URI[controller].uri)
		if not homePrefix: return _controller2URI[controller].uri
		return self.getHomePrefix(_controller2URI[controller].root)+_controller2URI[controller].uri

	def getTitle(self,active=False,reverseOrder=False,navTitle=False):
		content = self.content

		if navTitle and self._navTitle:
			return self._navTitle

		if isinstance(content,BaseController) and content.getTitle() != self._title:	
			if reverseOrder: return '%s - %s' % (content.getTitle(),self._title)
			return '%s - %s' % (self._title, content.getTitle())
		return self._title

	def getRegisteredControllers(self):
		return _controller2URI.values()

	def getToggleClass(self,id,value):
		name = id+'.'+value
		hideValue = self.getField(name)
		hideValue = self.getCookie(name,hideValue,init=True,force=True)
		if hideValue and hideValue != '0':
			return value
		return ''

	def getPrintLayout(self):
		return StringToBool(self.getField('printLayout'))
	
	def getBaseLayout(self,value=None,validate=False):
		if validate:
			if value not in ('inner','outer'):
				if self.getBrowserVersion()[0] == 'MSIE':
					 #and self.getBrowserVersion()[1] < 7.0:
					return 'inner'
				return 'outer'
			return value

		return self.processSetting('baselayout-sheet',self.getBaseLayout)

	def getColorTheme(self,value=None,validate=False):
		if validate:
			names = map(lambda x:x[0],_themes)+[False]
			if value not in names: return 'default'
			return value

		return self.processSetting('color-theme-sheet',self.getColorTheme,true='default')

	def getShadows(self,value=None,validate=False):
		if validate:
			if value not in ('full','half',False):
				if self.getBrowserVersion()[0] == 'MSIE':
					if self.getBrowserVersion()[1] >= 7.0: return 'full'
					return False
				value = 'half'
			return value

		return self.processSetting('shadows-sheet',self.getShadows,true='full')

	def processSetting(self,name,validator,true=True):
		value = self.getField(name)
		if value==None and self.getCookie(name) != None:
			value = self.getCookie(name)
			self.deleteCookie(name)
		if value==None:
			value = self.getSessionValue(name)

		value = StringToBool(value,default=None,none=None,true=true)
		value = validator(value,validate=True)
		self.setSessionValue(name,value)

		return value

	def addStyleSheet(self,sheetHref,sheetId=None,sheetClass='general',sheetMedia='screen, print',active=None):
		if not sheetId: sheetId = sheetHref.split('/')[-1].split('.')[0]
		if self.getPrintLayout(): sheetMedia = sheetMedia.replace('screen','noscreen').replace('print','screen')
		if active == None: active=True
		sheetRel = 'stylesheet'
		sheetMisc = ''
		if not active:
			sheetRel = 'alternate stylesheet'
			sheetMisc = 'title="%s-%s"' % (sheetId,sheetClass)
		self._extraSheets.append( (sheetRel, sheetHref,sheetId+'-'+sheetClass,sheetClass,sheetMedia,sheetMisc) )

	def createAlerts(self,local=False): pass

	def getAlerts(self,local=False):
		self.createAlerts(local)

		if local:
			dt = datetime.datetime.now()-self.now
			time = dt.seconds+dt.microseconds/10.0**6
			c = 'good'
			if time >= 0.5 and time < 1.0: c = 'poor'
			elif time >= 1.0: c = 'bad'
			self.addDebug('%s - Creation Time: <span class="varible %s">%3.2f sec</span>' % (self.getControllerURI(self.__class__,'Unknown',False).title(), c, time))

		return self._alerts

	def addDebug(self,message):
		self.addAlert(True,'D',message)

	def addMessage(self,message,shown=True):
		if shown:
			self.addAlert(True,'I',message)

	def addAlert(self,condition,severity,message,priority=None):
		if self.testAlerts:
			if condition: message += ' <span class="alertTrue">True</span>'
			else: message += ' <span class="alertFalse">False</span>'

		if severity == 'D' and not self.debugAlerts:
			return

		if condition or self.testAlerts:
			alert = {}
			alert['severity'] = severity
			alert['message'] = message
			alert['priority'] = priority
			self._alerts.append(alert)

	def getAccessLevel(self,default=0):
		return self.getSessionValue('accessLevel',default)

	def setStatus(self,status):
		self._status = status

	def getStatus(self):
		if not self._status: return ''
		return self._status

	def getNavItems(self,ignoreAccess=False):
		global _navItems
		items = []
		for item in _navItems:
			if not ignoreAccess and item.accessLevel and not self.getAccessLevel() & item.accessLevel:
				continue
			items.append(item)
		return items

class HeaderController(StandardController):
	_filename = 'psp/header.psp'
	def getClass(self):
		if self.inputHidden: return 'filterhide'

class FooterController(StandardController):
	_filename = 'psp/footer.psp'
	def createContent(self):
		self.byteConf = PopUpMenuController(self.req,'&nbsp;',pop=PU.UP_LEFT)

		def param(var,val):
			from urllib import urlencode
			fields = self.getAllFields()
			fields[var] = val
			return '?%s' % self.escape(urlencode(fields))

		fixed = BytesToText.getFixed()

		fixedUnit = PopUpMenuController(self.req,'Fixed Units',pop=PU.LEFT_UP)
		fixedUnit.addItems(PopUpMenuController(self.req,'Tera',href=param('fixedUnit','T'),toggle=fixed=='T'))
		fixedUnit.addItems(PopUpMenuController(self.req,'Giga',href=param('fixedUnit','G'),toggle=fixed=='G'))
		fixedUnit.addItems(PopUpMenuController(self.req,'Mega',href=param('fixedUnit','M'),toggle=fixed=='M'))
		fixedUnit.addItems(PopUpMenuController(self.req,'Kilo',href=param('fixedUnit','K'),toggle=fixed=='K'))
		fixedUnit.addItems(PopUpMenuController(self.req,'Bytes',href=param('fixedUnit',''),toggle=fixed==True or fixed==''))
		fixedUnit.addItems(PopUpMenuController(self.req,'Off',href=param('fixedUnit','0'),toggle=fixed in (False,None)))

		digits = BytesToText.getPrecision()

		precision = PopUpMenuController(self.req,'Precision',pop=PU.LEFT_UP)
		precision.addItems(PopUpMenuController(self.req,'Default',toggle=digits==None))
		precision.addItems(PopUpMenuController(self.req,'4 Digits',href=param('precisionUnit',4),toggle=digits==4))
		precision.addItems(PopUpMenuController(self.req,'3 Digits',href=param('precisionUnit',3),toggle=digits==3))
		precision.addItems(PopUpMenuController(self.req,'2 Digits',href=param('precisionUnit',2),toggle=digits==2))
		precision.addItems(PopUpMenuController(self.req,'1 Digits',href=param('precisionUnit',1),toggle=digits==1))
		precision.addItems(PopUpMenuController(self.req,'No Digits',href=param('precisionUnit',0),toggle=digits==0))

		base = BytesToText.getBase()

		baseUnit = PopUpMenuController(self.req,'Base System',pop=PU.LEFT_UP)
		baseUnit.addItem(PopUpMenuController(self.req,'1000',href=param('baseUnit',1000),toggle=base==1000))
		baseUnit.addItem(PopUpMenuController(self.req,'1024',href=param('baseUnit',1024),toggle=base==1024))

		show = BytesToText.getShowUnit()

		showUnit = PopUpMenuController(self.req,'Show Unit',pop=PU.LEFT_UP)
		showUnit.addItem(PopUpMenuController(self.req,'On',href=param('showUnit',1),toggle=show==True))
		showUnit.addItem(PopUpMenuController(self.req,'Off',href=param('showUnit',0),toggle=show==False))

		self.byteConf.addItem(baseUnit)
		self.byteConf.addItem(fixedUnit)
		self.byteConf.addItem(precision)
		self.byteConf.addItem(showUnit)

		self.styleConf = PopUpMenuController(self.req,'&nbsp;',pop=PU.UP_LEFT)

		themes = PopUpMenuController(self.req,'Themes',pop=PU.LEFT_UP)
		theme = self.parent.getColorTheme()
		for name,file in _themes:
			themes.addItem(PopUpMenuController(self.req,name.capitalize(),href=param('color-theme-sheet',name),onclick='''toggleList(this);switchStyleSheets('%s','color-theme'); return false;''' % name,toggle=theme==name))

		shadows = PopUpMenuController(self.req,'Shadows',pop=PU.LEFT_UP)
		shadow = self.parent.getShadows()
		shadows.addItem(PopUpMenuController(self.req,'Full',href=param('shadows-sheet','full'),onclick='''toggleList(this);return !switchStyleSheets('full','shadows');''',toggle=shadow=='full'))
		shadows.addItem(PopUpMenuController(self.req,'Half',href=param('shadows-sheet','half'),onclick='''toggleList(this);return !switchStyleSheets('half','shadows'); return false;''',toggle=shadow=='half'))
		shadows.addItem(PopUpMenuController(self.req,'Off',href=param('shadows-sheet','off'), onclick='''toggleList(this);switchStyleSheets( null, 'shadows'); return false;''',toggle=shadow==False))

		layout = PopUpMenuController(self.req,'Base Layout',pop=PU.LEFT_UP)
		baselayout=self.parent.getBaseLayout()
		layout.addItem(PopUpMenuController(self.req,'Inner',href=param('baselayout-sheet','inner'),onclick='''toggleList(this);switchStyleSheets( 'inner', 'baselayout'); return false;''',toggle=baselayout=='inner'))
		layout.addItem(PopUpMenuController(self.req,'Outer',href=param('baselayout-sheet','outer'),onclick='''toggleList(this);switchStyleSheets( 'outer', 'baselayout'); return false;''',toggle=baselayout=='outer'))

		media = PopUpMenuController(self.req,'Media Type',pop=PU.LEFT_UP)
		printLayout = self.parent.getPrintLayout()
		media.addItem(PopUpMenuController(self.req,'Normal',href=param('printLayout',0),onclick='''toggleList(this);displayCSSMediaType(); return false;''',toggle=not printLayout))
		media.addItem(PopUpMenuController(self.req,'Print',href=param('printLayout',1),onclick='''toggleList(this);displayCSSMediaType('print'); return false;''',toggle=printLayout))

		self.styleConf.addItem(layout)
		self.styleConf.addItem(themes)
		self.styleConf.addItem(shadows)
		self.styleConf.addItem(media)

class ControllerItem:
	def __init__(self,controller,uri=None,navItem=True,navTitle=None,navHideInactive=False,
		grandparent=None,child=None,root=None,accessLevel=0):
		self.controller = controller
		self.uri = uri
		self.navItem = navItem
		self.navTitle = navTitle
		self.navHideInactive = navHideInactive
		self.staticTitle = navTitle
		self.grandparent = grandparent
		self.child = child
		self.root = root
		self.accessLevel = accessLevel

		self.isActive = False
		self.parent = None
		self.childActive = False
		self.children = []

	def isNavItem(self):
		return self.navItem
	
	def isVisible(self):
		if self.navHideInactive and not self.isActive: return False
		return (self.staticTitle or self.navTitle)

	def isLinkable(self):
		if self.uri: return True
		return False

	def getURI(self):
		return self.uri

	def getLink(self,parent):
		if self.controller: return parent.getControllerURI(self.controller)
		else: return parent.homePrefixIt(self.uri,self.root)

	def getType(self):
		if self.grandparent:
			return 'grandparent'
		elif not self.child:
			return 'parent'
		assert(self.child)
		return 'child'

	def getClass(self):
		c = []
		t = self.getType()
		c.append(t)

		if self.children:
			c.append('hasChilds')
			if self.childActive: c.append('hasActiveChild')

		hiddenChild = True
		if self.parent:
			if self.parent.isActive:
				c.append('parentActive')
				hiddenChild = False
			elif not self.isActive: c.append('parentInactive')
			for item in self.parent.children:
				if item.isActive and item != self:
					c.append('siblingActive')
					hiddenChild = False
		if self.child and hiddenChild and not self.isActive: c.append('hiddenChild')
		if self.isActive:
			c.append('active')
			c.append(t+'Active')
		return ' '.join(c)

	def getTitle(self,parent):
		return parent.escape(self.navTitle)

# URI => Controller
_uri2Controller = DefaultDict([])
# Controller => URI
_controller2URI = {}
# Displayed navItems in correct order
_navItems = []

def registerController(controller=None,uri=None,*arg,**keywords):
	root = keywords['root'] = keywords.get('root',rootPath)
	if not uri: index = keywords.get('navTitle',None)
	else: index = os.path.abspath(root+uri)

	item = ControllerItem(controller,uri,**keywords)

	if controller:
		_controller2URI[controller] = item

	if item.isNavItem():
		_navItems.append(item)

		if not item.grandparent:
			# find parent
			parent = None
			for navItem in _navItems[-2::-1]:
				if (item.child and not navItem.child) or (not item.child and navItem.grandparent):
					item.parent = navItem
					navItem.children.append(item)
					break
			# TODO: add better error/handling/feedback here
			#assert(parent and "navItem has no parent!")

	_uri2Controller[index].append( item )

class NavController(BaseController):
	_filename = 'psp/nav.psp'

	_activeController = None
	def createContent(self):
		activeController = self.getActiveController()

		for item in self.getNavItems():
			item.childActive = False
			item.isActive = False
			if activeController == item.controller:
				item.isActive = True
				if item.parent: item.parent.childActive = True

			if item.controller and not item.staticTitle:
				dummy = item.controller(self.req,createContent=False)
				item.navTitle = dummy.getTitle(active=item.isActive,navTitle=True)

	def updateItem(self,controller):
		item = _controller2URI.get(controller.__class__,None)
		if item:
			item.navTitle = controller.getTitle(active=item.isActive,navTitle=True)
		if isinstance(controller,BaseController):
			if controller._highlightController:
				self.highlightController(controller._highlightController)

	def getActiveController(self):
		if self._activeController: return self._activeController
		self._activeController = self.getControllerByURI()
		return self._activeController

	def setActiveController(self,controller):
		self._activeController = controller

	def highlightController(self,controller):
		for item in self.getNavItems():
			if controller == item.controller:
				item.isActive = True
				if item.parent: item.parent.childActive = True

class AlertController(TableController):
	def __init__(self,req,alerts=[],number=None,of=None,newLook=None):
		if newLook == None: newLook = True
		self.newLook = newLook

		extra = ''
		if number: extra += '_%d' % number
		if of: extra += '_of_%d' % of

		if not newLook:
			TableController.__init__(self,req,'alerts%s' % extra,
				'Messages & Alerts',dbOrder=False,showHeaders=False,className='alertTable',emptyMessage='')
			self.addHeader(TH('severity', 'Severity',TH.HTML,sorted=True,sortable=True))
			self.addHeader(TH('message', 'Message',TH.TEXT))
		else:
			TableController.__init__(self,req,'alerts%s' % extra,
				None,dbOrder=False,className='newAlertTable',emptyMessage='')
			self.addHeader(TH('message', 'Messages & Alerts',TH.HTML,sorted=True,sortable=True))

		for alert in alerts:
			self.addAlert(**alert)

	def addAlert(self,message,severity='I',priority=None):
		if priority == None:
			priority = len(self._rows)

		i = {}
		i['message'] = message
		if severity == 'E':
			i['rowclass'] = 'error'
			severity = '<!--0.%05d-->'
		elif severity == 'I':
			i['rowclass'] = 'info'
			severity = '<!--2.%05d-->'
		elif severity == 'W':
			i['rowclass'] = 'warning'
			severity = '<!--1.%05d-->'
		else: # severity == 'D':
			i['rowclass'] = 'debug'
			severity = '<!--3.%05d-->'

		if not self.newLook:
			i['severity'] = '<span>%s&nbsp;</span>' % (severity%priority)
			self.addRow(**i)
		else:
			i['message'] = '<span class="alertIcon">%s%s</span>' % ((severity%priority),i['message'])
			#escape(i['message']))
			self.addRow(**i)

class PopUpMenuController(StandardController):
	_filename = 'psp/popup.psp'
	LEFT_UP='left-up'
	LEFT_DOWN='left-down'
	UP_LEFT='up-left'
	UP_RIGHT='up-right'
	RIGHT_UP='right-up'
	RIGHT_DOWN='right-down'
	DOWN_LEFT='down-left'
	DOWN_RIGHT='down-right'
	def __init__(self, req, value=None, href=None,onclick=None,pop=None,items=[],toggle=None,parent=None):
		StandardController.__init__(self,req,createContent=False,parent=parent)
		self.value = value
		self.href = href
		self.onclick = onclick
		self.items = []
		self.toggle = toggle
		if not pop: pop = self.UP_LEFT
		assert(pop in (self.LEFT_UP,self.LEFT_DOWN,self.UP_LEFT,self.UP_RIGHT,self.RIGHT_UP,self.RIGHT_DOWN,self.DOWN_LEFT,self.DOWN_RIGHT))
		self.pop = pop
		self.addItems(*items)
	
	def addItems(self,*items):
		for item in items: self.addItem(item)

	def addItem(self,item,index=None):
		if isinstance(item,StandardController):
			assert(item.parent==None or item.parent ==self)
			item.parent = self
		if index==None or index==-1:
			self.items.append(item)
		else:
			self.items.insert(index,item)

	def getLevel(self,plus=0):
		level = 0+plus
		parent = self.parent
		while isinstance(parent,PopUpMenuController):
			parent = parent.parent
			level += 1
		return level

	def getUlClass(self,plus=0):
		c = ['level%d' % self.getLevel(plus)]
		if self.items:
			c.append('subs')
		return ' '.join(c)

	def getLIClass(self,item=None):
		c = []
		if item == None:
			item = self
		if isinstance(item,PopUpMenuController):
			if item.items:
				c.append(item.pop)
			if item.toggle != None:
				s = '-off'
				if item.toggle: s = '-on'
				c.append(item.pop.replace('-','').replace('up','').replace('down','')+s)
			if not item.href and not item.onclick:
				c.append('nohref')
				if not item.items: c.append('inactive')

		return ' '.join(c)

	def getItem(self):
		s = ''
		if self.value:
			s += self.value
		if self.href or self.onclick:
			t = []
			if self.href: t.append('href="%s"' % self.href)
			if self.onclick: t.append('onclick="%s"' % self.onclick)
			s += '<a %s></a>' % ' '.join(t)
		return s

class PU(PopUpMenuController): pass

# I really dont like this behavour, really messy to understand
class SpecialController(StandardController):
	def getControllerByURI(self,default):
		filename=os.path.abspath(self.req.filename+self.req.path_info)
		if _uri2Controller[filename]:
			items = _uri2Controller[filename]
			for item in items:
				if item.controller:
					if issubclass(item.controller,SpecialController):
						return item.controller

		return default

	def handleRequest(self):
		controller = self.getControllerByURI(None)

		if controller:
			return controller(self.req).handleRequest()
		#return apache.HTTP_NOT_FOUND
		return None

import dircache
class ReturnLog(SpecialController):
	def handleRequest(self):
		log = os.path.basename(self.getField('l',''))
		if not log:
			self.req.content_type = 'text/html'

			for file in dircache.listdir('%s/' % getTempPath('logs')):
				self.req.write( '<a href="?l=%s">%s</a><br/>' % (file,file) )

			return apache.OK

		self.req.content_type = 'application/xml'
		filename = '%s/%s' % ( getTempPath('logs'), log )
		if not os.path.exists(filename):
			raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
		self.req.write(open(filename).read())
		#self.req.sendfile(filename)
		return apache.OK

