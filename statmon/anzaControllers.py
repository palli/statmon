
from core.tableControllers import TableController,TH,PropTableController,TR
from core.inputControllers import II

from statmonControllers import StatmonController

import model

import datetime

class AnzaBackupReportController(StatmonController):
	_title = 'Backup Report'
	_filename = 'psp/anzaBackupReport.psp'
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])

		contacts = map( lambda x: (x['contact'],'%s (%d)' % (x['contact'],x['count'])), model.getAnzaContacts() )
		contactfilter = self.processInput(II('contact','Contact',II.DROPDOWN,options=contacts,allowBlank=True,blankVal=''))

		start = self.processInput(self.standardInputs['startyesterday'])
		end = self.processInput(self.standardInputs['endtoday'])

		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			contactfilter=contactfilter
		)

		self.filespaces = {}
		self.clientopts = {}
		self.nodeList = []
		self.domainList = {}
		
		for i in nodes:
			self.nodeList.append( i.node_name )
			self.domainList[i.domain_name] = None
			# Filespace and filespace graphs
			self.filespaces[i.node_name] = filespaceTable = TableController(self.req,'filespaces_%s'%i.node_name,'Filespaces')
			filespaceTable.addHeader(TH('filespace_name','Filespace Name',TH.TEXT))
			filespaceTable.addHeader(TH('filespace_type', 'FS Type',TH.TEXT))
			filespaceTable.addHeader(TH('backup_end', 'Last Backup',TH.DATE))
			filespaceTable.addHeader(TH('capacity_bytes', 'Capacity',TH.BYTES,self.linkGraph))
			filespaceTable.addHeader(TH('used_bytes', 'Used',TH.BYTES,self.linkGraph))
			filespaceTable.addHeader(TH('logical_total', 'In Storage',TH.BYTES,dbOrder=False,sorted=True))
	
			filespaces = model.getFilespaces(i.node_name,orderby=filespaceTable.getOrderBy())
			for j in filespaces:
				j['logical_total'] = j.logical_bytes_bkup+j.logical_bytes_arch
				filespaceTable.addRow(**j)

			# Optionsets
			self.clientopts[i.node_name] = clientoptsTable = TableController(self.req,'clientopts_%s'%i.node_name,'Client Options Set',dbOrder=False)
			clientoptsTable.addHeader(TH('seqnumber','Sequence', TH.NUMBER,sorted=True,sortDesc=False))
			clientoptsTable.addHeader(TH('option_name','Option Name', TH.TEXT))
			clientoptsTable.addHeader(TH('option_value','Value', TH.NUMBER))
			
			clientopts = model.getClientopts(i.node_name)
			for j in clientopts: clientoptsTable.addRow(**j)
		
		copygroups = []
		for i in self.domainList.keys():
			copygroups += model.getCopygroups(domain_name=i)
		
		# Lets construct a copygroup table
		self.copygroups = copygroupTable = TableController(self.req,'copygroup','Copygroups',dbOrder=False)
		copygroupTable.addHeader(TH('domain_name', 'Domain Name', TH.TEXT ))
		copygroupTable.addHeader(TH('set_name', 'Set Name', TH.TEXT ))
		copygroupTable.addHeader(TH('copygroup_name', 'Group Name', TH.TEXT ))
		copygroupTable.addHeader(TH('destination', 'Destination', TH.TEXT ))
		copygroupTable.addHeader(TH('verexists', 'Versions Data Exists', TH.TEXT ))
		copygroupTable.addHeader(TH('verdeleted', 'Versions Data Deleted', TH.TEXT ))
		copygroupTable.addHeader(TH('retextra', 'Retain Extra Versions', TH.TEXT ))
		copygroupTable.addHeader(TH('retonly', 'Retain Only Version', TH.TEXT ))
		
		for j in copygroups: copygroupTable.addRow(**j)
		self.nodeList.sort()

class AnzaUsageReportController(StatmonController):
	_title = 'Usage Report'
	_filename = 'psp/anzaUsageReport.psp'
	def createContent(self):
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])

		contacts = map( lambda x: (x['activity'],x['activity']), model.getAnzaContacts() )

		contactfilter = self.processInput(II('contact','Contact',II.DROPDOWN,options=contacts,allowBlank=True,blankVal=''))

		#stgpool = self.processInput(self.standardInputs['stgpool'])
		
		showDuplicatePools = self.processInput(II('dups','Include _DUP_',II.DROPDOWN,options=[('yes','Yes'),('','No')],allowBlank=True))

		# Create node list table
		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes')
		if not contactfilter:
			nodeTable.addHeader(TH('contact', 'Contact',TH.TEXT,sorted=True))
			nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode))
		else:
			nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('num_files', 'Number of Files',TH.NUMBER,dbOrder=False))
		nodeTable.addHeader(TH('logical_total', 'Total Storage',TH.BYTES,dbOrder=False))
		
		nodes = model.getNodes(
			nodefilter=nodefilter,
			domainfilter=domainfilter,
			contactfilter=contactfilter,
			orderby=nodeTable.getOrderBy()
		)
		
		for i in nodes:
			i['logical_total'] = i.logical_bytes_arch+i.logical_bytes_bkup
			i['num_files'] = i.num_files_bkup + i.num_files_arch
			if showDuplicatePools == True:
				i['logical_total'] += i.dup_logical_bytes_arch+i.dup_logical_bytes_bkup
				i['num_files'] += i.dup_num_files_bkup + i.dup_num_files_arch
			nodeTable.addRow(**i)

