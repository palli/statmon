
from statmonControllers import OfflineStatmonController

class HelpController(OfflineStatmonController):
	_title = 'Online Guide'
	_filename = 'help/index.html'
	def createContent(self): pass

class AboutController(OfflineStatmonController):
	_title = 'About'
	_filename = 'psp/helpAbout.psp'
	def createContent(self): pass

class TestController(OfflineStatmonController):
	_filename = 'psp/selftest.psp'

	def createContent(self):
		self.tests = []
		
		# RRDTool
		name = 'rrdtool'
		filename = os.popen('which rrdtool').read().strip()
		if os.path.exists(filename):
			status = True
		else:
			status = False
		detail = filename
		self.tests.append( SelfTest(name,status,detail) )
		
		# MySQL Connection
		name = "MySQL connection"
		try:
			count,result = model.db.query("show tables")
			status = True
			detail = result
		except Exception, e:
			status = False
			detail = e.val
		self.tests.append( SelfTest(name,status,detail))
		
		# TSM Database connection
		name = "TSM Database connection"
		try:
			tsm = datasource.TSMDatasource()
			result = tsm.query("select node_name from nodes")
			status = True
			detail = result
		except Exception, strerror:
			status = False
			detail = strerror
		self.tests.append( SelfTest(name,status,detail))
		
		# See if grapher works:
		name = "RRDTool based grapher"
		try:
			db = datasource.MySQLDataSource()
			rest = {
				'domainfilter' : '*',
				'nodefilter' : '*',
				'nodelist' : ['DARKSTAR.BASIS.IS'],
				'domainlist' : None,
				'node' : 'DARKSTAR.BASIS.IS',
				'path' : '',
				'datapath' : 'data/',
				'imagepath' : 'images/',
				'db' : db,
				'update' : False,
				'graph' : True,
				'maxage' : 1,
				#'imagewidth' : 1000,
				#'imageheight' : 300,
				'graphstart' : '-6w',
				#'graphend' : '-1d',
			}
			g = grapher.NodeCount(**rest)
			status = True
			detail = ''

		except Exception, e:
			status = False
			detail = e
		self.tests.append( SelfTest(name,status,detail))
	def testeval(self,obj):
		obj = eval('self.'+obj)
		return escape(str(obj))
