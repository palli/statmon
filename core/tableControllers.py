
from standardControllers import StandardController
from cgi import escape
from utils import BytesToText,StringToBool
from urllib import urlencode
import datetime

class TableHeader:
	"""Table header column"""
	# types
	BYTES = "bytes"
	DATE = "date"
	DATETIME = "datetime"
	FLOAT = "float"
	HTML = "html"
	NUMBER = "number"
	TEXT = "text"
	TIME = "time"

	# for sanity checks only
	TYPES = [ BYTES, DATE, DATETIME, FLOAT, HTML, NUMBER, TEXT, TIME,]

	def __init__(self,sname,name,htype,postProcess=None,sorted=False,sortable=True,sum=None,sortDesc=None,dbOrder=None,spanContent=False,escapeName=True,abbr=None):
		"""
			sname = short name, used for internal references,
			        should be short and unique
			name = display name
			htype = header type: TEXT, DATE, BYTES, NUMBER, etc..
		"""
		assert(htype in self.TYPES)

		self.sname = sname
		self.name = name
		if escapeName:
			self.name = escape(self.name)
		if abbr:
			self.name = '''<abbr title="%s">%s</abbr>''' % (self.name,abbr)
		self.htype = htype

		self.isFirst = False
		self.isLast = False

		if sum == None:
			if htype in (TH.NUMBER,TH.BYTES): sum = True
			else: sum = False
		self.flagSum = sum

		if sortDesc == None:
			if htype in (TH.NUMBER,TH.BYTES,TH.FLOAT,TH.TIME): sortDesc = True
			else: sortDesc = False
		self.flagSortDesc = sortDesc
		self.flagSorted = sorted
		self.flagSortable = sortable
		self.flagDbOrder = dbOrder
		self.spanContent = spanContent

		self.postProcess = postProcess

		self.flagTotal = False
		self.sum = 0

	def preProcess(self,oldval):
		miscData = None
		if type(oldval) in (list,tuple):
			miscData = oldval[1]
			newval = oldval = oldval[0]
		else:
			newval = oldval
		#assert(type(newval) == str)

		if self.flagSum:
			try: self.sum += oldval
			except: pass

		if self.htype == self.BYTES:
			newval = BytesToText(newval)
		elif self.htype == self.DATE:
			try: newval = newval.strftime('%Y-%m-%d')
			except: newval = 'Never'
		elif self.htype == self.DATETIME:
			try: newval = newval.strftime('%Y-%m-%d %H:%M:%S')
			except: newval = 'Never'
		elif self.htype == self.FLOAT:
			try: newval = '%3.2f' % newval
			except: newval = 'NaN'
		elif self.htype == self.HTML: return (newval,oldval)
		elif self.htype == self.NUMBER:
			try: newval = '%d' % newval
			except: newval = 'NaN'
		elif self.htype == self.TEXT:
			if newval == None: newval = ''
		elif self.htype == self.TIME:
			if isinstance(newval,datetime.timedelta):
				days = newval.days
				newval += datetime.datetime(1900,1,1)
				newval = '%03d:%s' % (days,newval.strftime('%H:%M:%S'))
			else:
				try: newval = newval.strftime('%H:%M:%S')
				except: newval = 'Never'

		if type(newval) == str:
			newval = unicode(newval,'latin1')
		elif type(newval) != unicode:
			newval = str(newval)
		newval = newval.encode('utf8')
		newval = escape(newval)
		if self.postProcess:
			if miscData:
				newval = self.postProcess(newval,miscData)
			else:
				newval = self.postProcess(newval)
		
		if self.spanContent:
			newval = '<span>%s</span>' % newval

		return (newval,oldval)

	def getSortOrder(self,reverse=False):
		order = 'asc'
		if self.flagSortDesc == (not reverse):
			order = 'desc'
		
		return order

	def getHead(self,sortable=True):
		if self.flagSortable and sortable:
			fields = self.parent.getAllFields()

			fields[self.parent.name+'SortOrder'] = self.getSortOrder(self.flagSorted)
			fields[self.parent.name+'Sort'] = self.sname

			jsRev = 'false'
			if self.getSortOrder() != 'desc': jsRev = 'true'
			
			jsSorted = 'false'
			if self.flagSorted: jsSorted = 'true'

			anchor = '%s_%s' % (self.parent.name,self.sname)
			onclick = '''onclick="this.blur(); return sortTable('%s_body',%d,%s,%s);"''' %\
						(self.parent.name, self.idx, jsRev,jsSorted)

			return '''
					<a name="%s" class="tablelink" href="?%s#%s" %s>
						%s
					</a>
					''' %\
					( anchor, escape(urlencode(fields)), anchor, onclick, self.name )

		return self.name

	def getFoot(self):
		if self.flagSum:
			return self.preProcess(self.sum)[0]
		elif self.flagTotal:
			return 'Total:'
		return ''

	def __getClass(self):
		c = []

		if self.flagSorted and self.flagSortable:
			c.append('sorted')

		return c

	def getHeadClass(self,sortable=True):
		c = self.__getClass()
		
		c.append('title')
		if self.flagSorted and sortable:
			c.append(self.getSortOrder())

		return ' '.join(c)

	def getFootClass(self):
		c = self.__getClass()
		
		if self.flagSum:
			c.append(self.htype)
		elif self.flagTotal:
			c.append('ttext')

		return ' '.join(c)

	def getBodyClass(self):
		c = self.__getClass()
		c.append(self.htype)

		return ' '.join(c)
	
	#def getSpan(self):
		#span = 1
		##if self.isLast: span += 1
		##if self.isFirst: span += 1
		#return span

