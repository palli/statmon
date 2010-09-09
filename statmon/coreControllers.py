
from core.tableControllers import TableController,TH,PropTableController,TR
from core.inputControllers import II
from core.utils import BytesToText,DefaultDict,getPluralMap,getDeltaString
from core import utils

import model
import grapher
from statmonControllers import StatmonController

from urllib import urlencode
from cgi import escape
from math import log10

import datetime
import time
import re
import copy
import os

class NodeListController(StatmonController):
	_title = 'Domains & Nodes'
	_filename = 'psp/nodelist.psp'
	_selectedDomains = None
	_selectedNodes = None
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])
		#start, end = self.getStartEnd('graphstart','graphend')

		#params = self.params
		#params['domainfilter'] = domainfilter
		#params['nodefilter'] = nodefilter
		#params['graphstart'] = start
		#params['graphend'] = end
		#params['imagewidth'] = '409' # ca 41 em

		# TODO: ehrm.. something
		contacts = map( lambda x: (x['contact'],'%s (%d)' % (x['contact'],x['count'])), model.getAnzaContacts() )
		contactfilter = self.processInput(II('contact','Contact',II.DROPDOWN,options=contacts,allowBlank=True,blankVal=''))
		
		reflects = self.processInput(II('reflects','Domain List Reflects Omitted Nodes',II.DROPDOWN,options=[('','Yes'),('no','No')],allowBlank=True))
		selected = True
		if reflects:
			selected = False

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes',emptyMessage='No Matching Nodes Found')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('server_name', 'Server',TH.TEXT))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		nodeTable.addHeader(TH('node_version', 'Version',TH.NUMBER,sum=False))
		nodeTable.addHeader(TH('fs_min_backup_end', 'Last Time Every Filespace on Node was Successfully Backed up',TH.DATETIME,abbr='Last Complete Backup'))
		nodeTable.addHeader(TH('fs_max_backup_end', 'Most Recent Time any Single Filespace on Node was Successfully Backed up',TH.DATETIME,abbr='Most Recent Backup'))
		nodeTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		nodeTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		nodeTable.addHeader(TH('logical_total', 'Total Backup + Total Archive',TH.BYTES,dbOrder=False,abbr='Total Storage'))

		self._selectedNodes = nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			contactfilter=contactfilter,
			orderby=nodeTable.getOrderBy()
		)
		nodeCount = {}
		nodeBkup = {}
		nodeArch = {}
		for i in nodes:
			nodeCount[i.domain_name] = nodeCount.get(i.domain_name,0)+1
			nodeBkup[i.domain_name] = nodeBkup.get(i.domain_name,0)+i.logical_bytes_bkup
			nodeArch[i.domain_name] = nodeArch.get(i.domain_name,0)+i.logical_bytes_arch
			i['rowclass'] = i.domain_name
			if not i.platform_name: i['platform_name'] = 'Unknown'
			i['logical_total'] = i.logical_bytes_arch+i.logical_bytes_bkup
			nodeTable.addRow(**i)

		reflect = ''
		if selected and nodefilter!='%':
			reflect = ' (Reflecting Nodes List Below)'

		jsScript = '''<input class="checkbox" type="checkbox" name="master_checkbox" checked="checked" onchange="SetAllCheckBoxes('domain_form', 'checkbox', this.checked);"/>'''
		self.domainTable = domainTable = TableController(self.req,'domains','Domains',emptyMessage='No Matching Domains Found')
		#domainTable.addHeader(TH('show_hide', jsScript,TH.HTML,sortable=False,escapeName=False))
		domainTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain,sorted=True))
		domainTable.addHeader(TH('defmgmtclass','Default Management Class',TH.TEXT,abbr='DEFMGMT'))

		if selected:
			domainTable.addHeader(TH('num_shown', 'Number of Matching Nodes'+reflect,TH.NUMBER,dbOrder=False,abbr='Shown'))
			domainTable.addHeader(TH('num_hidden', 'Number of Omitted Nodes'+reflect,TH.NUMBER,dbOrder=False,abbr='Hidden'))
			#domainTable.addHeader(TH('num_nodes', 'Total Number of Nodes',TH.NUMBER,abbr='Total'))
		else:
			domainTable.addHeader(TH('num_nodes', 'Number of Nodes',TH.NUMBER,abbr='Nodes'))

		domainTable.addHeader(TH('logical_bytes_bkup', 'Total Backup'+reflect,TH.BYTES,dbOrder=(not selected),abbr='TB'))
		domainTable.addHeader(TH('logical_bytes_arch', 'Total Archive'+reflect,TH.BYTES,dbOrder=(not selected),abbr='TA'))
		domainTable.addHeader(TH('logical_total', 'Total Storage = Total Archive + Total Backup'+reflect,TH.BYTES,dbOrder=False,abbr='TS'))

		self._selectedDomains = domains = model.getDomains(
			domainfilter=domainfilter,
			orderby=domainTable.getOrderBy()
		)
		rest = {}
		for i in domains:
			i['show_hide'] = '''<input class="checkbox" name="checkbox" type="checkbox" checked="checked" onchange="showToggle('nodes_body', '%s', this.checked)"/>''' % ( i.domain_name )

			if selected:
				i['num_shown'] = nodeCount.get(i.domain_name,0)
				i['num_hidden'] = i['num_nodes']-nodeCount.get(i.domain_name,0)
				i['logical_bytes_bkup'] = nodeBkup.get(i.domain_name,0)
				i['logical_bytes_arch'] = nodeArch.get(i.domain_name,0)
			i['logical_total'] = i['logical_bytes_bkup']+i['logical_bytes_arch']
			domainTable.addRow( **i )

		self.addMessage('<a href="#">%s node(s)</a> on <a href="#">%s domain(s)</a> shown'% ( len( nodes ), len( nodeCount ) ))
		
		if selected:
			self.addMessage('Domain list reflects displayed nodes')
		else:
			self.addMessage('Domain list does not reflects displayed nodes')

		#self.domainNodeCount = grapher.DomainNodeCount(**params)

		self.splitAlerts = 2

	def createAlerts(self,local=False):
		nodes = self._selectedNodes
		domains = self._selectedDomains
		if nodes == None or domains == None:
			nodes = model.getNodes()
			domains = model.getDomains()

		# Alert if some nodes have not backed up in some time
		oldNodes = []
		for i in nodes:
			if not i.fs_min_backup_end:
				i.fs_min_backup_end = datetime.datetime(1970,1,1)
			diff = self.now - i.fs_min_backup_end
			if diff > datetime.timedelta(days=2):
				oldNodes.append( i )

		self.addAlert( oldNodes,'W', 'Last Backup is more than 2 day(s) old on %s nodes' % len( oldNodes ) )

		# Check if any nodes exist with registered domains that do not exist
		domainList = map(lambda x: x.domain_name, domains)
		for i in nodes:
			self.addAlert( i.domain_name not in domainList, 'E', 'Node %s has nonexistent domain %s' % ( i.node_name, i.domain_name ) )

class StoragePoolsController(StatmonController):
	_title = 'Storage Pools'
	_filename = 'psp/storagePools.psp'
	def createContent(self):
		stgpoollist = []

		stgpoolfilter = self.processInput(self.standardInputs['stgpool'])
		start, end = self.getStartEnd('graphstart','graphend')

		params = self.params
		params['stgpoolfilter'] = stgpoolfilter
		params['stgpoollist'] = stgpoollist
		params['graphstart'] = start
		params['graphend'] = end
		params['imagewidth'] = '409' # ca 41 em

		self.spTable = spTable = TableController(self.req,'storagepools','Storage Pools')
		spTable.addHeader(TH('stgpool_name', 'Node Name',TH.TEXT,self.linkStoragePool,sorted=True))
		spTable.addHeader(TH('est_capacity_bytes', 'Estimated Capacity',TH.BYTES))
		spTable.addHeader(TH('est_used_bytes', 'Estimated Used',TH.BYTES))
		spTable.addHeader(TH('est_useable_bytes', 'Estimated Usable',TH.BYTES))
		spTable.addHeader(TH('est_reclaimable_bytes', 'Estimated Reclaimable',TH.BYTES))
		spTable.addHeader(TH('description', 'Description',TH.TEXT))

		storagepools = model.getStoragepools(
			stgpoolfilter=stgpoolfilter,
			stgpoollist=stgpoollist,
			orderby=spTable.getOrderBy())
		
		for i in storagepools:
			spTable.addRow(**i)

		self.graphStoragePoolUsage = grapher.StoragePoolUsage(**params)
		self.graphStoragePoolUtilization = grapher.StorageAggregatedUtilization(**params)

class StoragePoolController(StatmonController):
	_filename = 'psp/storagePool.psp'
	_title = None
	def createContent(self):
		poolname = self.getField('poolname')
		try:
			pool = model.getStoragepool(poolname)[0]	
		except:
			self.storagepoolInfoTable = ''
			self.volumeInfoTable = ''
			self.nodeTable = ''
			return

		self._title = 'View Pool'

		self.storagepoolInfoTable = storagepoolInfoTable = PropTableController(self.req,'Storagepool Information')
		storagepoolInfoTable.addRow(TR('Pool Name',pool.stgpool_name,TR.TEXT,None,self.linkStoragePool))
		storagepoolInfoTable.addRow(TR('Storage Type',pool.pooltype,TR.TEXT))
		storagepoolInfoTable.addRow(TR('Device Class',pool.devclass,TR.TEXT))
		storagepoolInfoTable.addRow(TR('Description',pool.description,TR.TEXT))
		storagepoolInfoTable.addRow(TR('Access',pool.access,TR.TEXT))
		storagepoolInfoTable.addRow(TR('Next Pool',pool.nextstgpool,TR.TEXT))
		storagepoolInfoTable.addRow(TR('Estimated Size',pool.est_capacity_bytes,TR.BYTES))
		storagepoolInfoTable.addRow(TR('Total Amount Used',pool.est_used_bytes,TR.BYTES))
		storagepoolInfoTable.addRow(TR('Total Usable Amount',pool.est_useable_bytes,TR.BYTES))

		self.volumeInfoTable = volumeInfoTable = PropTableController(self.req,'Volume Information')
		volumeInfoTable.addRow(TR('Volumes Filling',pool.filling,TR.NUMBER))
		volumeInfoTable.addRow(TR('Volumes Full',pool.full,TR.NUMBER))
		volumeInfoTable.addRow(TR('Volumes Unavailable',pool.unavailable,TR.NUMBER))
		volumeInfoTable.addRow(TR('Volumes Read-only',pool.readonly,TR.NUMBER))
		volumeInfoTable.addRow(TR('Volumes Empty',pool.empty,TR.NUMBER))
		volumeInfoTable.addRow(TR('Total Volumes',pool.volumes,TR.NUMBER))

		self.params['stgpoollist'] = [pool.stgpool_name]
		
		self.params['imagewidth'] = "581" # ca 55 em
		self.params['imageheight'] = '89' # ca 12.8em+1.2 = 15 ?

		self.graphStoragePoolUsage = grapher.StoragePoolUsage(**self.params)

		self.params['imagewidth'] = "243" # ca 27 em

		self.params['imageheight'] = '110'
		self.graphStorageUtilization = grapher.StorageUtilization(**self.params)
		self.params['imageheight'] = '72'
		self.graphVolumeCount = grapher.VolumeCount(**self.params)
		self.graphs = True

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes using this Pool')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('num_files', 'Files',TH.NUMBER,dbOrder=False))
		nodeTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		nodeTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		nodeTable.addHeader(TH('logical_total', 'Total Storage',TH.BYTES,dbOrder=False,sorted=True))

		# Get all nodes that store data on this pool
		occupancy = model.getOccupancy(stgpool=pool.stgpool_name,orderby=nodeTable.getOrderBy())

		for i in occupancy:
			i['num_files'] = i.num_files_bkup + i.num_files_arch
			i['logical_total'] = i.logical_bytes_bkup + i.logical_bytes_arch
			nodeTable.addRow(**i)

	#def getTitle(self):
		#return self._title % self.poolname

