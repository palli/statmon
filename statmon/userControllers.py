
from statmonControllers import StatmonController
from core.tableControllers import TableController,TH

import core.utils

import model
import grapher

import datetime

class NodeListController(StatmonController):
	_title = 'Nodes'
	_filename = 'psp/userNodelist.psp'

	def createContent(self):
		user = self.getSessionValue('user')
		nodelist=model.getStatmonACL(user,'node_name')
		emptyMessage='''No active viewable nodes selected for user `%s' found matching: %s<br/>
			Please contact the site administrator for assistance with full details of the task you are trying to carry out.''' % (user,', '.join(nodelist))
		if not nodelist:
			emptyMessage='''No viewable nodes selected for user `%s'.<br/>
			Please contact the site administrator for assistance with full details of the task you are trying to carry out.''' % user

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes',emptyMessage=emptyMessage)
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		nodeTable.addHeader(TH('node_version', 'Version',TH.NUMBER,sum=False))
		nodeTable.addHeader(TH('fs_min_backup_end', 'Last Time Every Filespace on Node was Successfully Backed up',TH.DATETIME,abbr='Last Complete Backup'))
		#nodeTable.addHeader(TH('fs_max_backup_end', 'Most Recent Time any Single Filespace on Node was Successfully Backed up',TH.DATETIME,abbr='Most Recent Backup'))
		#nodeTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		#nodeTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		nodeTable.addHeader(TH('logical_total', 'Total Backup + Total Archive',TH.BYTES,dbOrder=False,abbr='Total Storage'))


		nodes = model.getNodes(
			nodelist=nodelist,
			orderby=nodeTable.getOrderBy()
		)
		for i in nodes:
			if not i.platform_name: i['platform_name'] = 'Unknown'
			i['logical_total'] = i.logical_bytes_arch+i.logical_bytes_bkup
			nodeTable.addRow(**i)

class GraphsController(StatmonController):
	_title = 'Graphs'
	_filename = 'psp/userGraphs.psp'
	_selectedNodes = None
	def createContent(self):
		start, end = self.getStartEnd('graphstart','graphend')

		params = self.params
		user = self.getSessionValue('user')
		
		params['nodelist'] = model.getStatmonACL(user,'node_name')
		params['domainfilter'] = '*'
		params['graphstart'] = start
		params['graphend'] = end

		self.params['imagewidth'] = '411' # ca 41em

		self.graphNodeCount = grapher.NodeCount(**params)
		self.graphDailyRestore = grapher.DailyRestore(**params)
		self.graphDailyBackup = grapher.DailyBackup(**params)
		self.graphTotalArchive = grapher.TotalArchive(**params)
		self.graphTotalBackup = grapher.TotalBackup(**params)
		self.graphTransferSpeed = grapher.TransferBackupSpeed(**params)
		self.graphSessionDuration = grapher.SessionBackupDuration(**params)
		self.graphSessionCount = grapher.SessionBackupCount(**params)

class BackupStatusController(StatmonController):
	_title = 'Backup Status'
	_filename = 'psp/userBackupStatus.psp'

	def createContent(self):
		self.days = [] # List container for all days recorded
		self.hosts = [] # List of all hosts recorded

		start, end = self.getStartEnd('historystart','endyesterday')

		schedules = model.getBackupHistory(start)
		schedules.sort(key=lambda x: x['nodename'])
		hosts = core.utils.DefaultDict( [] )

		# We need to reformat start to a datetime object.
		self.day = day = datetime.timedelta(days=1)

		user = self.getSessionValue('user')
		nodelist=model.getStatmonACL(user,'node_name')

		nodes = model.getNodes(
			nodelist=nodelist
		)

		self.nodeMap = {}
		for i in nodes:
			self.nodeMap[i.node_name] = i
		i = start
		last_success = {}
		while i <= end:
			self.days.append(i)
			i = i + day
		for i in schedules:
			if not self.nodeMap.has_key(i.nodename): continue
			hosts[i.nodename].append( i )
		for host, records in hosts.iteritems():
			self.hosts.append(host)
			log = core.utils.DefaultDict( 'U' )
			for i in records:
				if i['msgno'] == 2507:
					ls = max( self.parseDate(i['date_time']), last_success.get(host,None))
					last_success[host] = ls
					if log[ self.parseDate( i['date_time'] ) ] == 'N':
						i['successful'] = 'N'
					else:
						i['successful'] = 'Y'
				elif i['msgno'] == 2579:
					i['successful'] = 'N'
				elif i['msgno'] == 2578:
					i['successful'] = 'M'
				else:
					i['successful'] = 'U'
				log[ self.parseDate( i['date_time'] ) ] = i['successful']
			i = start
			while i < end:
				log[ self.parseDate(i)] = log[ self.parseDate(i)]
				i = i + day
			hosts[host] = log
		self.hostMap = hosts
		self.hosts.sort(key=lambda x: last_success.get(x,None) )
		self.last_success = last_success
		self.days.sort()


	def getClassValue(self,host,date):
		records = self.hostMap[host]
		value = records[ self.parseDate(date) ]
		classes = []
		if   value == 'Y': classes.append('schedule_success')
		elif value == 'N': classes.append('schedule_failed')
		elif value == 'M': classes.append('schedule_missed')
		elif value == 'U': classes.append('schedule_none')
		
		strReg = self.parseDate(self.nodeMap[host].reg_time)
		strDate = self.parseDate(date)

		if strDate == strReg:
			classes.append('new_reg')
		elif strDate < strReg:
			classes.append('non_reg')

		return ' '.join(classes)

	def getWeekday(self, date):
		return core.utils.dayOfWeek(date).lower()

	def getMonth(self, date):
		number = date
		months = [ 'offset', 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov', 'Dec']
		return months[number]

	def linkActlog(self,nodefilter=None,message=None,start=None,end=None,title=''):
		querystring = '<span class="gant_link"></span>'
		return querystring

