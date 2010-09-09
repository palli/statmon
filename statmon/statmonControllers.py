
from core.environment import logger,getTempPath
from core.utils import getCurrentUser,getCurrentGroup,StringToBool
from core.standardControllers import StandardController,currentPath
from core.baseControllers import BaseController,BlankController,SpecialController,AlertController,registerController
from core.inputControllers import InputItem,II
from core.tableControllers import TableController,TH

from defaultConfig import configStatmonGrapher,configStatmonMisc

# model.getDB preferred for readability / traceability
import model

from mod_python import apache
from urllib import urlencode
from cgi import escape

import time, datetime, os, random

currentPath = os.path.dirname(__file__)+'/'
# TODO: read from config
_extraCSS = '../custom.css'
_hasExtraCSS = None
_serverName = None

class OfflineStatmonController(BaseController):
	""" Controller with statmon specfic stuff
		Should not init nor depend on DB to function
		TODO: work in progress, used by
			Help, About controller
	"""
	_title = 'TSM Status Monitor'
	_pspPath = currentPath

	def preCreate(self):
		BaseController.preCreate(self)
		self.accessControl()

	def accessControl(self):
		login = StringToBool(self.getField('login'))
		logout = StringToBool(self.getField('logout'))
		if logout:
			# invalidate session
			self.getSession().invalidate()
			# destroy remember cookies
			self.clearRemember(self.getBasepath())
			login = False

		from controllers import MASTER_ACCESS, PRELOGIN, LOGGED, DEV_ACCESS

		# force default accessLevel to PRELOGIN if not set and hasStatmonACL
		if model.hasStatmonACL():
			if not self.getSessionValue('logged',default=False,init=True):
				self.setSessionValue('accessLevel',PRELOGIN)
		else:
			# else set accessLevel to MASTER_ACCESS (omitting ACL_EDIT_ACCESS)
			# force regardless of exiting value
			self.setSessionValue('accessLevel',MASTER_ACCESS)
			login = False

		# validate if login params are supplied
		remember = self.getCookie('rememberUser',False)
		if login or (remember and not logout):
			user = self.getField('user','')
			password = self.getField('pass','')
			onepass = self.getField('opass','')

			statmonUser = None
			if (user and onepass):
				oneTimeUser = model.getStatmonUser(user)
				if onepass in self.oneTimePass(oneTimeUser,forValidation=True):
					statmonUser = oneTimeUser

			if (user and password) or remember or statmonUser:
				refreshRemember = False
				# attempt cookie validation
				if remember and not statmonUser:
					rememberUser = model.getStatmonUser(remember)
					if rememberUser and self.getCookie('rememberCert',secret=rememberUser.password) == rememberUser.user:
						model.validateStatmonUser(rememberUser.user) # touch last login timestamp
						statmonUser = rememberUser
						refreshRemember = True
					else:
						self.clearRemember(self.getBasepath())

				# attempt normal validation
				if model.validateStatmonUser(user,password):
					statmonUser = model.getStatmonUser(user,password)
	
				if statmonUser:
					self.setSessionValue('logged',True)
					self.setSessionValue('user',statmonUser.user)
					accessLevel = statmonUser.access|LOGGED
					self.setSessionValue('accessLevel',accessLevel)

					# refresh or set remember cookies
					if (self.getField('remember',False) or refreshRemember) and statmonUser.password and not onepass:
						self.setRemember(self.getBasepath(),statmonUser.user,statmonUser.password)

		# force login if not logged in and (page requires login or user requests login)
		if (model.hasStatmonACL() and
			not self.getSessionValue('logged',False,True) and
			(self.getControllerByURI(notFound=False,overrideFound=False,forbidden=True)
			or login)):

			redirectURL = ''
			for item in self.getNavItems(ignoreAccess=True):
				if item.navTitle == 'Logout':
					if item.getURI()[0:2] == '..':
						redirectURL = item.getLink(self)
					break
			if redirectURL:
				from mod_python.util import redirect
				redirect(self.req,redirectURL)
			else:
				from settingsControllers import LoginController
				self.overrideContent = LoginController
				self._highlightController = LoginController

		global _serverName
		if not _serverName:
			try:
				_serverName = model.getStatus()[0].server_name
			except: _serverName = None

		if model.hasStatmonACL():
			if self.getSessionValue('user'):
				if _serverName:
					self.setStatus(self.getSessionValue('user')+'@'+_serverName)
				else:
					self.setStatus(self.getSessionValue('user'))

		if self.getAccessLevel()&DEV_ACCESS:
			self.debugAlerts = True

	def clearRemember(self,path):
		self.deleteCookie('rememberUser',path=path)
		self.deleteCookie('rememberCert',path=path)

	def setRemember(self,path,user,password):
		expires=time.time()+2600000
		path=self.getBasepath()
		self.setCookie('rememberUser',user,expires=expires,path=path)
		self.setCookie('rememberCert',user,secret=password,expires=expires,path=path)

	def oneTimePass(self,statmonUser,forValidation=False):
		import time, md5, datetime
		count=2
		period=600
		passes = []
		now = time.time()
		for offset in range(count):
			digest = md5.new(statmonUser.user)
			digest.update(str(statmonUser.password))
			digest.update(str(int(now/period)-offset))
			passes.append(digest.hexdigest())
			if not forValidation: break
		if not forValidation:
			expires = period*(int(now/period)+count)
			return passes[0],datetime.datetime(*time.gmtime(expires)[:6])
		return passes

	def createContent(self):
		global _hasExtraCSS

		self.addStyleSheet(self.homePrefixIt('css/statmon.css',cwd=currentPath),'normal',sheetClass='statmon')
		self.addStyleSheet(self.homePrefixIt('css/print.css',cwd=currentPath),'print',sheetClass='statmon',sheetMedia='print')

		if _hasExtraCSS == None:
			if os.path.exists(os.path.abspath(currentPath+_extraCSS)): _hasExtraCSS = True
			else: _hasExtraCSS = False
		if _hasExtraCSS:
			self.addStyleSheet(self.homePrefixIt(_extraCSS,cwd=currentPath))

		#if configStatmonInternal('.failedToLoad').getValue():
			#self.injectedContent = FailedReadConfigController(self.req)

		BaseController.createContent(self)
	
	#def addAlert(self,condition,severity,message,priority=None):
		#from controllers import DEV_ACCESS
		#if severity != 'D' or self.getAccessLevel()&DEV_ACCESS:
			#BaseController.addAlert(self,condition=condition,severity=severity,message=message,priority=priority)