class GraphsController(StatmonController):
	_title = 'Graphs'
	_filename = 'psp/graphs.psp'
	_selectedNodes = None
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])
		start, end = self.getStartEnd('graphstart','graphend')

		params = self.params
		params['domainfilter'] = domainfilter
		params['nodefilter'] = nodefilter
		params['graphstart'] = start
		params['graphend'] = end

		self.addDebug('Start Date: %s' % start.date() )
		self.addDebug('End Date: %s' % end.date() )

		self._selectedNodes = nodes = model.getNodes(nodefilter=nodefilter,domainfilter=domainfilter)

		self.nodeTable = nodeTable = TableController(self.req,'graphNodes','Graph Nodes')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		for node in nodes: nodeTable.addRow(**node)

		self.params['imagewidth'] = '411' # ca 41em

		self.graphNodeCount = grapher.NodeCount(**params)
		self.graphDailyRestore = grapher.DailyRestore(**params)
		self.graphDailyBackup = grapher.DailyBackup(**params)
		self.graphTotalArchive = grapher.TotalArchive(**params)
		self.graphTotalBackup = grapher.TotalBackup(**params)
		self.graphTransferSpeed = grapher.TransferBackupSpeed(**params)
		self.graphSessionDuration = grapher.SessionBackupDuration(**params)
		self.graphSessionCount = grapher.SessionBackupCount(**params)

		#self.graphSessionReclamationDuration = grapher.SessionReclamationDuration(**params)
		#self.graphSessionExpirationDuration = grapher.SessionExpirationDuration(**params)

		#self.graphTransferReclamationSpeed = grapher.TransferReclamationSpeed(**params)
		#self.graphTransferExpirationSpeed = grapher.TransferExpirationSpeed(**params)

		self.splitAlerts = 2

	def createAlerts(self,local=False):
		if self._selectedNodes and local:
			self.addMessage('''<a href="" onclick="toggleClass('content','overflow-auto');toggleDisplay('graphnodes');return false;">%d node(s)</a> form the following graphs''' % len( self._selectedNodes ) )

class DomainController(StatmonController):
	#_title = 'Find Domain'
	_title = None
	_filename = 'psp/domain.psp'
	def createContent(self):
		domain_name = self.getField('domain')
		try:
			domain = model.getDomain(domain_name)[0]
		except:
			self.domainInfoTable = ''
			self.schedulesTable = ''
			self.noScheduleTable = ''
			self.graphsBox = ''
			return

		self._title = 'Viewing %s Domain' % escape(domain.domain_name)
		self._navTitle = 'View Domain'

		params = self.params
		params['domainlist'] = [domain.domain_name]
		params['nodefilter'] = '*'

		#Domain information
		self.domainInfoTable = domainInfoTable = PropTableController(self.req,'Domain Information')
		domainInfoTable.addRow(TR('Domain Name',domain.domain_name,TR.TEXT,None,self.linkDomain))
		domainInfoTable.addRow(TR('Number of Nodes',domain.num_nodes,TR.NUMBER))
		domainInfoTable.addRow(TR('Last Active',domain.set_last_activated,TR.TEXT))
		domainInfoTable.addRow(TR('Description',domain.description,TR.TEXT))
		domainInfoTable.addRow(TR('Profile',domain.profile,TR.TEXT))
		domainInfoTable.addRow(TR('Last Change Date',domain.chg_time,TR.DATE))
		domainInfoTable.addRow(TR('Last Change Admin',domain.chg_admin ,TR.TEXT))
		domainInfoTable.addRow(TR('Default Management Class',domain.defmgmtclass,TR.TEXT))
		domainInfoTable.addRow(TR('Total Amount in Backup',domain.logical_bytes_bkup,TR.BYTES))
		domainInfoTable.addRow(TR('Total Amount in Archive',domain.logical_bytes_arch,TR.BYTES))


		self.graphsBox = graphs = GraphsController(self.req)
		# TODO: merge function for this and existing input box?
		# TODO: merge function for this and existing alerts?
		self._alerts += graphs._alerts
		graphs.alertTable = ''

		# Schedule information
		self.schedulesTable = schedulesTable = TableController(self.req,'schedules','Nodes and Schedules')
		schedulesTable.addHeader(TH('schedule_name', 'Schedule Name',TH.TEXT,self.linkSchedule,sorted=True))
		schedulesTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		schedulesTable.addHeader(TH('chg_admin', 'Change Admin',TH.TEXT))
		schedulesTable.addHeader(TH('chg_time', 'Change Time',TH.DATE))
		# TODO: remove +', node_name' (used to sort secondary by node_name for more pretty inital list)
		schedules = model.getAssociations(domain_name=domain.domain_name,orderby=schedulesTable.getOrderBy()+', node_name')
		scheduledNodes = []
		for i in schedules:
			i['schedule_name'] = (i['schedule_name'],i['domain_name'])
			schedulesTable.addRow(**i)
			scheduledNodes.append(i['node_name'])
		
		self.noScheduleTable = noScheduleTable = TableController(self.req,'nodes','Nodes without Schedules')
		noScheduleTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		noScheduleTable.addHeader(TH('reg_admin', 'Registering Admin',TH.TEXT))
		noScheduleTable.addHeader(TH('reg_date', 'Registion Date',TH.DATE))
		noScheduleTable.addHeader(TH('fs_min_backup_end','Last Time Every Filespace on Node was Successfully Backed up',TR.DATETIME,abbr='Last Complete Backup'))

		nodes = model.getNodes(domainfilter=domain.domain_name,orderby=noScheduleTable.getOrderBy())
		for i in nodes:
			if i['node_name'] not in scheduledNodes:
				noScheduleTable.addRow(**i)

	#def getTitle(self):
		#return self._title % self.domain_name

# TODO: rename me!?
class SnapshotController(StatmonController):
	_title = 'Statmon Information'
	_navTitle = 'Information'
	_filename = 'psp/snapshots.psp'
	_selectedSnapshots = None
	def createContent(self):
		start, end = self.getStartEnd('graphstart','graphend')

		self.snapTable = snapTable = TableController(self.req,'snaps','Latest Snapshots',dbOrder=False)
		snapTable.addHeader(TH('snap_id', 'Snap ID',TH.NUMBER,sorted=True,sum=False))
		snapTable.addHeader(TH('version', 'Collector version',TH.NUMBER,sum=False))
		snapTable.addHeader(TH('start_date', 'Started',TH.DATETIME))
		snapTable.addHeader(TH('end_date', 'Finished',TH.DATETIME,dbOrder=False))
		snapTable.addHeader(TH('runtime', 'Runtime',TH.TIME))
		snapTable.addHeader(TH('completed', 'Completed',TH.NUMBER))

		self._selectedSnapshots = snapshots = model.getSnapshots(orderby='snap_id desc limit 15')

		for i in snapshots:
			if not i.end_date:
				i['end_date'] = self.now
			i['runtime'] = i.end_date - i.start_date
			snapTable.addRow(**i)

		local_db = model.getLocalDB()
		local_db.reverse()
		#orderby='snap_id desc', limit=2

		from __init__ import __version__
		statmonVersion = __version__
		try: collectorVersion = snapshots[0].version
		except: collectorVersion = 'Unknown'

		try: DBSize = local_db[0].size
		except: DBSize = None

		try: collectionDate = snapshots[0].end_date
		except: collectionDate = None

		try: collectionSize = local_db[0].size - local_db[1].size
		except: collectionSize = None
		
		try: collectionTime = snapshots[0].end_date-snapshots[0].start_date
		except: collectionTime = None

		try:
			if snapshots[0].completed == 1: collectionStatus = 'Successful'
			else: collectionStatus = 'Unsuccessful'
		except: collectionStatus = 'Never Collected' # no snapshot / never collected

		self.snapshotInfoTable = snapshotInfoTable = PropTableController(self.req,'Snapshot Information')
		snapshotInfoTable.addRow(TR('Statmon Version',statmonVersion,TR.NUMBER))
		snapshotInfoTable.addRow(TR('Collector Version',collectorVersion,TR.NUMBER))

		snapshotInfoTable.addRow(TR('Local DB Size',DBSize,TR.BYTES))
		snapshotInfoTable.addRow(TR('Last Collection',collectionDate,TR.DATE))
		snapshotInfoTable.addRow(TR('Last Collection Size',collectionSize,TR.BYTES))
		snapshotInfoTable.addRow(TR('Last Collection Duration',collectionTime,TR.TIME))
		snapshotInfoTable.addRow(TR('Last Collection Status',collectionStatus,TR.TEXT))

		#First collection
		#Average Runtime

		# Graph with Local database size
		#self.params['imagewidth'] = "291" # ca 31 em
		self.params['imagewidth'] = "242" # ca 27 em
		self.params['imageheight'] = '77' # ca 12.8em ?
		self.params['graphstart'] = start
		self.params['graphend'] = end
		self.graphLocalDatabaseSize = grapher.LocalDatabaseSize(**self.params)
		self.graphCollectorVersion = grapher.CollectorVersion(**self.params)
		
		self.addDebug('TODO: Add Some boring info here for more content')
		self.addDebug('TODO: Add Some boring info here for more content')
		self.splitAlerts = 2

	def createAlerts(self,local=False):
		snapshots = self._selectedSnapshots
		if snapshots == None:
			snapshots = model.getSnapshots(orderby='snap_id desc limit 1')

		# Check if last collection is to old
		
		try: snapshot = snapshots[0]
		except: snapshot = None
		
		# TODO: read from config
		collectionAgeWarningValue = datetime.timedelta(days=2)
		collectionTooOld = snapshot and collectionAgeWarningValue and snapshot.end_date and (self.now - snapshot.end_date) > collectionAgeWarningValue
		self.addAlert(collectionTooOld,'E','Last collection is more than two days old')
		self.addAlert(not snapshot,'E','No Snapshot info found?! Run collector?!')

