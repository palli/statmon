
import random
import time
import datetime

from mod_python import apache
from baseControllers import SpecialController, registerController, BaseController, PopUpMenuController, PU, _uri2Controller, AlertController
from tableControllers import TableController,TH,PropTableController,TR
from inputControllers import InputController,II

#from statmonControllers import StatmonController,AlertController
#from statmon.statmonControllers import OfflineStatmonController
#from statmon.helpControllers import OfflineStatmonController

class TestsController(BaseController):
	_title = 'Tests'
	def getContent(self):
		l = []
		l.append('<h2>Tests:</h2>')
		l.append('<ul>')
		t = []
		for key,items in _uri2Controller.items():
			for item in items:
				tokens = key.rsplit('tests/')
				if len(tokens) > 1:
					try:
						title = item.controller._title
					except:
						title = ' '.join(map(lambda x: x.capitalize(),tokens[1].split('/')))
					string = '<li class="normal-list"><a href="%s">%s</a></li>' % (self.getControllerURI(item.controller),title)
					t.append((title,string))
		t.sort(key=lambda x:x[0])
		l += map(lambda x:x[1],t)
		l.append('</ul>')
		return '\n'.join(l)
registerController(TestsController, 'tests',navItem=False)

class TestSpecial(SpecialController):
	def handleRequest(self):
		self.req.write("OK OK\n")
		return apache.OK
registerController(TestSpecial, 'tests/test/simple/special/controller',navItem=False)

class TestBaseContent(BaseController):
	_title = 'Test Simple PSP Less Content Controller'
	def getContent(self): return '<h2>OK OK</h2>\n'
registerController(TestBaseContent, 'tests/simple/psp/less/content',navItem=False)

class TestMissingContentPSP(BaseController):
	_title = 'Test Error Handling - Missing Content PSP - No Dump'
	_filename = 'nonexistant.psp'
registerController(TestMissingContentPSP, 'tests/missing/content/psp',navItem=False)

class TestMissingBasePSP(BaseController):
	_title = 'Test Error Handling - Missing Base PSP - No Dump'
	_filename = 'nonexistant.psp'
	def createContent(self):
		self.parent._filename = self._filename
registerController(TestMissingBasePSP, 'tests/missing/base/psp',navItem=False)