class FailedReadConfigController(OfflineStatmonController):
	# TODO: unbreak
	# TODO: move elsewhere
	_filename = 'psp/failedReadConfig.psp'
	def createContent(self):
		dialogTable = TableController(self.req,'alert','Failed to Load Config!',showHeaders=False)
		dialogTable.addHeader(TH('text', 'text',TH.HTML,sorted=False,sortable=False))
		configFullpath = configStatmonInternal('.configFullpath').getValue()
		configName = os.path.basename(configFullpath)
		handlerFullpath = configStatmonInternal('.handlerFullpath').getValue()
		handlerDir = os.path.dirname(handlerFullpath)
		handlerName = os.path.basename(handlerFullpath)
		configFancy = """'%s'""" % self.makeBold(configFullpath)
		user = getCurrentUser()
		group = getCurrentGroup()
		link = self.getControllerURI(SettingsController)
		text = """
		Failed to read configuration from %s<br/>
		<br/>
		To generate a new config file please run following commands:<br/>
		<div class="text-box">
			<pre>cd %s</pre>
			<pre>python %s configure</pre>
			<pre>chmod g+r %s</pre>
			<pre>chgrp %s %s</pre>
			<pre>apachectl restart</pre>
		</div><br/>""" % (configFancy,handlerDir,handlerName,configName,group,configName)
		text += """
		Alternately verify that %s exists and is read/writeble by either user %s or group %s using following commands:<br/>
		<div class="text-box">
			<pre>touch %s</pre>
			<pre>chmod u+rw %s</pre>
			<pre>chown %s:%s %s</pre>
			<pre>apachectl restart</pre>
		</div>
		Then <a href="%s">click this link</a> for in browser configuration.<br/>""" % (configFancy,self.makeBold(user),self.makeBold(group),configFullpath,configFullpath,user,group,configFullpath,link)
		dialogTable.addRow(text=text)
		self.dialogTable = dialogTable.getContent()
	def makeBold(self,string,bold='bold'):
		return '<span style="font-weight: %s;">%s</span>' % (bold,string)