class FilespacesController(StatmonController):
	_title = 'Filespaces'
	_filename = 'psp/filespaces.psp'
	_selectedFilespaces = None

	def configureTests(self):
		# TODO: read from config
		self.alertFSFillingPercent = 95.0
		self.alertFSFullPercent = 99.0
		self.alertFSNeverBackedUp = True
		self.alertFSOldBackup = datetime.timedelta(days=2)

	def testAlertFSFilling(self,filespace):
		if self.testAlertFSFull(filespace): return False # prevent overlap
		if not self.alertFSFillingPercent: return False # check disabled
		if not filespace.pct_util: return None # unknown
		return self.alertFSFillingPercent < float(filespace.pct_util)

	def testAlertFSFull(self,filespace):
		if not self.alertFSFullPercent: return False # check disabled
		if not filespace.pct_util: return None # unknown
		return self.alertFSFullPercent < float(filespace.pct_util)

	def testAlertFSNeverBackedUp(self,filespace):
		if not self.alertFSNeverBackedUp: return False # check disabled
		return not filespace.backup_end

	def testAlertFSOldBackup(self,filespace):
		if not self.alertFSNeverBackedUp: return False # check disabled
		if not filespace.backup_end: return None # unknown
		fsDelta = self.today - filespace.backup_end
		return self.alertFSOldBackup < fsDelta

	def createContent(self):
		domainlist = []
		nodelist = []

		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])

		start, end = self.getStartEnd('graphstart','graphend')

		sort = DefaultDict(False)
		sort[self.getField('defaultSort','node_name')] = True

		self.filespaceTable = filespaceTable = TableController(self.req,'filespaces','Filespaces')
		filespaceTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=sort['node_name']))
		filespaceTable.addHeader(TH('filespace_name','Filespace Name',TH.TEXT))
		filespaceTable.addHeader(TH('filespace_type', 'FS Type',TH.TEXT))
		filespaceTable.addHeader(TH('backup_end', 'Last Backup',TH.DATE,sorted=sort['backup_end']))
		filespaceTable.addHeader(TH('capacity_bytes', 'Capacity',TH.BYTES))
		filespaceTable.addHeader(TH('used_bytes', 'Used',TH.BYTES))
		filespaceTable.addHeader(TH('free_bytes', 'Free',TH.BYTES,dbOrder=False))
		filespaceTable.addHeader(TH('pct_util', '%',TH.FLOAT,sorted=sort['pct_util']))
		filespaceTable.addHeader(TH('logical_total', 'Total Backup + Total Archive',TH.BYTES,dbOrder=False,abbr='In Storage'))

		filespaces = model.getFilespaces(nodefilter=nodefilter,domainfilter=domainfilter,orderby=filespaceTable.getOrderBy())

		conditional = self.getField('conditional',False)

		self._selectedFilespaces = []
		for i in filespaces:
			if conditional:
				self.configureTests()

				if self.getField('neverBacked',False) and not self.testAlertFSNeverBackedUp( i ): continue
				if self.getField('oldBackup',False) and not self.testAlertFSOldBackup( i ): continue
				if self.getField('fillingFilespaces',False) and not self.testAlertFSFilling( i ): continue
				if self.getField('fullFilespaces',False) and not self.testAlertFSFull( i ): continue

			i['free_bytes'] = i['capacity_bytes']-i['used_bytes']
			i['logical_total'] = i.logical_bytes_bkup+i.logical_bytes_arch
			filespaceTable.addRow(**i)
			self._selectedFilespaces.append(i)

		# Graph
		params = self.params
		params['domainfilter'] = domainfilter
		params['domainlist'] = domainlist
		params['nodefilter'] = nodefilter
		params['nodelist'] = nodelist
		params['graphstart'] = start
		params['graphend'] = end
		params['imagewidth'] = '410' # ca 41em
		self.graphFilespace = grapher.FilespacesAggregated(**params)

		#self.addMessage('<a href="#">%s filespaces</a> on <a href="#">%s nodes</a> shown'% ( len( filespaces ), len(nodes) ))

	def createAlerts(self,local=False):
		filespaces = self._selectedFilespaces
		if filespaces == None:
			filespaces = model.getFilespaces()

		self.configureTests()

		oldBackup = []
		neverBacked = []
		fillingFilespaces = []
		fullFilespaces = []
		for i in filespaces:
			# Check if filespace has nevered been backuped
			if self.testAlertFSNeverBackedUp( i ): neverBacked.append( i )
			# Check if filespace backup is old
			if self.testAlertFSOldBackup( i ): oldBackup.append( i )
			# Check if filespace is almost full
			if self.testAlertFSFilling( i ): fillingFilespaces.append( i )
			# Check if filespace is 'full'
			if self.testAlertFSFull( i ): fullFilespaces.append( i )

		fields = self.getAllFields()
		fields['conditional']='1'

		fields['defaultSort']='backup_end'
		p = getPluralMap(neverBacked)
		v = '<span class="varible">%s</span>' % len( neverBacked )
		c = '<span class="condition">never</span>'
		l = '%s?%s' % ( self.getControllerURI(self.__class__), urlencode(fields) )
		if not fields.has_key('neverBacked'): l += '&neverBacked=1'
		s = '<a href="%s">%s filespace%s</a> %s %s been backed up' % (escape(l),v, p['s'], p['have'], c)
		self.addAlert(neverBacked,message=s,severity='W',priority=59999-len(neverBacked))

		fields['defaultSort']='backup_end'
		p = getPluralMap(oldBackup)
		v = '<span class="varible">%s</span>' % len( oldBackup )
		c = '<span class="condition">%s</span>' % getDeltaString(self.alertFSOldBackup)
		l = '%s?%s' % ( self.getControllerURI(self.__class__), urlencode(fields) )
		if not fields.has_key('oldBackup'): l += '&oldBackup=1'
		s = '<a href="%s">%s filespace%s</a> %s not been backed up for more than %s' % (escape(l), v, p['s'], p['have'], c)
		self.addAlert(oldBackup,message=s,severity='W',priority=59999-len(oldBackup))

		fields['defaultSort']='pct_util'
		p = getPluralMap(fillingFilespaces)
		v = '<span class="varible">%s</span>' % len( fillingFilespaces )
		c = '<span class="condition">%2.1f%%</span>' % self.alertFSFillingPercent
		l = '%s?%s' % ( self.getControllerURI(self.__class__), urlencode(fields) )
		if not fields.has_key('fillingFilespaces'): l += '&fillingFilespaces=1'
		s = '<a href="%s">%s filespace%s</a> %s more than %s full'% (escape(l), v, p['s'], p['are'], c )
		self.addAlert(fillingFilespaces,message=s,severity='W',priority=99999-len(fillingFilespaces))

		fields['defaultSort']='pct_util'
		p = getPluralMap(fullFilespaces)
		v = '<span class="varible">%s</span>' % len( fullFilespaces )
		c = '<span class="condition">%2.1f%%</span>' % self.alertFSFullPercent
		l = '%s?%s' % ( self.getControllerURI(self.__class__), urlencode(fields) )
		if not fields.has_key('fullFilespaces'): l += '&fullFilespaces=1'
		s = '<a href="%s">%s filespace%s</a> %s more than %s full' % (escape(l), v, p['s'], p['are'], c)
		self.addAlert(fullFilespaces,message=s,severity='E',priority=99999-len(fullFilespaces))

class BackupStatusController(StatmonController):
	_title = 'Backup Status'
	_filename = 'psp/backupStatus.psp'
	_selectedSchedules = None
	_hiddenNodes = None
	def createContent(self):
		self.days = [] # List container for all days recorded
		self.hosts = [] # List of all hosts recorded

		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])

		start, end = self.getStartEnd('historystart','endyesterday')

		self._selectedSchedules = schedules = model.getBackupHistory(start)
		schedules.sort(key=lambda x: x['nodename'])
		hosts = DefaultDict( [] )

		# We need to reformat start to a datetime object.
		self.day = day = datetime.timedelta(days=1)

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Search Results')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('reg_time','Registerion Date',TR.DATE))
		nodeTable.addHeader(TH('fs_min_backup_end','Last Time Every Filespace on Node was Successfully Backed up',TR.DATETIME,abbr='Last Complete Backup',sortDesc=False,sorted=True))

		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			orderby=nodeTable.getOrderBy()
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
			log = DefaultDict( 'U' )
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
		self.__schedules = hosts
		self.hosts.sort(key=lambda x: last_success.get(x,None) )
		self.last_success = last_success
		self.days.sort()

		# Finally, lets see which nodes did NOT make a backup
		assert( self._hiddenNodes == None)
		self._hiddenNodes = []
		for node in nodes:
			if not hosts.has_key(node.node_name):
				nodeTable.addRow( **node )
				self._hiddenNodes.append( node )

	def getClassValue(self,host,date):
		records = self.__schedules[host]
		value = records[ self.parseDate(date)]
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
		return utils.dayOfWeek(date).lower()

	def getMonth(self, date):
		number = date
		months = [ 'offset', 'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov', 'Dec']
		return months[number]

	def createAlerts(self,local=False):
		schedules = self._selectedSchedules
		interval = 'given interval'
		if schedules == None:
			schedules = model.getBackupHistory(start=self.yesterday)
			interval = 'last 24 hours'


		if self._hiddenNodes and local:
			self.addMessage('''<a href="" onclick="toggleClass('content','overflow-auto');toggleDisplay('omittednodes');return false;">%d node(s)</a> did not have a scheduled backup during this period''' % len( self._hiddenNodes ) )

		if schedules:
			# Number of failed schedules
			successful = []
			failedSchedules = []
			missedSchedules = []
			other = []
			for i in schedules:
				if i['msgno'] == 2507:
					successful.append(i)
				elif i['msgno'] == 2579:
					failedSchedules.append(i)
				elif i['msgno'] == 2578:
					missedSchedules.append(i)
				else:
					other.append(i)
	
			self.addAlert(failedSchedules,'W','%d failed backup schedules in the %s (%3.2f%%)' %
				(len(failedSchedules), interval,100.0*len(failedSchedules)/len(schedules)))
			self.addAlert(missedSchedules,'E','%d missed backup schedules in the %s (%3.2f%%)' %
				(len(missedSchedules), interval,100.0*len(missedSchedules)/len(schedules)))
			self.addAlert(successful,'I','%s successful backup schedules in the %s (%3.2f%%)' %
				(len(successful), interval,100.0*len(successful)/len(schedules)))
			self.addAlert(other,'D','%s unclassified backup schedules in the %s?! (%3.2f%%)' %
				(len(other), interval,100.0*len(other)/len(schedules)))