class TestTest(BaseController):
	_title = 'Test Complex PSP Content Controller'
	_filename = 'psp/test.psp'
	def generateString(self,length):
		s = ''
		for i in xrange(length): s+= random.choice('.abcdefghijk ')
		return s.strip()
		
	def createContent(self):
		
		#begin Input
		simpleInput = InputController(self.req,'Simple Input')

		now = datetime.datetime.now()
		options = [('abc','abc..'),('def','def..')]

		seed = simpleInput.processInput(II('seed','Seed Number',II.NUMBER,default=random.randint(0,10000)))
		incr = simpleInput.processInput(II('incr','Seed Increment',II.NUMBER,default=1))
		texta = simpleInput.processInput(II('texta','Test Text A',II.TEXT,allowBlank=True,blankVal='%'))
		textb = simpleInput.processInput(II('textb','Test Text B',II.TEXT,default='foo'))
		datec = simpleInput.processInput(II('datec','Test Date C',II.DATE,allowBlank=True,blankVal=now))
		dated = simpleInput.processInput(II('dated','Test Date D',II.DATE,default=now))
		opte = simpleInput.processInput(II('opte','Test Drop Down E',II.DROPDOWN,options=options,allowBlank=True,blankVal='Blank'))
		optf = simpleInput.processInput(II('optf','Test Drop Down F',II.DROPDOWN,options=options,default='def'))

		seed = simpleInput.updateInput('seed',seed+incr)
		self.simpleInput = simpleInput.getContent()

		#begin prop table
		simpleProps = PropTableController(self.req,'Simple Stuff')
		simpleProps.addRow(TR('Seed Number',seed,TR.NUMBER))
		simpleProps.addRow(TR('Seed Increment',incr,TR.NUMBER))
		simpleProps.addRow(TR('Test Text A',texta,TR.TEXT))
		simpleProps.addRow(TR('Test Text B',textb,TR.TEXT))
		simpleProps.addRow(TR('Test Date C',datec,TR.DATETIME))
		simpleProps.addRow(TR('Test Date D',dated,TR.DATETIME))
		simpleProps.addRow(TR('Test Text B',type(dated),TR.TEXT))
		simpleProps.addRow(TR('Test Drop Down E',opte,TR.TEXT))
		simpleProps.addRow(TR('Test Drop Down F',optf,TR.TEXT))

		self.simpleProps = simpleProps.getContent()

		#begin simple table
		self.simpleTable = simpleTable = TableController(self.req,'simpleTable','Simple Table',dbOrder=False)
		simpleTable.addHeader(TH('text', 'Text',TH.TEXT,sorted=True))
		simpleTable.addHeader(TH('bytes', 'Bytes',TH.BYTES))
		simpleTable.addHeader(TH('number', 'Number',TH.NUMBER))
		simpleTable.addHeader(TH('time', 'Time',TH.TIME))
		simpleTable.addHeader(TH('date', 'Date',TH.DATE))
		simpleTable.addHeader(TH('datetime', 'Date Time',TH.DATETIME))
		simpleTable.addHeader(TH('float', 'Float',TH.FLOAT))
		#simpleTable.addHeader(TH('html', 'Raw HTML',TH.HTML))
		simpleTable.addHeader(TH('html2', 'Raw HTML',TH.HTML))

		random.seed(seed)
		for i in random.sample(xrange(1000),max(0,int(random.normalvariate(10,15)))):
			random.seed(i)
			li_type = random.choice(['error','info','warning'])
			image = 'img/li_%s.png' % li_type
			image2 = image.replace('li_','')
			row = {
				'text' : self.generateString(max(2,int(random.normalvariate(30,15)))),
				'bytes' : min(2**64,max(0,int(2**random.normalvariate(36,15)))),
				'number' : i,
				'time' : datetime.datetime.now()+datetime.timedelta((random.random()-.5)*2000),
				'date' : datetime.datetime.now()+datetime.timedelta((random.random()-.5)*2000),
				'datetime' : datetime.datetime.now()+datetime.timedelta((random.random()-.5)*2000),
				'float' : random.random()*1000,
				'html' : '<img src="%s" alt="%s"/>' % (self.homePrefixIt(image),li_type[0]),
				'html2' : '<img src="%s" alt="%s"/>' % (self.homePrefixIt(image2),li_type[0])
			}
			simpleTable.addRow(**row)

		self.simplePopUp = PopUpMenuController(self.req,'Up-Left',pop=PU.UP_LEFT)

		#self.addItems(self.simplePopUp,3)
		self.addItems(self.simplePopUp,2,all=False)

		# Create Alerts
		alerts=self.getAlerts(local=True)
		self.alertTable = AlertController(self.req,alerts)
	
	def addItems(self,poper,depth=3,all=False):
		dirs = (PU.UP_LEFT,PU.UP_RIGHT,PU.LEFT_DOWN,PU.RIGHT_DOWN,PU.LEFT_UP,PU.RIGHT_UP,PU.DOWN_LEFT,PU.DOWN_RIGHT)
		leaf = True
		if not all:
			dirs = random.sample(dirs,min(random.randrange(0,5),len(dirs)))

		for direction in dirs:
			href = random.choice(['#',None,None])
			subPoper = PopUpMenuController(self.req,direction,href=href,pop=direction)
			if depth<=0 or self.addItems(subPoper,depth-1,all):
				l = 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Curabitur at dolor. Sed vitae mauris sed ante tempus iaculis. Maecenas et nulla accumsan nulla posuere tempus. Praesent fringilla turpis. Sed auctor quam ut pede. Vestibulum nulla. Suspendisse quis libero. Fusce pede velit, dignissim at, rhoncus ac, condimentum vitae, metus. Vivamus vehicula, mi sit amet eleifend sodales, felis est vehicula mauris, at luctus ligula est vel massa. Quisque dapibus. Nam aliquet orci vitae mi. Vivamus egestas libero. Proin egestas nonummy sem. Quisque at massa et lorem nonummy tristique. Vivamus luctus, sem ut mollis interdum, nibh nulla vehicula mi, facilisis auctor ante nunc venenatis tellus. Duis ornare. Sed tincidunt nisi. Nulla viverra felis vitae libero.'.split()
				subPoper.value = ' '.join(random.sample(l,random.randrange(1,3)))
			poper.addItem(subPoper)
			leaf = False
		return leaf

registerController(TestTest, 'tests/test',navItem=False)

class TestCodeError(BaseController):
	_title = 'Test Error Handling - Code failure - Readable Dump'
	def createContent(self):
		# we fail here
		failure
registerController(TestCodeError, 'tests/code/error',navItem=False)