class TH(TableHeader): pass

class TableRow(TableHeader):
	def __init__(self,name,val,htype,postProcessName=None,postProcessVal=None,spanContent=False,abbr=None):
		assert(htype in self.TYPES)

		self.flagSum = False

		self.spanContent = spanContent

		self.htype = self.TEXT
		self.postProcess = postProcessName
		self.name = self.preProcess(name)[0]

		if abbr:
			self.name = '''<abbr title="%s">%s</abbr>''' % (self.name,abbr)

		self.htype = htype
		self.postProcess = postProcessVal
		self.val = self.preProcess(val)[0]

class TR(TableRow): pass

class PropTableController(StandardController):
	_filename = 'psp/propTable.psp'

	def __init__(self, req, title):
		StandardController.__init__(self,req,createContent=False)

		self.title = self.escape(title)
		self._rows = []
	
	def addRow(self,row):
		assert(isinstance(row,TR))
		self._rows.append(row)

	def getContent(self,shadowdrop=True):
		if shadowdrop: return self.shadowdrop(self.getContent(shadowdrop=False))
		return StandardController.getContent(self)

class TableController(StandardController):
	_filename = 'psp/table.psp'

	def __init__(self, req, name, title=None, dbOrder=True,
		showHeaders=True,className='standardTable',emptyMessage='No Data Found',extraFooter=None,extraFooterClass='',enableExport=False):
		StandardController.__init__(self,req,createContent=False)

		self.name = name
		self._headers = []
		self._snames = []
		self._rows = []
		self.dbOrder = dbOrder
		self._sortCalced = False
		self.title = self.escape(title)
		self.hasFooter = False
		self.showHeaders = showHeaders
		self.className = className
		self._emptyMessage = emptyMessage
		self.extraFooter = extraFooter
		self.extraFooterClass = extraFooterClass
		self.formatTable = True
		self.enableExport = enableExport

	def calcSorting(self):
		if self._sortCalced: return
		self._sortCalced = True
		
		lastSum = False
		self._headers.reverse()
		for col in self._headers:
			if col.flagSum:
				lastSum = True
				self.hasFooter = True
			elif lastSum:
				col.flagTotal = True
				lastSum = False
		self._headers.reverse()

		sortColName = self.getField(self.name+'Sort')
		sortOrder = self.getField(self.name+'SortOrder')
		if sortOrder != 'desc' and sortOrder != 'asc': sortOrder = None

		self.dbSortable = False
		self.sortColIdx = None
		for i in range(len(self._headers)):
			col = self._headers[i]
			col.idx = i
			if sortColName and col.flagSorted and sortColName != col.sname:
				# there can only be one sorted column
				col.flagSorted = False
			if col.flagSorted or sortColName == col.sname:
				# the sort column found
				self.sortColIdx = i
				sortColName = col.sname
				col.flagSorted = True
				if sortOrder == 'desc':
					col.flagSortDesc = True
				elif sortOrder == 'asc':
					col.flagSortDesc = False
				sortOrder = col.getSortOrder()

				if self.dbOrder and (col.flagDbOrder == None or col.flagDbOrder):
					self.dbSortable = True

		self.sortColName = sortColName
		self.sortOrder = sortOrder

	def createContent(self):
		self.calcSorting()
		if self._headers:
			self._headers[0].isFirst = True
			self._headers[-1].isLast = True

		if self.sortColIdx != None and not self.dbSortable:
			rev = False
			if self.sortOrder == 'desc': rev = True
			self.sortRows(self.sortColIdx,rev)

		formatTable = StringToBool(self.getField('formatTable'),none=self.formatTable)
		if formatTable: self.formatIndex = 0
		else: self.formatIndex = 1
		fields = self.getAllFields()
		fields['exportTable'] = self.name
		self.exportURL = escape(urlencode(fields))

	def sortRows(self,col,rev):

		k = lambda x: x[col][1]
		def c(a, b):
			if a == b: return 0
			elif a == None: return -1
			elif b == None: return 1
			else: return cmp(a,b)
		self._rows.sort(c,key=k,reverse=rev)

	def getContent(self,shadowdrop=True):
		if shadowdrop: return self.shadowdrop(self.getContent(shadowdrop=False))
		self.createContent()
		return StandardController.getContent(self)

	def addHeader(self,header):
		assert(isinstance(header,TableHeader))
		assert(header.sname not in self._snames)

		header.parent = self
		self._headers.append(header)
		self._snames.append(header.sname)
	
	def addRow(self,*arg,**keywords):
		#for key in keywords: assert(key in self._snames)

		row = []
		for hcol in self._headers:
			row.append(hcol.preProcess(keywords.get(hcol.sname,None)))
		row.append( keywords.get('oddevenclass', '') )
		row.append( keywords.get('rowclass', '') )
		self._rows.append(row)

	def getOrderBy(self):
		self.calcSorting()
		if self.dbSortable:
			return '%s %s' % ( self.sortColName, self.sortOrder )
		return None
	
	def setEmptyMessage(self,emptyMessage):
		self._emptyMessage = emptyMessage
	
	def getName(self):
		return self.name
	
	def setExportable(self,enable=True):
		self.enableExport = enable

class CVSTableController(TableController):
	_filename = 'psp/cvsTable.psp'
	_content_type = 'text/csv'
	def getContent(self):
		import csv
		self.formatTable = False
		self.createContent()
		self.csvWriter = csv.writer(self.req)
		return StandardController.getContent(self)

	def CVSLineDump(self,array,conv=None):
		self.csvWriter.writerow(map(conv,array))
		return ''