class NodeController(StatmonController):
	_title = ''
	_filename = 'psp/node.psp'
	def createContent(self):
		self.foundNodes = ''
		self.nodeInfoTable = ''
		self.nodeInfoTable = ''
		self.schedulesTable = ''
		self.filespaceTable = ''
		self.fsUsedList = []
		self.fsStorageList = []

		domainfilter = self.processInput(self.standardInputs['domain'])
		node_name = self.processInput(self.standardInputs['findnode'])
		start, end = self.getStartEnd('graphstart','graphend')
		
		if model.hasStatmonACL():
			user = self.getSessionValue('user')
			if not node_name in model.getStatmonACL(user,'node_name'):
				return self.getControllerByURI(notFound=False,overrideFound=False,forbidden=True)

		nodeTable = TableController(self.req,'nodes','Search Results')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))

		nodes = model.getNodes(
			nodefilter=self.autoWilds(node_name),
			domainfilter=domainfilter,
			orderby=nodeTable.getOrderBy()
		)
		node = None
		if len(nodes) == 1:
			node = nodes[0]
		else:
			for i in nodes:
				if i.node_name.upper() == node_name.upper():
					node = i
					break
				nodeTable.addRow(**i)
		if not node or not node.node_name.upper() == node_name.upper():
			# make input box reflect what was actually searched for
			self.updateInput('node',newval=self.autoWilds(node_name))
		if not node:
			if len(nodes):
				self._title = '%d Matching Nodes Found' % len(nodes)
				#self._navTitle = '%d Matches' % len(nodes)
				self.foundNodes = nodeTable
				self.addAlert(True,'W','Multiple matches found. Please select one or try again with more extact conditions')
			else:
				self._title = 'No Matching Nodes Found'
				#self._navTitle = 'No Match'
				self.addAlert(True,'W','Please input valid node name')
			return

		self._title = 'Viewing %s Node' % escape(node.node_name)
		self._navTitle = 'View Node'
		#self.updateInput('node',newval=node.node_name)

		params = self.params
		params['node'] = node.node_name
		params['nodelist'] = [node.node_name]
		params['domainfilter'] = '*'

		params['imagewidth'] = '410' # ca 41em
		params['graphstart'] = start
		params['graphend'] = end

		maxSessions = self.processInput(II('max','Max Sessions',II.NUMBER,default=7,allowBlank=False))
		self.sessionsTable = sessionsTable = SessionsController( self.req,parent=self,entityfilter=node.node_name,
			maxSessions=maxSessions,merge=True )
		self._alerts += sessionsTable._alerts
		sessionsTable.alertTable = ''
		sessionsTable.tableTitle = 'Recent Session for Node'

		# Graphs
		self.graphSessionSuccessRate = grapher.SessionSuccessRate(**params)
		self.graphFilespacesStorage = grapher.FilespacesStorage(**params)
		self.graphDailyRestore = grapher.DailyRestore(**params)
		self.graphDailyBackup = grapher.DailyBackup(**params)
		self.graphTotalArchive = grapher.TotalArchive(**params)
		self.graphTotalBackup = grapher.TotalBackup(**params)
		self.graphTransferSpeed = grapher.TransferBackupSpeed(**params)
		self.graphSessionDuration = grapher.SessionBackupDuration(**params)
		self.graphSessionCount = grapher.SessionBackupCount(**params)
		self.graphs = True

		# Information about this node
		self.nodeInfoTable = nodeInfoTable = PropTableController(self.req,'Node Information')
		nodeInfoTable.addRow(TR('Domain',node.domain_name,TR.TEXT,None,self.linkDomain))
		nodeInfoTable.addRow(TR('Platform',node.platform_name,TR.TEXT))
		nodeInfoTable.addRow(TR('Last Time Every Filespace on Node was Successfully Backed up',node.fs_min_backup_end,TR.DATETIME,abbr='Last Complete Backup'))
		#nodeInfoTable.addRow(TR('Last Time when at Least one Filespace on Node was Successfully Backed up',node.fs_max_backup_end,TR.DATETIME,abbr='Last Partial Backup'))

		nodeInfoTable.addRow(TR('Contact',node.contact,TR.TEXT))
		nodeInfoTable.addRow(TR('URL',node.url,TR.TEXT))
		nodeInfoTable.addRow(TR('Registerion Date',node.reg_time,TR.DATE))
		nodeInfoTable.addRow(TR('Registering Admin',node.reg_admin,TR.TEXT))
		nodeInfoTable.addRow(TR('Host Address',node.tcp_name,TR.TEXT))
		nodeInfoTable.addRow(TR('Host IP',node.tcp_address,TR.TEXT))
		nodeInfoTable.addRow(TR('Total Amount in Backup', (node.logical_bytes_bkup,self.graphTotalBackup), TR.BYTES,None,self.linkGraph))
		nodeInfoTable.addRow(TR('Total Amount in Archive', (node.logical_bytes_arch,self.graphTotalArchive), TR.BYTES,None,self.linkGraph))
		nodeInfoTable.addRow(TR('Total Amount in Storage', (node.logical_bytes_bkup+node.logical_bytes_arch,self.graphFilespacesStorage), TR.BYTES,None,self.linkGraph))

		# Schedule information
		self.schedulesTable = schedulesTable = TableController(self.req,'schedules','Schedules for Node',emptyMessage='No Schedules Configured for Node')
		schedulesTable.addHeader(TH('schedule_name', 'Schedule Name',TH.TEXT,self.linkSchedule,sorted=True))
		schedulesTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT))
		schedulesTable.addHeader(TH('start_time', 'Start Time',TH.TEXT))
		schedulesTable.addHeader(TH('chg_admin', 'Change Admin',TH.TEXT))
		schedulesTable.addHeader(TH('chg_time', 'Change Time',TH.DATE))
		schedules = model.getAssociations(node_name=node.node_name,orderby=schedulesTable.getOrderBy())
		for i in schedules:
			i['schedule_name'] = (i['schedule_name'],i['domain_name'])
			schedulesTable.addRow(**i)

		# Filespace and filespace graphs
		self.filespaceTable = filespaceTable = TableController(self.req,'filespaces','Filespaces on Node')
		filespaceTable.addHeader(TH('filespace_name','Filespace Name',TH.TEXT))
		filespaceTable.addHeader(TH('filespace_type', 'Filesystem Type',TH.TEXT,abbr='Type'))
		filespaceTable.addHeader(TH('backup_end', 'Last Successful Backup',TH.DATE,abbr='Last Backup'))
		filespaceTable.addHeader(TH('capacity_bytes', 'Local Filespace Capacity',TH.BYTES,self.linkGraph,abbr='Capacity'))
		filespaceTable.addHeader(TH('used_bytes', 'Used Locally',TH.BYTES,self.linkGraph,abbr='Used'))
		filespaceTable.addHeader(TH('logical_total', 'Total Backup + Total Archive',TH.BYTES,self.linkGraph,dbOrder=False,sorted=True,abbr='In Storage'))

		filespaces = model.getFilespaces(node.node_name,orderby=filespaceTable.getOrderBy())

		self.fsUsedList = []
		self.fsStorageList = []
		for i in filespaces:
			params['fsid'] = int(i.filespace_id)
			params['imageheight'] = "75"
			#params['imagewidth'] = "150"
			params['imagewidth'] = '158' # ca 20em
			params['title'] = i.filespace_name
			if len(params['title']) > 32:
				params['title'] = i.filespace_name[0:32] + ' ...'

			if not i.virtual_fs:
				graph = grapher.FilespacesAggregated(**params)
				i['capacity_bytes'] = (i.capacity_bytes,graph)
				i['used_bytes'] = (i.used_bytes,graph)
				self.fsUsedList.append( graph )

			graph = grapher.FilespacesAggregatedStorage(**params)
			self.fsStorageList.append( graph )

			i['logical_total'] = (i.logical_bytes_bkup+i.logical_bytes_arch, graph)
			filespaceTable.addRow(**i)
			
			self.addAlert(not i.backup_end,'W','''Filespace `%s' has never been backed up''' % escape(i.filespace_name))
			if i.backup_end: 
				backold = self.now - i.backup_end > datetime.timedelta(days=2)
				self.addAlert(backold,'W','''Last Backup of `%s' more than 2 day(s) old on''' % escape(i.filespace_name))
			fsfull = float(i.pct_util) > 99.0
			self.addAlert(fsfull,'E','''Filespace `%s' is more than 99%% full''' % escape(i.filespace_name))
			fsfilling = float(i.pct_util) > 95.0
			self.addAlert(fsfilling,'W','''Filespace `%s' is more than 95%% full''' % escape(i.filespace_name))

		self._splitAlerts = 2

	#def getTitle(self,active=False):
		##if active:
			##node_name = self.getField('node')
			##if node_name:
				##return self._title + ': ' + escape(node_name)
		#return self._title

class StorageAbusersController(StatmonController):
	_title = 'Storage Abusers'
	_filename = 'psp/storageAbusers.psp'
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Storage Abusers')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		#nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		#nodeTable.addHeader(TH('node_version', 'Client Version',TH.NUMBER,sum=False))
		#nodeTable.addHeader(TH('fs_min_backup_end', 'Last Complete Backup',TH.DATETIME))
		nodeTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		nodeTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		nodeTable.addHeader(TH('logical_total', 'Total Storage',TH.BYTES,dbOrder=False))
		nodeTable.addHeader(TH('fs_used_bytes', 'FS Used',TH.BYTES))
		nodeTable.addHeader(TH('fs_ratio', 'Ratio',TH.FLOAT,dbOrder=False))
		nodeTable.addHeader(TH('hog_factor', 'Hog Factor',TH.FLOAT,dbOrder=False,sorted=True))

		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			orderby=nodeTable.getOrderBy()
		)
		for i in nodes:
			hogFactor = 0.0
			fsRatio = 0.0
			if i.fs_used_bytes and i.logical_bytes_bkup+i.logical_bytes_arch:
				storage = float(i.logical_bytes_bkup+i.logical_bytes_arch)
				fsused = float(i.fs_used_bytes)
				hogFactor = (log10(storage/1024/1024/1024)**3)*storage/fsused
				fsRatio = storage/fsused
			i['fs_ratio'] = fsRatio
			i['hog_factor'] = hogFactor
			i['logical_total'] = i.logical_bytes_arch+i.logical_bytes_bkup
			nodeTable.addRow(**i)

class NewNodesController(StatmonController):
	_title = 'New Nodes'
	_navTitle = 'New Nodes'
	_filename = 'psp/newNodes.psp'
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])
		since = self.processInput(self.standardInputs['historystart'])
		self._title = 'New Nodes since %s' % since.strftime('%Y-%m-%d')

		self.nodeTable = nodeTable = TableController(self.req,'nodes',self._title,emptyMessage='''No New Nodes - Try different `since' condition?''')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		nodeTable.addHeader(TH('tcp_name', 'Host Name',TH.TEXT))
		nodeTable.addHeader(TH('tcp_address', 'IP Address',TH.TEXT))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('reg_admin', 'Registing Admin',TH.TEXT))
		nodeTable.addHeader(TH('reg_time', 'Registion Date',TH.DATE,sorted=True,sortDesc=True))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		nodeTable.addHeader(TH('node_version', 'Client Version',TH.NUMBER,sum=False))
		nodeTable.addHeader(TH('fs_min_backup_end', 'Last Complete Backup',TH.DATETIME))

		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			orderby=nodeTable.getOrderBy()
		)
		for i in nodes:
			if not i.reg_time or i.reg_time >= since:
				nodeTable.addRow(**i)