class TestPSPError(BaseController):
	_title = 'Test Error Handling - PSP Code failure - Readable Dump'
	_filename = 'psp/broken.psp'

registerController(TestPSPError, 'tests/psp/code/error',navItem=False)

class LogsViewer(BaseController):
	_title = 'Logs'


class TestEmptyController(BaseController):
	pass

registerController(TestEmptyController, 'tests/test/empty/controller',navItem=False)

class TestDumpSessions(BaseController):
	_filename = 'psp/sessions.psp'
	_title = 'List Sessions'
	def createContent(self):
		self.sessions = []
		i = 0
		for session in self.getAllSessions():
			sid = session.id()[0:16]+'...'
			sessionTable = PropTableController(self.req,sid)

			if i == 0:
				sessionTable.addRow(TR('type','global',TR.TEXT))
			elif i == 1:
				sessionTable.addRow(TR('type','current',TR.TEXT))
			else:
				sessionTable.addRow(TR('type','other',TR.TEXT))

			sessionTable.addRow(TR('created',session.created(),TR.TEXT))
			sessionTable.addRow(TR('last_accessed',session.last_accessed(),TR.TEXT))
			sessionTable.addRow(TR('timeout',session.timeout(),TR.TEXT))

			keys = session.keys()
			keys.sort()
			for name in keys:
				value = session[name]
				if name == 'sessions':
					value = map(lambda x: x[0:16]+'...',value)
					value = ', '.join(value)
				sessionTable.addRow(TR(name,repr(value),TR.TEXT))
			self.sessions.append(sessionTable)
			i += 1

registerController(TestDumpSessions, 'tests/sessions',navItem=False)


#class TestAlerts(StatmonController):
	#_title = 'Test Alerts'
	#_filename = 'psp/testAlerts.psp'

	#def createContent(self):
		#simpleInput = InputController(self.req,'Configure Test')
		#now = simpleInput.processInput(II('now','Override Now',II.DATE,default=self.now,allowBlank=True,blankVal=self.now))
		#now = now.combine( now.date(), self.now.time() )
		#options = [('no','No'),('yes','Yes')]
		#mode = simpleInput.processInput(II('test','Test Mode',II.DROPDOWN,options=options,default='no'))
		#testMode = False
		#if mode == 'yes': testMode = True

		#options = [('no','No'),('yes','Yes')]
		#mode = simpleInput.processInput(II('local','Local Mode',II.DROPDOWN,options=options,default='no'))
		#localMode = False
		#if mode == 'yes': localMode = True

		#self.simpleInput = simpleInput.getContent()

		#simpleProps = PropTableController(self.req,'Test Params')
		#simpleProps.addRow(TR('Overriden Now',now,TR.DATETIME))
		#simpleProps.addRow(TR('Test Mode',testMode,TR.TEXT))
		#simpleProps.addRow(TR('Local Mode',localMode,TR.TEXT))

		#self.simpleProps = simpleProps.getContent()

		#simpleTable = TableController(self.req,'times','Times',dbOrder=False)
		#simpleTable.addHeader(TH('item', 'Item Name',TH.TEXT))
		#simpleTable.addHeader(TH('time', 'Time (sec)',TH.FLOAT,sorted=True,sum=True))

		#self.t = l = []
		#totTime = 0.0;
		#allAlerts = []
		#for key,item in _uri2Controller.items():
			#if item.navItem and item.controller and issubclass(item.controller,StatmonController):
				#start = time.time()
				#p = {}
				#controller = item.controller(self.req,createContent=False)
				#controller.now = now
				#controller._testAlerts = testMode
				#if localMode:
					#controller.preCreate()
					#controller.createContent()
					#controller.postCreate()

				#p['item'] = item.navTitle

				#if localMode:
					#p['alert'] = controller.alertTable
				#else:
					## Create Alerts
					#alerts =controller.getAlerts()
					#allAlerts += alerts
					#alertTable = AlertController(self.req,alerts=alerts)
					#p['alert'] = alertTable.getContent()

				#end = time.time()
				#p['time'] = end-start
				#totTime += p['time']

				#simpleTable.addRow(**p)
				#l.append(p)

		#if not localMode:
			#p = {}
			#p['item'] = 'All Combined'
			#p['time'] = totTime
			#alertTable = AlertController(self.req,alerts=allAlerts)
			#p['alert'] = alertTable.getContent()
			#l.insert(0,p)

		#self.simpleTable = simpleTable.getContent()

#registerController(TestAlerts, 'tests/alerts',navItem=False)
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