#class FailedWriteConfigController(OfflineStatmonController):
	#_filename = 'psp/failedWriteConfig.psp'
	#def createContent(self): pass

class StatmonController(OfflineStatmonController):
	""" Controller with statmon specfic stuff
		Depends on DB
	"""

	def __init__(self, req,createContent=True,preCreate=True,parent=None):
		BaseController.__init__(self,req,False,parent=parent)
		self.parent = None
		if isinstance(parent,StatmonController): self.parent = parent

		if not createContent: return
		self.preCreate()
		self.createContent()
		self.postCreate()

	def getDB(self):
		# intercept hook, unused
		return model.getDB()

	def preCreate(self):
		OfflineStatmonController.preCreate(self)

		if self.parent:
			self.graphStart = self.parent.graphStart
			self.graphEnd = self.parent.graphEnd
			self.historyStart = self.parent.historyStart
			self.standardInputs = self.parent.standardInputs
		else:
			# this should be the only used default start/end used now.. hopefully

			self.graphStart = self.today-datetime.timedelta(days=configStatmonGrapher.graphStart.getValue())
			self.graphEnd = self.today-datetime.timedelta(days=configStatmonGrapher.graphEnd.getValue())
			self.historyStart = self.today-datetime.timedelta(days=configStatmonMisc.backupHistoryStart.getValue())

			autoWilds = lambda x: self.autoWilds(x)
			autoWildsNode = lambda x: self.autoWilds(x,testNode=True)
			autoWildsDomain = lambda x: self.autoWilds(x,testDomain=True)

			# reusable inputs
			self.standardInputs = {
				'domain' :
					InputItem('domain','Domain Name',II.TEXT,allowBlank=True,blankVal='%',postProcess=autoWildsDomain),
				'node' :
					InputItem('node','Node Name',II.TEXT,allowBlank=True,blankVal='%',postProcess=autoWildsNode),
				'stgpool' :
					InputItem('stgpool','Storage Pool Name',II.TEXT,allowBlank=True,blankVal='%',postProcess=autoWilds),
				'schedule' :
					InputItem('schedule','Schedule Name',II.TEXT,allowBlank=True,blankVal='%',postProcess=autoWilds),
				'findnode' :
					InputItem('node','Node Name',II.TEXT),
				'findschedule' :
					InputItem('schedule','Schedule Name',II.TEXT),
				'graphstart' :
					InputItem('start','Graphs Start',II.DATE,default=self.graphStart,blankVal=self.graphStart),
				'historystart' :
					InputItem('start','Since Date',II.DATE,default=self.historyStart,blankVal=self.historyStart),
				'startweekago' :
					InputItem('start','Start Date',II.DATE,default=self.weekago,blankVal=self.weekago),
				'startyesterday' :
					InputItem('start','Start Date',II.DATE,default=self.yesterday,blankVal=self.yesterday),
				'graphend' : 
					InputItem('end','Graphs End',II.DATE,default=self.graphEnd,blankVal=self.graphEnd),
				'endtoday' :
					InputItem('end','End Date',II.DATE,default=self.today,blankVal=self.today),
				'endyesterday' :
					InputItem('end','End Date',II.DATE,default=self.yesterday,blankVal=self.yesterday),
				'msgno' :
					InputItem('msgno','Message ID',II.NUMBER,allowBlank=True,blankVal=None),
				'msgcon' :
					InputItem('msgcon','Message Contains',II.TEXT,allowBlank=True,blankVal=None,postProcess=autoWilds),
			}

		# setup basic stuff needed by grapher
		self.params = {
			'nodefilter' : None,
			'nodelist' : None,
			'domainfilter' : None,
			'domainlist' : None,
			'stgpoolfilter' : None,
			'stgpoollist' : None,
			'node' : None,
			'schedulefilter' : '%',
			'graphstart' : self.graphStart,
			'graphend' : self.graphEnd,
			'imagewidth' : configStatmonGrapher.graphWidth.getValue(),
		}

		self.graphs = False

	def postCreate(self):
		BaseController.postCreate(self)

		# Create Alerts
		alerts=self.getAlerts(local=True)
		self.alertTable = AlertController(self.req,alerts)

		if self._splitAlerts:
			self.alertTables = []
			splits = self._splitAlerts
			from math import ceil
			for i in range(splits):
				start = int(ceil(i*len(alerts)/float(splits)))
				end = int(ceil((i+1)*len(alerts)/float(splits)))
				if end-start:
					alertTable = AlertController(self.req,alerts[start:end],number=i+1,of=splits)
					self.alertTables.append( alertTable )

	def linkNode(self,node,maxLength=None):
		from coreControllers import NodeController

		if not node or node == 'None': return ''

		text = node
		if maxLength and len(text) > maxLength: text = text[:maxLength-2]+'...'

		return '<a href="%s?node=%s">%s</a>' % (
			self.getControllerURI(NodeController), escape(node), escape(text) )
	def linkDomain(self,domain):
		from coreControllers import DomainController
		if not domain or domain == 'None': return domain
		domain = escape(domain)
		return '<a href="%s?domain=%s">%s</a>' % (
			self.getControllerURI(DomainController), domain, domain )
	def linkStoragePool(self,pool):
		from coreControllers import StoragePoolController
		pool = escape(pool)
		return '<a href="%s?poolname=%s">%s</a>' % (
			self.getControllerURI(StoragePoolController), pool, pool )
	def linkActlog(self,nodefilter=None,message=None,start=None,end=None,maxLength=None,title=''):
		from coreControllers import ActlogController
		querystring = '<a class="gant_link" href="%s?%s" title="%s"></a>'
		uri= self.getControllerURI(ActlogController)
		params = {}
		if nodefilter: params['node'] = nodefilter
		if message: params['msgcon'] = message
		if start: params['start'] = start
		if end: params['end'] = end
		if maxLength != None: params['length'] = maxLength
		querystring = querystring%(uri,urlencode(params),title)
		return querystring
	def linkSchedule(self,schedule,domain):
		from coreControllers import ClientScheduleController
		schedule = escape(schedule)
		domain = escape(domain)
		return '<a href="%s?schedule=%s&domain=%s">%s</a>' % (
			self.getControllerURI(ClientScheduleController), schedule, domain, schedule )
	def linkGraph(self,text,graph=None,controller=None):
		if not graph: return text
		if controller == None:
			from coreControllers import ZoomController
			controller = ZoomController

		param = urlencode({'p':encodeGraph(graph)})
		uri = self.getControllerURI(controller)

		return '<a href="%s?%s">%s</a>' % (uri, param, text)
	def displayGraph(self,graph,shadowdrop=True,directLink=False):
		if not graph: return ''

		staticTitle = graph.getStaticTitle()
		graphId = staticTitle[:1] + str(random.randrange(10000,99999)) + staticTitle[-1:]

		content = self.makeGraphTable(graph,graphId=graphId,staticTitle=staticTitle,directLink=directLink)
		if shadowdrop:
			content = self.shadowdrop( content )

		return self.graph( content, graphId )
	
	#def getImageURI(self):
		#return self.getControllerURI(ReturnImage)

	def getGraphURI(self):
		return self.getControllerURI(ReturnGraph)

	def makeGraphTable(self,graph,graphId,staticTitle,directLink):
		src = self.getControllerURI(ReturnGraph)

		force = {}
		if graph.format in 'svg':
			img = '<embed'
		else:
			force['format'] = 'PNG'
			img = '<img'

		param = escape(urlencode({'p':encodeGraph(graph,force)}))
		img += ' src="%s?%s" alt="Loading %s Graph..."/>' % (src,param, graph.getTitle())
		if directLink: controller = ReturnGraph
		else: controller = None

		# TODO: this probably shouldn't be generating a table, rather divs, or should it..
		table = '''
		<table class="graph">
			<thead>
				<tr class="nopretty title even">
					<td class="nopadding top">
							<div class="title">
								<a class="button" href="#" onclick="toggleDisplay('%s'); return false;"><span class="active">&nbsp;</span></a>
								%s
							</div>
					</td>
				</tr>''' % (graphId, self.escape(staticTitle))
		if graph.getStaticTitle() != graph.getTitle():
			table += '''
				<tr class="nopretty odd">
						<td class="center">
							%s
						</td>
				</tr>''' % graph.getTitle()
		table += '''
			</thead>
			<tbody class="highlight">
				<tr class="odd"><td class="image">%s</td></tr>
			</tbody>
		</table>''' % self.linkGraph(img,graph,controller=controller)

		return table

	def createAlerts(self,local=False): pass

	def graph(self,content,graphId):
		if not content: return content
		graph = GraphController(self.req)
		graph.content = content
		graph.graphId = graphId
		return graph.getContent()

	def getClass(self):
		return os.path.basename(self._filename).replace('.','-')

	def escape(self,string):
		if type(string)!=type(''):
			return string
		return escape(string)

	def autoWilds(self,string,testNode=False,testDomain=False):
		if not string: return string
		if testNode and model.getNodes(nodefilter=string,countOnly=True): return string
		if testDomain and model.getDomains(domainfilter=string,countOnly=True)>0: return string
		for wildchar in '%*?':
			if wildchar in string: return string
		return '*' + string + '*'

	def getStartEnd(self,startInput,endInput):
		if type(startInput) in (str,unicode): startInput = self.standardInputs[startInput]
		if type(endInput) in (str,unicode): endInput = self.standardInputs[endInput]
		
		a = self.processInput(startInput)
		b = self.processInput(endInput)

		start = min(a,b)
		end = max(a,b)

		if a != start: self.updateInput(startInput.sname,start)
		if b != end: self.updateInput(endInput.sname,end)

		return start,end