class OverviewController(StatmonController):
	_title = 'Overview'
	_filename = 'psp/overview.psp'
	def createContent(self):
		start, end = self.getStartEnd('graphstart','graphend')

		# Platform Info+Storage abusers
		# optional query (result size) optimize
		fields = {
			'node_name':'node_name',
			'platform_name':'platform_name',
			'logical_total':'logical_bytes_bkup+logical_bytes_arch',
		}
		self.nodes = nodes = model.getNodes(orderby='logical_bytes_bkup+logical_bytes_arch desc',fields=fields)

		# Begin Platform Info
		self.osTable = osTable = TableController(self.req,'os','Nodes By Platform',dbOrder=False)
		osTable.addHeader(TH('platform_name', 'Platform',TH.TEXT))
		osTable.addHeader(TH('node_count', 'Count',TH.NUMBER,sorted=True))
		osMap = DefaultDict(DefaultDict(0))
		for i in nodes:
			if not i['platform_name']: i['platform_name'] = 'Unknown'
			osMap[i['platform_name']]['platform_name'] = i['platform_name']
			osMap[i['platform_name']]['node_count']  += 1
		osItems = osMap.items()
		osItems.sort(key=lambda x: x[1],reverse=True)
		for os,count in osItems[5:]:
			osMap[None]['platform_name'] = 'Other' 
			osMap[None]['node_count'] += osMap.pop(os)['node_count']
		keys = osMap.keys()
		keys.sort()
		for key in keys:
			osTable.addRow(**osMap[key])
		# End Platform Info

		# Begin Storage Abusers
		numOsTable = len(osMap.keys())
		self.abuseTable = abuseTable = TableController(self.req,'abuse','Top Storage Users',dbOrder=False)
		abuseTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sortable=False))
		abuseTable.addHeader(TH('logical_total', 'Total Backup + Total Archive',TH.BYTES, sorted=True,abbr='In Storage'))
		for i in nodes[:numOsTable]:
			#i['logical_total'] = i.logical_bytes_bkup+i.logical_bytes_arch
			i['node_name'] = (i['node_name'],22)
			abuseTable.addRow(**i)
		# End Storage Abusers

		# Begin Server Informations
		status = None
		try: status = model.getStatus()[0]
		except: pass

		server_name = 'Unknown'
		version = 'Unknown'
		ipaddr = 'Unknown'
		availability = 'Unknown'
		scheduler = 'Unknown'
		licensecompliance = 'Unknown'

		if status:
			server_name = status.server_name
			version = '%s.%s.%s.%s'%  (
				status.server_version,
				status.server_release,
				status.server_level,
				status.server_sublevel)
			ipaddr = status.server_hla
			availability = status.availability.title()
			scheduler = status.scheduler.title()
			licensecompliance = status.licensecompliance.title()

		self.serverInfoTable = serverInfoTable = PropTableController(self.req,'Server Information')
		serverInfoTable.addRow(TR('Server Name',server_name,TR.TEXT))
		serverInfoTable.addRow(TR('Version',version,TR.TEXT))
		serverInfoTable.addRow(TR('Hostname',ipaddr,TR.TEXT))
		serverInfoTable.addRow(TR('Availability',availability,TR.TEXT))
		serverInfoTable.addRow(TR('Central Scheduler',scheduler,TR.TEXT))
		#Server License Compliance
		serverInfoTable.addRow(TR('Server License',licensecompliance,TR.NUMBER))

		# End Server Informations

		# Begin Last 24 hours stuff ...
		summary = model.getSummary(start_time=self.yesterday,start_end_time=self.today)
		numSessions = len ( summary )
		numBackup = 0
		numAffected = numExamined = numFailed = 0
		numBytesTransfered = 0
		for i in summary:
			if i.activity == 'BACKUP':
				numBackup += 1
				numAffected  += max(i.affected,0)
				numExamined += max(i.examined,0)
				numFailed += max(i.failed,0)
				numBytesTransfered += max(i.bytes,0)
		self.last24InfoTable = last24InfoTable = PropTableController(self.req,'Yesterday Backup Sessions')
		last24InfoTable.addRow(TR('Number of Sessions',numBackup,TR.NUMBER))
		#last24InfoTable.addRow(TR('Number of Sessions',numSessions,TR.NUMBER))
		last24InfoTable.addRow(TR('Examined Objects',numExamined,TR.NUMBER))
		last24InfoTable.addRow(TR('Affected Objects',numAffected,TR.NUMBER))
		last24InfoTable.addRow(TR('Failed Objects',numFailed,TR.NUMBER))
		last24InfoTable.addRow(TR('Bytes Transfered',numBytesTransfered,TR.BYTES))
		# End Last 24 hours stuff ...

		# Graphs
		self.params['nodefilter'] = self.params['domainfilter'] = '*'
		#self.params['imagewidth'] = '411' # ca 41em
		self.params['imagewidth'] = '158' # ca 20em
		self.params['imageheight'] = '95'
		self.params['graphstart'] = start
		self.params['graphend'] = end
		self.graphDailyBackup = grapher.DailyBackup(**self.params)
		self.graphTotalBackup = grapher.TotalBackupSimple(**self.params)
		self.graphTSMLogSize = grapher.TSMLogSize(**self.params)
		self.graphTSMDatabaseSize = grapher.TSMDatabaseSize(**self.params)
		
		#self.addDebug('now: %s' % self.now)
		#self.addDebug('today: %s' % self.today)
		#self.addDebug('yesterday: %s' % self.yesterday)
		#self.addDebug('weekago: %s' % self.weekago)
		
		self._splitAlerts = 2

	def createAlerts(self,local=False):
		if local:
			for item in self.getRegisteredControllers():
				if item.navItem and item.controller and issubclass(item.controller,StatmonController):
					controller = item.controller(self.req,createContent=False)
					self._alerts += controller.getAlerts()
		else:
			# Here comes a list of alerts
			# TODO: Check if all alerts should be refactored somewhere else..?
	
			domains = model.getDomains()
			status = model.getBackupHistory(start=self.yesterday)

			# Last DB Backup
			try: log = model.getLog()[0]
			except: log = None

			try: db = model.getDb()[0]
			except: db = None

			# TODO: read from config
			dbAgeWarningValue = datetime.timedelta(days=2)
			dbBackupTooOld = db and (self.now - db.last_backup_date) > dbAgeWarningValue
			self.addAlert(dbBackupTooOld,'W','Last TSM DB Backup is more than %s old' % str(dbAgeWarningValue).split(',')[0])
			self.addAlert(not db,'E','Failed to read TSM DB info?!')

			# TODO: read from config
			logWarnValue = 90.0
			logFilling = log and logWarnValue and float(log.pct_utilized) > logWarnValue
			self.addAlert(logFilling,'W','TSM Log is more than %d%% full' % logWarnValue)
			self.addAlert(not log,'E','Failed to read TSM log info?!')

			# Check if any occupancy exist on storagepools that do not exist
			stgpools = model.getAlertStoragepools()
			self.addAlert(stgpools,'D','getAlertStoragepools')
			for i in stgpools:
				self.addAlert(stgpools,'E','Storagepool %s is not found in stgpools'%stgpools[0])

class FailedFilesController(StatmonController):
	_title = 'Failed Files'
	_filename = 'psp/failedFiles.psp'
	_selectedFailedfiles = None
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])
		start = self.processInput(self.standardInputs['startyesterday'])
		#end = self.processInput(self.standardInputs['end'])

		self._selectedFailedfiles = actlog = model.getFailedFiles( start )

		sub = {}
		self.titles = {}
		sub[4005] = r'''ANE4005E Error processing \\*'(.*)\\*': file not found.*'''
		sub[4987] = r'''ANE4987E Error processing \\*'(.*)\\*': the object is in use by another process.*'''
		sub[4037] = r'''ANE4037E File \\*'(.*)\\*' changed during processing.*'''
		self.titles[4005] = 'File not found'
		self.titles[4987] = 'Open File'
		self.titles[4037] = 'File Changed during Processing'
		self.entries = DefaultDict([])
		self.myNodes = model.getNodes(domainfilter=domainfilter,nodefilter=nodefilter)
		self.myNodes = map(lambda x: x.node_name, self.myNodes)
		self.nodes = []
		for i in actlog:
			if not i['nodename'] in self.myNodes:
				continue
			if not i['nodename'] in self.nodes:
				self.nodes.append( i['nodename'] )
			i['filename'] = re.sub( sub[i['msgno']], r'\1', i['message'])
			self.entries[i['nodename']].append(i)
		self.order = []
		for node,items in self.entries.items():
			self.order.append((-len(items),node))
		self.order.sort()

	def createAlerts(self,local=False):
		interval = 'given interval'
		failedFiles = 0
		if self._selectedFailedfiles == None:
			failedFiles = model.getFailedFiles(start_date=self.yesterday,countOnly=True)
			interval = 'last 24 hours'
		else:
			failedFiles = len(self._selectedFailedfiles)

		# Number of failed files
		if failedFiles:
			alert = {}
			alert['severity'] = 'I'
			alert['message'] = '%s failed files in the %s' % (failedFiles,interval)
			self._alerts.append( alert )


class ZoomController(StatmonController):
	_filename = 'psp/zoom.psp'
	def createContent(self):
		from statmonControllers import decodeGraph, encodeGraph
		from grapher import fromRRDTime

		self.addHiddenValue('p',self.getField('p'))
		Grapher,params = decodeGraph(self.getField('p'))

		graphstart = fromRRDTime(params.get('graphstart',self.graphStart))
		graphend = fromRRDTime(params.get('graphend',self.graphEnd))

		start, end = self.getStartEnd(
			II('start','Start Date',II.DATE,default=graphstart,blankVal=graphstart),
			II('end','End Date',II.DATE,default=graphend,blankVal=graphend) )

		params['graphstart'] = start
		params['graphend'] = end

		params['imageheight'] = self.processInput( II('height','Height',II.NUMBER,default=200) )
		params['imagewidth'] = self.processInput( II('width','Width',II.NUMBER,default=700) )

		options=[('','PNG'),('SVG','SVG'),('EPS','EPS'),('PDF','PDF')]
		format = self.processInput(II('type','Format',II.DROPDOWN,options=options,allowBlank=True,default='PNG',blankVal='PNG'))
		params['format'] = format

		self.inputHidden = False

		if Grapher:
			self.theGraph = Grapher(**params)
		else:
			self.theGraph = None

class ActlogController(StatmonController):
	_title = 'Activity Log'
	_filename = 'psp/actlog.psp'
	def createContent(self):
		msgno = self.processInput(self.standardInputs['msgno'])
		node = self.processInput(self.standardInputs['node'])
		if node == self.standardInputs['node'].blankVal: node = None
		mes = self.processInput(self.standardInputs['msgcon'])

		start, end = self.getStartEnd('startyesterday','endtoday')
		
		cutLength = self.processInput(II('length','Message Cut-Off',II.NUMBER,default=70,allowBlank=True,blankVal=0))

		self.actlogTable = actlogTable = TableController(self.req,'actlog','Activity Log')
		actlogTable.addHeader(TH('severity', 'Severity',TH.HTML,spanContent=True))
		actlogTable.addHeader(TH('date_time', 'Time',TH.DATETIME,sorted=True))
		actlogTable.addHeader(TH('msgno', 'Msg ID',TH.NUMBER,sum=False))
		actlogTable.addHeader(TH('nodename', 'Node Name',TH.TEXT,self.linkNode))
		actlogTable.addHeader(TH('domainname', 'Domain Name',TH.TEXT,self.linkDomain))
		actlogTable.addHeader(TH('message', 'Message',TH.TEXT))

		count = model.getActlog(message=mes,msgno=msgno,
			nodefilter=node,start=start,end=end,countOnly=True)
		self.addMessage('%d of %d matching entries' % (min(count,1000),count))

		actlog = model.getActlog(message=mes,msgno=msgno,
			nodefilter=node,start=start,end=end,
			orderby=actlogTable.getOrderBy(),messageCutLength=cutLength)
		for i in actlog:
			self.parseSeverity( i )
			actlogTable.addRow(**i )

	def parseSeverity(self,record):
		# sortable
		date = record.get('date_time',record.get('newest_date_time',self.now)).isoformat()
		rowclass = 'unclassified'
		priority = '00'
		if record['severity'] == 'E':
			rowclass = 'error'
			priority = '01'
		elif record['severity'] == 'I':
			rowclass = 'info'
			priority = '03'
		elif record['severity'] == 'W':
			rowclass = 'warning'
			priority = '02'
		elif record['severity'] == 'D':
			rowclass = 'debug'
			priority = '04'

		record['rowclass'] = rowclass
		record['severity'] = '<span>&nbsp;<!--%s-%s--></span>' % (priority,date)

class ActlogStatsController(ActlogController):
	_title = 'Statistics'
	_filename = 'psp/actlogStats.psp'
	def createContent(self):
		cutLength = self.processInput(II('length','Message Cut-Off',II.NUMBER,default=70,allowBlank=True,blankVal=0))

		# This is for the box that shows actlog records
		# Along with msgno by count
		self.actlogStatTable = actlogStatTable = TableController(self.req,'actlogStats','Activity Log Stats')
		actlogStatTable.addHeader(TH('severity', 'Severity',TH.HTML))
		actlogStatTable.addHeader(TH('msgno', 'Message Type ID',TH.NUMBER,sum=False,abbr='ID'))
		actlogStatTable.addHeader(TH('msg_count', 'Total Count',TH.NUMBER,abbr='T. Count'))
		actlogStatTable.addHeader(TH('msg_size', 'Total Messages Size',TH.BYTES,abbr='T. Size'))
		actlogStatTable.addHeader(TH('count_last24', 'Number of Message of this Type the Last 24 Hours',TH.NUMBER,sorted=True,abbr='24. Count'))
		actlogStatTable.addHeader(TH('size_last24', 'Total Size of Message of this Type the Last 24 Hours Size',TH.BYTES,abbr='24. Size'))
		actlogStatTable.addHeader(TH('newest_date_time', 'Most Recent Message Date',TH.DATETIME,abbr='Most Recent Date'))
		actlogStatTable.addHeader(TH('newest_message', 'Most Recent Message',TH.TEXT))

		totalEntries = 0
		last24Entries = 0
		actlogCount = model.getActlogCount(orderby=actlogStatTable.getOrderBy(),messageCutLength=cutLength)
		for i in actlogCount:
			self.parseSeverity( i )
			actlogStatTable.addRow( **i )
			totalEntries += i['msg_count']
			last24Entries += i['count_last24']

		self.addMessage('''%d entries in actlog (%d last 24 hours)'''  % (totalEntries,last24Entries) )
		#self.graphActlogGraph = grapher.ActlogGraph(**self.params)

class ClientSchedulesController(StatmonController):
	_title = 'Client Schedules'
	_filename = 'psp/clientSchedules.psp'
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])
		schedulefilter = self.processInput(self.standardInputs['schedule'])

		# Get all nodes that have no associations
		# TODO: let DB handle this?
		associations = model.getAssociations()
		nodes_with_associations = []
		node_count = DefaultDict(0)
		for i in associations:
			nodes_with_associations.append( i.node_name )
			node_count[i.schedule_name] += 1
		###

		self.csTable = csTable = TableController(self.req,'client_sche','Schedules')
		csTable.addHeader(TH('schedule_name', 'Schedule Name',TH.TEXT,self.linkSchedule,sorted=True))
		csTable.addHeader(TH('domain_name','Domain Name',TH.TEXT,self.linkDomain))
		csTable.addHeader(TH('node_count','Nodes',TH.NUMBER,sum=False,dbOrder=False))
		csTable.addHeader(TH('chg_admin', 'Admin',TH.TEXT))
		csTable.addHeader(TH('startdate', 'Start Date',TH.DATE))
		csTable.addHeader(TH('starttime', 'Start Time',TH.TIME))
		csTable.addHeader(TH('action', 'Action',TH.TEXT))
		#csTable.addHeader(TH('description', 'Description',TH.TEXT))
		csTable.addHeader(TH('duration_durunits', 'Duration',TH.NUMBER,dbOrder=False,sum=False))
		csTable.addHeader(TH('period_perunits', 'Period',TH.NUMBER,dbOrder=False,sum=False))
		csTable.addHeader(TH('priority', 'Priority',TH.NUMBER,sum=False))
		csTable.addHeader(TH('dayofweek', 'Day of Week',TH.TEXT))
		
		# Get all schedules:
		client_schedules = model.getClientSchedules(
				schedulefilter=schedulefilter,
				domainfilter=domainfilter,
				orderby=csTable.getOrderBy()
				)

		for i in client_schedules:
			if i.duration != None: i['duration_durunits'] = '%d %s' % (i.duration, i.durunits)
			if i.period != None: i['period_perunits'] = '%d %s' % (i.period, i.perunits)
			i['node_count'] = node_count[i.schedule_name]
			if not i.period: i['period_perunits'] = i.perunits
			i['schedule_name'] = (i['schedule_name'],i['domain_name'])
			csTable.addRow(**i)

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes without Schedules')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		nodeTable.addHeader(TH('node_version', 'Client Version',TH.NUMBER,sum=False))
		nodeTable.addHeader(TH('fs_min_backup_end', 'Last Time Every Filespace on Node was Successfully Backed up',TH.DATETIME,abbr='Last Complete Backup'))
		nodeTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		nodeTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		nodeTable.addHeader(TH('logical_total', 'Total Storage',TH.BYTES,dbOrder=False))
		
		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			orderby=nodeTable.getOrderBy()
		)


		for i in nodes:
			if i.node_name not in nodes_with_associations:
				if not i.platform_name: i['platform_name'] = 'Unknown'
				i['logical_total'] = i.logical_bytes_arch+i.logical_bytes_bkup
				nodeTable.addRow(**i)

class ClientScheduleController(StatmonController):
	#_title = 'Find/View Client Schedule'
	_title = None
	_filename = 'psp/clientSchedule.psp'
	def createContent(self):
		self.foundSchedules = ''
		self.scheduleInfoTable = ''
		self.sessionsTable = ''
		self.nodeTable = ''



		domain_name = self.getField('domain','')
		domainfilter = self.processInput(self.standardInputs['domain'])
		schedule_name = self.processInput(self.standardInputs['findschedule'])

		nodefilter = self.processInput(self.standardInputs['node'])

		start, end = self.getStartEnd('graphstart','graphend')

		params = self.params
		params['domainfilter'] = domainfilter
		params['nodefilter'] = nodefilter
		params['schedulefilter'] = schedule_name
		params['graphstart'] = start
		params['graphend'] = end

		scheduleTable = TableController(self.req,'nodes','Search Results')
		scheduleTable.addHeader(TH('schedule_name', 'Schedule Name',TH.TEXT,self.linkSchedule,sorted=True))
		scheduleTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		scheduleTable.addHeader(TH('action', 'Action',TH.TEXT))

		schedules = model.getClientSchedules(
				schedulefilter=schedule_name,
				domainfilter=domainfilter,
				orderby=scheduleTable.getOrderBy()
		)
		schedule = None
		if len(schedules) == 1:
			schedule = schedules[0]
		for i in schedules:
			if i.schedule_name.upper() == schedule_name.upper() and i.domain_name.upper() == domain_name.upper():
				schedule = i
				break
			i['schedule_name'] = (i['schedule_name'],i['domain_name'])
			scheduleTable.addRow(**i)
			i['schedule_name'] = i['schedule_name'][0]
		if not schedule:
			self.addAlert(not schedules,'E','No Matching Schedule Found!')
			if not schedules:
				self._title = 'No Matching Schedule Found!'
				return
			self._title = '%d Matching Schedule Found' % len(schedules)
			self.foundSchedules = scheduleTable
			return

		self._title = 'Viewing %s Schedule' % escape(schedule.schedule_name)
		self._navTitle = 'View Schedule'

		# Pretty format
		duration = '%s %s' % (schedule.duration,schedule.durunits)
		period = '%s %s' % (schedule.period,schedule.perunits)

		self.scheduleInfoTable = scheduleInfoTable = PropTableController(self.req,'Schedule Information')
		scheduleInfoTable.addRow(TR('Schedule Name',(schedule.schedule_name,schedule.domain_name),TR.TEXT,None,self.linkSchedule))
		scheduleInfoTable.addRow(TR('Domain Name',schedule.domain_name,TR.TEXT,None,self.linkDomain))
		scheduleInfoTable.addRow(TR('Description',schedule.description,TR.TEXT))
		scheduleInfoTable.addRow(TR('Action',schedule.action,TR.TEXT))
		scheduleInfoTable.addRow(TR('Options',schedule.options,TR.TEXT))
		scheduleInfoTable.addRow(TR('Objects',schedule.objects,TR.TEXT))
		scheduleInfoTable.addRow(TR('Priority',schedule.priority,TR.NUMBER))
		scheduleInfoTable.addRow(TR('Start Date',schedule.startdate,TR.DATE))
		scheduleInfoTable.addRow(TR('Start TIME',schedule.starttime,TR.TIME))
		scheduleInfoTable.addRow(TR('Duration',duration,TR.TEXT))
		scheduleInfoTable.addRow(TR('Period',period,TR.TEXT))
		scheduleInfoTable.addRow(TR('Expiration',schedule.expiration,TR.TEXT))
		scheduleInfoTable.addRow(TR('Last Changed',schedule.chg_time,TR.DATETIME))
		scheduleInfoTable.addRow(TR('Changed by',schedule.chg_admin,TR.TEXT))
		scheduleInfoTable.addRow(TR('Profile',schedule.profile ,TR.TEXT))
		scheduleInfoTable.addRow(TR('Schedule style',schedule.sched_style,TR.TEXT))
		scheduleInfoTable.addRow(TR('Day of month',schedule.dayofmonth,TR.TEXT))
		scheduleInfoTable.addRow(TR('Week of month',schedule.weekofmonth,TR.TEXT))
		scheduleInfoTable.addRow(TR('Day of week',schedule.dayofweek,TR.TEXT))

		self.sessionsTable = sessionsTable = SessionsController( self.req, schedulefilter=schedule.schedule_name, domainfilter=schedule.domain_name,showSchedules=False )
		self._alerts += sessionsTable._alerts
		sessionsTable.alertTable = ''
		sessionsTable.tableTitle = 'Recent Session for Schedule'

		# Get all nodes that are using this schedule
		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes using this Schedule')
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		nodeTable.addHeader(TH('node_version', 'Client Version',TH.NUMBER,sum=False))
		#nodeTable.addHeader(TH('fs_min_backup_end', 'Last Time Every Filespace on Node was Successfully Backed up',TH.DATETIME,abbr='Last Complete Backup')) # does not relate to this schedule
		nodeTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		nodeTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		nodeTable.addHeader(TH('logical_total', 'Total Storage',TH.BYTES,dbOrder=False))
		
		nodes = model.getNodes( orderby=nodeTable.getOrderBy() )

		associations = model.getAssociations(schedule_name=schedule.schedule_name)
		associations = map(lambda x: x.node_name, associations)
		for i in nodes:
			if i.node_name in associations:
				if not i.platform_name: i['platform_name'] = 'Unknown'
				i['logical_total'] = i.logical_bytes_arch+i.logical_bytes_bkup
				nodeTable.addRow(**i)

		self.params['imagewidth'] = "242" # ca 27 em
		self.params['imageheight'] = '77'

		self.graphDailyBackup = grapher.DailyBackup(**params)
		self.graphTransferSpeed = grapher.TransferBackupSpeed(**params)
		self.graphSessionDuration = grapher.SessionBackupDuration(**params)
		self.graphSessionCount = grapher.SessionBackupCount(**params)

		self._splitAlerts = 2

	#def getTitle(self,active=False):
		#if active:
			#return self._navTitle
		#return None
		#return 'Find/View Client Schedule'
		#return self._title
		#return self._title % self.schedule_name