class GraphController(OfflineStatmonController):
	_filename = 'psp/graph.psp'
	def createContent(self): pass

def encodeGraph(graph,override={}):
	from cPickle import dumps
	from base64 import encodestring
	params = graph.getParams()
	params['grapher'] = graph.__class__

	for key,value in override.items(): params[key] = value

	return encodestring(dumps(params))

def decodeGraph(string):
	from base64 import decodestring
	from cPickle import loads,PicklingError
	from types import ClassType

	params = {}
	try:
		params = loads(decodestring(string))
	except PicklingError, e: pass
	except TypeError, e: pass

	from grapher import Grapher
	grapher = params.pop('grapher',None)
	if type(grapher) is not ClassType or not issubclass(grapher,Grapher): grapher = None

	return grapher,params

#class ReturnImage(SpecialController):
	#def handleRequest(self):
		#self.req.content_type = 'image/png'
		#image = os.path.basename(self.getField('i',''))
		#filename = '%s/%s' % ( getTempPath('images'), image )
		#if not os.path.exists(filename):
			#raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
		#self.req.sendfile(filename)
		#return apache.OK

class ReturnGraph(SpecialController):
	def handleRequest(self):
		Grapher,params = decodeGraph(self.getField('p'))
		if not Grapher:
			return apache.HTTP_INTERNAL_SERVER_ERROR

		for key,value in {
			'db' : model.getDB(),
			'datapath' : '%s/' % getTempPath('data'),
			'imagepath' : '%s/' % getTempPath('images'),
			'logger' : logger,
			'graph' : False,
			'maxage': 600,
			'hidetitle' : True,
			'graph' : True,
		}.items(): params[key] = value

		graph = Grapher(**params)

		filename = graph.getFullPathImagename()

		self.req.content_type = {
			'png' : 'image/png',
			'svg' : 'image/svg+xml',
			'eps' : 'application/postscript',
			'pdf' : 'application/pdf',
		}[graph.format.lower()]	

		if not os.path.exists(filename):
			raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
		self.req.sendfile(filename)

		return apache.OK

#registerController(ReturnImage, 'image', navItem=False)
registerController(ReturnGraph, 'graph', navItem=False)