# TODO: inherit from common parent (this and summary)
class SessionsController(StatmonController):
	_title = 'Sessions'
	_filename = 'psp/sessions.psp'

	class Row:
		def __init__(self,entity='',activity='',theClass=''):
			self._entity = entity
			self._entityNote = {}
			self._activity = activity
			self._class = theClass
			self._records = []
			self._start_time = None
			self._link = lambda x: x
			self._expandable = False
			self._beginBody = False
			self._endBody = False
			self._total = ''
			self._schedule = ''
			self._domain = ''
			self._day = ''

		class Record:
			def __init__(self):
				self._entity = ''
				self._class = ''
				self._offset = 0
				self._duration = 0
				self._activity = None

	def __init__(self,req,createContent=True,parent=None,
		entityfilter=None,schedulefilter=None,domainfilter=None,showSchedules=True,maxSessions=None,merge=False):
		self.schedulefilter = schedulefilter
		self.domainfilter = domainfilter
		self.entityfilter = entityfilter
		self.showSchedules = showSchedules
		self.maxSessions = maxSessions
		self.merge = merge
		StatmonController.__init__(self,req,createContent=createContent,parent=parent)

	def createContent(self):
		entityfilter = self.processInput(II('entity','Entity',II.TEXT,allowBlank=True,blankVal=None))
		if self.entityfilter: entityfilter = self.entityfilter

		activity = None
		if not (self.entityfilter or self.schedulefilter):
			activities = map( lambda x: (x['activity'],x['activity']), model.getSummaryActivities() )
			activity = self.processInput(II('activity','Activity',II.DROPDOWN,options=activities,allowBlank=True,blankVal=None))

		schedulefilter = self.processInput(II('schedule','Schedule',II.TEXT,allowBlank=True,blankVal=None))
		if self.schedulefilter: schedulefilter = self.schedulefilter

		start, end = self.getStartEnd('startweekago','endtoday')

		if self.parent:
			start = self.parent.updateInput('start')
			end = self.parent.updateInput('end')

		maxSessions = self.processInput(II('max','Max Sessions',II.NUMBER,default=1000,allowBlank=False))
		if self.maxSessions: maxSessions = self.maxSessions

		self.tableTitle = 'Sessions'

		# quick and dirty hack
		nodes = model.getNodes()
		node2domain = {}
		entitylist = []
		for i in nodes:
			node2domain[i.node_name] = i.domain_name
			if self.domainfilter and self.domainfilter == i.domain_name:
				entitylist.append(i.node_name)
		if not self.domainfilter: entitylist = None

		cutOffRules = [
			('oldest','Oldest'),
			('shortest','Shortest'),
			('newest','Newest'),
			('longest','Longest'),]
		cutOffRule = self.processInput(II('cutrule','Cut-Off Rule',II.DROPDOWN,options=cutOffRules,default='oldest'))

		minDuration = self.processInput(II('duration','Min Duration (secs)',II.NUMBER,default=0,allowBlank=True))

		orderby='end_time desc'
		if cutOffRule == 'shortest':
			orderby='end_time-start_time desc'
		if cutOffRule == 'longest':
			orderby='end_time-start_time'
		elif cutOffRule == 'newest':
			orderby='start_time'

		summary = model.getSummary(
			end_start_time=start,
			start_end_time=end,
			entityfilter=entityfilter,
			entitylist=entitylist,
			activity=activity,
			schedulefilter=schedulefilter,
			minDuration=minDuration,
			orderby=orderby,
			limit=maxSessions
		)
		count = model.getSummary(
			end_start_time=start,
			start_end_time=end,
			entityfilter=entityfilter,
			entitylist=entitylist,
			schedulefilter=schedulefilter,
			activity=activity,
			minDuration=minDuration,
			countOnly=True
		)
		day = datetime.timedelta(days=1)
		yesterday = self.now-1*day
		today = start

		countAll = sum(map(lambda x:x.count_all,count))
		countDuration = sum(map(lambda x:x.count_duration,count))

		dailyCount = DefaultDict(0)
		totalCount = 0
		while count:
			day = count.pop(0)
			dailyCount[str(day.start_time.date())] += day.count_duration
			totalCount += day.count_duration
			sessionFake = copy.deepcopy(day)
			if day.start_time.date() < day.end_time.date():
				midnight = day.start_time.date()+datetime.timedelta(days=1)
				day.start_time = datetime.datetime(*midnight.timetuple()[:3])

				count.insert(0,day)

			sessionFake.entity = None
			summary.insert(0,sessionFake)

		#keys = dailyCount.keys()
		#keys.sort()
		#for key in keys:
			#self.addDebug('%s: %d' % (key,dailyCount[key]))

		if countAll-countDuration:
			self.addMessage('%d sessions omitted due to minimum session duration condition of %d seconds' % (countAll-countDuration,minDuration) )

		self.addAlert(countDuration > maxSessions,'W',
			'Only displaying %d of %d sessions' % (maxSessions,countDuration) )
		if countDuration > maxSessions:
			if summary:
				session = summary[0]
				skipped = (countDuration - maxSessions)
				delta = session.end_time-session.start_time
				message='Omitted %d session(s) ' % skipped
				if cutOffRule == 'shortest':
					message+='shorter than: %s' % delta
				if cutOffRule == 'longest':
					message+='longer than: %s' % delta
				elif cutOffRule == 'newest':
					message+='starting after: %s' % session.start_time
				else:
					message+='ending before: %s' % session.end_time
				self.addAlert( 1, 'W', message )

		#if maxSummaries and orginalLength>maxSummaries:
			#session = summary[-1]
			#self.addDebug('cut off at - entity: %s activity: %s start: %s end: %s duration: %s' % (session.entity,session.activity,session.start_time,session.end_time,session.end_time-session.start_time))
			#summary = summary[:-1]
		
		#self.addDebug('%d/%d sessions %d' % (len(summary),orginalLength,orginalLength2))
		summary.sort( key = lambda x: x.start_time )

 #title="<%= row.entity %> - <%= i.start_time %>"

		# debug
		#for i in range(min(len(summary),9999999)):
			#session = summary[i]
			#self.addDebug('num: %d entity: %s activity: %s start: %s end: %s' % \
				#(i, session.entity,session.activity,session.start_time,session.end_time))
		#self.merge = False

		# This code is write-once, read-never^H^H^H^Hrarely
		widthScale = 2000.0
		preStart = DefaultDict(0)
		postEnd = DefaultDict(0)
		overlapCount = DefaultDict(0)

		lastEntity = None
		lastActivity = None
		lastSchedule = None
		beginBody = False
		self.rows = []
		head = self.Row()
		row = self.Row()
		tail = self.Row('All Entities Aggregated','','all-session-aggregation')
		while summary:
			session = summary.pop(0)

			headTitle = 'Complete Aggregation for %s'
			headNote = None
			if session.start_time.date() < start.date():
				#if session.entity != None:
				preStart[session.start_time.date()] = dailyCount[str(session.start_time.date())]
				headNote = '1'
			if session.start_time.date() >= end.date():
				postEnd[session.start_time.date()] = dailyCount[str(session.start_time.date())]
				#if session.entity != None:
				headNote = '3'

			if not head._start_time or head._start_time != session.start_time.date():
				date = '%s' % session.start_time.date()
				#head._activity = '(%d)' % headCount
				#headCount = 0
				dayofweek = utils.dayOfWeek(session.start_time)
				head = self.Row('%s - %s' % (date,dayofweek),'',
					'daily-session-aggregation')
				head._day = dayofweek.lower()
				head._total = '/%d' % dailyCount[str(date)]

				beginBody = head._expandable = 'd%s' % date
				head._start_time = session.start_time.date()
				if headNote:
					head._entityNote[headNote] = headNote
				if not self.merge: self.rows.append(head)
				row._endBody = True

			if session.entity == None: continue

			record = self.Row.Record()

			# wrap around
			if session.start_time.date() < session.end_time.date():
				session._entityNote = '2'
				sessionNew = copy.deepcopy(session)
				midnight = session.start_time.date()+datetime.timedelta(days=1)
				session.end_time = datetime.datetime(*midnight.timetuple()[:3])
				sessionNew.start_time = datetime.datetime(*midnight.timetuple()[:3])
				overlapCount[session.start_time.date()] += 1

				insertPoint = 0
				for i in range(len(summary)):
					insertPoint = i
					if summary[i].start_time > sessionNew.start_time: break
					insertPoint += 1
				summary.insert(insertPoint,sessionNew)

			# debug
			#if session.entity[-1] == '*':
				#self.addDebug('entity: %s activity: %s start: %s end: %s' % \
				#(session.entity,session.activity,session.start_time,session.end_time))

			#record._width = 24*60*60/widthScale
			record._offset = (session.start_time - today).seconds/widthScale
			duration = session.end_time - session.start_time
			record._duration = duration.seconds/widthScale
			record._duration += 24*60*60*duration.days/widthScale

			activity = session.activity
			entity = session.entity
			schedule = max(session.schedule_name,'')
			#if session.schedule_name:

			# TODO: bug fix?! fix in db/collector instead?!
			if entity == """''""": entity = activity

			if session.activity == 'RECLAMATION':
				entity = ''.join(entity.split()[:1])

			if not summary or row._endBody or not lastEntity or lastEntity != entity or not lastActivity or lastActivity != activity or lastSchedule != schedule:
				row = self.Row(entity,activity,'session')
				row._schedule = schedule
				row._domain = node2domain.get(entity,'')
				if self.merge:
					row._entity = head._entity
					row._day = head._day
					for key in head._entityNote.keys():
						row._entityNote[key] = head._entityNote[key]
				self.rows.append(row)
				#headCount += 1
				lastEntity = entity
				lastActivity = activity
				lastSchedule = schedule

				row._beginBody = beginBody
				if beginBody: beginBody = False

			record._class = 'server-session'
			if activity in ('BACKUP','RESTORE','ARCHIVE'):
				if not self.merge: row._link = self.linkNode
				record._class = 'client-session'

			if record._duration < 0.0834:
				record._duration = 0.0834

			if record._duration > 0.0005:
				head._records.append(record)
				try: row._entityNote[session._entityNote] = session._entityNote
				except: pass
				row._records.append(record)
				tail._records.append(record)

		for row in self.rows:
			if row._expandable and not row._records:
				row._expandable = False
				row._activity = 'Empty'

		tail._activity = 'Total'
		tail._total = '/%d' % totalCount
		row._endBody = True
		self.rows.append(tail)

		dates = preStart.keys()
		dates.sort()
		for date in dates:
			self.addMessage('<span style="vertical-align: super;">1</span>: %s was added due to conditional overlapping session(s)' % (date) )

		if overlapCount:
			#% (sum(overlapCount.values()), len(overlapCount)
			self.addMessage('<span style="vertical-align: super;">2</span>: Session overlaps one or more day(s)' )

		dates = postEnd.keys()
		dates.sort()
		for date in dates:
			self.addMessage('<span style="vertical-align: super;">3</span>: %s was added due to conditional overlapping session(s)' % (date) )

		# calc ca max entity line length in EMs
		maxEntityLength = 0
		maxActivityLength = 0
		maxScheduleLength = 0
		for row in self.rows:
			maxEntityLength = max(maxEntityLength,len(row._entity))
			maxActivityLength = max(maxActivityLength,len(row._activity))
			maxScheduleLength = max(maxScheduleLength,len(row._schedule))
		self.maxEntityLength = maxEntityLength*0.55
		self.maxActivityLength = maxActivityLength*0.55
		self.maxScheduleLength = maxScheduleLength*0.55

		#if self.fill:
			#reminder = self.fill-(self.maxEntityLength+self.maxActivityLength+self.maxScheduleLength+24*3600/2000.0)

			#if self.showSchedules:
				#self.maxEntityLength += reminder/3.0
				#self.maxActivityLength += reminder/3.0
				#self.maxScheduleLength += reminder/3.0
			#else:
				#self.maxEntityLength += reminder/2.0
				#self.maxActivityLength += reminder/2.0
		
		self._splitAlerts = 2

	# TODO: fix this, (used in psp)
	def sortKeys(self,keys): keys.sort();return keys

# TODO: inherit from common parent (this and sessions)
class SummaryController(StatmonController):
	_title = 'Summaries'
	_filename = 'psp/summary.psp'
	def __init__(self,req,createContent=True,parent=None,
		entityfilter=None,schedulefilter=None,domainfilter=None,showSchedules=True,maxSessions=None,merge=False):
		self.schedulefilter = schedulefilter
		self.domainfilter = domainfilter
		self.entityfilter = entityfilter
		self.showSchedules = showSchedules
		self.maxSessions = maxSessions
		self.merge = merge
		StatmonController.__init__(self,req,createContent=createContent,parent=parent)

	def createContent(self):
		entityfilter = self.processInput(II('entity','Entity',II.TEXT,allowBlank=True,blankVal=None))
		if self.entityfilter: entityfilter = self.entityfilter

		activity = None
		if not (self.entityfilter or self.schedulefilter):
			activities = map( lambda x: (x['activity'],x['activity']), model.getSummaryActivities() )
			activity = self.processInput(II('activity','Activity',II.DROPDOWN,options=activities,allowBlank=True,blankVal=None))

		schedulefilter = self.processInput(II('schedule','Schedule',II.TEXT,allowBlank=True,blankVal=None))
		if self.schedulefilter: schedulefilter = self.schedulefilter

		start, end = self.getStartEnd('startweekago','endtoday')

		if self.parent:
			start = self.parent.updateInput('start')
			end = self.parent.updateInput('end')

		maxSessions = self.processInput(II('max','Max Sessions',II.NUMBER,default=1000,allowBlank=False))
		if self.maxSessions: maxSessions = self.maxSessions

		# quick and dirty hack
		nodes = model.getNodes()
		node2domain = {}
		entitylist = []
		for i in nodes:
			node2domain[i.node_name] = i.domain_name
			if self.domainfilter and self.domainfilter == i.domain_name:
				entitylist.append(i.node_name)
		if not self.domainfilter: entitylist = None

		cutOffRules = [
			('oldest','Oldest'),
			('shortest','Shortest'),
			('newest','Newest'),
			('longest','Longest'),]
		cutOffRule = self.processInput(II('cutrule','Cut-Off Rule',II.DROPDOWN,options=cutOffRules,default='oldest'))

		minDuration = self.processInput(II('duration','Min Duration (secs)',II.NUMBER,default=0,allowBlank=True))

		orderby='end_time desc'
		if cutOffRule == 'shortest':
			orderby='end_time-start_time desc'
		if cutOffRule == 'longest':
			orderby='end_time-start_time'
		elif cutOffRule == 'newest':
			orderby='start_time'

		summary = model.getSummary(
			end_start_time=start,
			start_end_time=end,
			entityfilter=entityfilter,
			entitylist=entitylist,
			activity=activity,
			schedulefilter=schedulefilter,
			minDuration=minDuration,
			orderby=orderby,
			limit=maxSessions
		)

		self.summaryTable = TableController(self.req,'summary','Summaries')

		self.summaryTable.addHeader(TH('entity', 'Entity',TH.TEXT))
		self.summaryTable.addHeader(TH('activity', 'Activity',TH.TEXT))
		self.summaryTable.addHeader(TH('start_time', 'Start Time',TH.DATETIME,sorted=True))
		self.summaryTable.addHeader(TH('end_time', 'End Time',TH.DATETIME))
		self.summaryTable.addHeader(TH('duration', 'Duration',TH.TIME,dbOrder=False,sortDesc=True))
		self.summaryTable.addHeader(TH('schedule_name', 'Schedule Name',TH.TEXT))
		self.summaryTable.addHeader(TH('examined', 'Examined',TH.NUMBER))
		self.summaryTable.addHeader(TH('affected', 'Affected',TH.NUMBER))
		self.summaryTable.addHeader(TH('failed', 'Failed',TH.NUMBER))
		self.summaryTable.addHeader(TH('bytes', 'Bytes',TH.BYTES))
		self.summaryTable.addHeader(TH('successful', 'Successful',TH.TEXT))

		for session in summary:
			session['duration'] = session['end_time']-session['start_time']
			self.summaryTable.addRow(**session)

class SummaryBackupStatisticController(StatmonController):
	_title = 'Backup Statistics'
	_filename = 'psp/summaryBackupStatistic.psp'

	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])
		schedulefilter = self.processInput(II('schedule','Schedule',II.TEXT,allowBlank=True,blankVal='',default='*'))

		start, end = self.getStartEnd('historystart','endyesterday')

		params = self.params
		params['domainfilter'] = domainfilter
		params['nodefilter'] = nodefilter
		params['schedulefilter'] = schedulefilter
		params['graphstart'] = start
		params['graphend'] = end

		# quick and dirty hack
		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter, fields = {'node_name' : 'node_name' }
		)
		nodelist = map( lambda x : x.node_name, nodes )

		self.summaryTable = TableController(self.req,'summary','Backup Statistics for Session Starting from %s to %s' % (start.date(),end.date()))

		self.summaryTable.addHeader(TH('entity', 'Entity',TH.TEXT,self.linkNode))
		self.summaryTable.addHeader(TH('successful','Total Successful Sessions Over Period',TH.NUMBER,abbr='TSS'))
		self.summaryTable.addHeader(TH('unsuccessful','Total Unsuccessful Sessions Over Period',TH.NUMBER,abbr='TUS'))

		self.summaryTable.addHeader(TH('avg_duration','Average Session Duration',TH.TIME,sorted=True,abbr='A.Dur'))
		self.summaryTable.addHeader(TH('max_duration','Maximum (Single) Session Duration',TH.TIME,abbr='M.Dur'))
		self.summaryTable.addHeader(TH('sum_duration','Total Session Duration Over Period',TH.TIME,abbr='T.Dur'))

		self.summaryTable.addHeader(TH('avg_transfer','Average Transfer per Session',TH.BYTES,sum=False,abbr='A.Trans'))
		self.summaryTable.addHeader(TH('max_transfer','Maximum (Single) Session Transfer',TH.BYTES,sum=False,abbr='M.Trans'))
		self.summaryTable.addHeader(TH('sum_transfer','Total Session Transfer Over Period',TH.BYTES,abbr='T.Trans'))

		self.summaryTable.addHeader(TH('avg_examined','Average Number of Objects Examined per Session',TH.NUMBER,sum=False,abbr='A.Ex'))
		#self.summaryTable.addHeader(TH('max_examined','M.Examined',TH.NUMBER,sum=False))
		self.summaryTable.addHeader(TH('sum_examined','Total Number of Objects Examined Over Period',TH.NUMBER,abbr='T.Ex'))

		self.summaryTable.addHeader(TH('avg_affected','Average Number of Objects Affected',TH.NUMBER,sum=False,abbr='A.Aff'))
		#self.summaryTable.addHeader(TH('max_affacted','M.Affected',TH.NUMBER,sum=False))
		self.summaryTable.addHeader(TH('sum_affected','Total Number of Objects Affected Over Period',TH.NUMBER,abbr='T.Aff'))

		#self.summaryTable.addHeader(TH('avg_affected','Average Number of Objects Affected',TH.NUMBER,sum=False,abbr='A.A'))
		self.summaryTable.addHeader(TH('max_failed','Maximum Number of Objects Failed (Single Session)',TH.NUMBER,sum=False,abbr='M.Fail'))
		self.summaryTable.addHeader(TH('sum_failed','Total Number of Objects Failed Over Period',TH.NUMBER,abbr='A.Fail'))
		
		self.summaryTable.addHeader(TH('avg_successp','Average Percent of Successful Objects (affected/(affected+failed))',TH.FLOAT,abbr='A.S %',sum=False))
		self.summaryTable.addHeader(TH('max_successp','Maximum Percent of Successful Objects (Single Best Session)',TH.FLOAT,abbr='M.S %',sum=False))

		summaries = model.getSummaryStatistics(
			start_time=start,start_end_time=end,
			entityfilter=nodefilter,entitylist=nodelist,
			schedulefilter=schedulefilter,orderby=self.summaryTable.getOrderBy())

		for summary in summaries:
			#summary['fail_percent'] = summary['sum_failed'] and ( float(summary['sum_failed']) / float( summary['sum_affected'] + summary['sum_failed'] ) ) * 100
			self.summaryTable.addRow(**summary)

		self.params['imagewidth'] = '995'
		self.params['imageheight'] = '121'

		#self.params['imagewidth'] = '409' # ca 41em
		#self.params['imageheight'] = '212'

		self.graphSessionActivityCount = grapher.SessionActivityCount(**params)
		self.graphSessionActivityTXRate = grapher.SessionActivityTXRate(**params)
