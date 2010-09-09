#!/usr/bin/python

if __name__ == '__main__':
	import os,sys

	p = os.path.abspath(os.path.dirname(os.curdir+'/'+__file__)+'.')
	sys.path.append(p)

import os.path
from core.utils import *
import datasource
import rrdtool
import pickle
import time
import datetime

class RRDDef:
	"""Stores data sources and other informations associated with a graph"""
	def __init__(self):
		self.hasMax = None
		self.dataSources = []
		self.creationTime = time.time()
	
	def __str__(self):
		return '%s,%s' % (self.hasMax,self.dataSources)
	
	def __repr__(self):
		return self.__str__()
	
	def store(self,filename):
		file = open(filename, 'wb')

		obj = [
			self.creationTime,
			self.hasMax,
			self.dataSources,
			self.maxTS,
			self.maxDS,
			self.maxVal ]

		pickle.dump(obj,file)
		file.close()

	def load(self,filename):
		file = open(filename, 'rb')
		obj = pickle.load(file)
		self.creationTime, self.hasMax, self.dataSources, self.maxTS, self.maxDS, self.maxVal = obj
		file.close()

class RRDTool:
	_filename = '@profile@-@hashid@-@ds@.@ending@'

	def __init__(self,*arg,**keywords):
		self.__keywords = keywords

		self.l = self.getKeyword('logger',NullLogger())
		self.__path = self.getKeyword('path')

		hashstr = ''
		for param,options in self._params.items():
			if self.getKeywordOption(param,'Hash'):
				keywords[param] = self.getKeyword(param)
				hashstr += str(self.getKeyword(param))
		self.__hashid = str(generateHash(hashstr))
		self.defs = None

	def getKeywordOption(self,key,option):
		params = self._params
		if not params.has_key(key): return None

		options = params[key]
		if not options.has_key(option): return None
		return options[option]

	def getKeyword(self,key,default=''):
		if not self.__keywords.has_key(key):
			params = self._params
			if params.has_key(key) and params[key].has_key('Default'):
				return params[key]['Default']
			return default
		return self.__keywords[key]
	
	def getKeywords(self,ktype=None):
		kwords = []
		for key,value in self.__keywords.items():
			if not ktype or type(value) in ktype:
				kwords.append(key)
		return kwords

	def getFilename(self,ds='None',ending='rrd',appendPath=True,injectPath=''):
		filename = self._filename.replace('@profile@',self._profile)
		filename = filename.replace('@ds@',str(ds))
		filename = filename.replace('@hashid@',self.__hashid)
		filename = filename.replace('@ending@',ending)

		if injectPath:
			filename = injectPath + filename

		if appendPath and not os.path.isabs(filename):
			filename = self.__path + filename

		return filename

	def storeDefs(self,defs):
		defname = self.getFilename(ending='def',injectPath=self.datapath)
		defs.store(defname)
		self.defs = defs

	def loadDefs(self):
		defs = self.defs
		if not self.defs:
			try:
				defs = RRDDef()
				defname = self.getFilename(ending='def',injectPath=self.datapath)
				defs.load(defname)
			except IOError, e:
				defs = None
				self.l.show("Failed to load RRD definitions !","!")

		return defs

def toRRDTime(timestamp):
	if type(timestamp) == datetime.datetime:
		timestamp = time.mktime( timestamp.utctimetuple() )
	return str(int(timestamp))

def fromRRDTime(ts):
	if type(ts) == datetime.datetime:
		return ts
	return datetime.datetime(*time.gmtime(int(ts))[:-3])

class Grapher(RRDTool):
	__colors = ['#990000','#009933','#330099','#CC6600','#FF0066', '#339999','#660099','#888888','#00ddbb']
	__cindex = 0

	_title = 'Default Title'
	_resolution = 86400
	_step = 1
	_base = '1000'
	_heartBeat = 1
	_upperLimit = 'u'
	_graphType = 'AREA'
	_graphOption = None # default STACK for AREA, empty for LINE
	_textType = ''
	_params = { }
	_max = 'Capacity'
	_query = ''' select 0, 0, 0 '''
	_maxCap = 0
	_maxVal = 0
	_miscDsInfo = DefaultDict(DefaultDict(None))

	def __init__(self,*arg,**keywords):
		RRDTool.__init__(self,*arg,**keywords)

		self.db = self.getKeyword('db',None)
		self.maxage = self.getKeyword('maxage',None)
		self.imagepath = self.getKeyword('imagepath')
		self.datapath = self.getKeyword('datapath')
		self.imageheight = str(self.getKeyword('imageheight'))
		self.imagewidth = str(self.getKeyword('imagewidth','400'))
		self.graphstart = self.getKeyword('graphstart',None)
		self.graphend = self.getKeyword('graphend',None)
		self.hidetitle = self.getKeyword('hidetitle', False)
		self.format = self.getKeyword('format', 'PNG')

		self.__info = (int(self.imagewidth or 400)+81,int(self.imageheight or 100)+82,'')

		self.inter = DefaultDict(DefaultDict(0))

		if self.getKeyword('update'):
			self.update()

		if self.getKeyword('graph'):
			self.graph()

	def __getData(self):
		""" fetches data from db using profile Query.
		Expected format: ts, ds, desc, value, [max] """
		
		query = self._query
		for key in self.getKeywords():
			value = self.getKeyword(key)
			if self.getKeywordOption(key,'Escape'):
				value = self.db.escape(value)
			if self.getKeywordOption(key,'EscapeFilter'):
				value = self.db.escapeFilter(value)
			if self.getKeywordOption(key,'EscapeList'):
				value = self.db.escapeList(value)

			if type(value) in (str,int):
				query = query.replace('@'+key+'@', str(value))

		count, data = self.db.query(query)
		data = list(data)

		# sanity checks
		if count == 0:
			data = [(int(time.time()), 'No Matching Data Found', 0),]
			count = 1

		from array import ArrayType
		for i in range(len(data)):
			data[i] = list(data[i])
			if type(data[i][1]) is ArrayType: data[i][1] = data[i][1].tostring()

		return self.postProcess(data)

	def postProcess(self,data):
		if not (2 < len(data[0]) and len(data[0]) < 5):
			raise BadDataException('Badly formatted data returned ')

		return data
	def update(self,db=None,incremental=False):
		self.l.start("""Preprocessor.update(profile='%s')""" % self._profile)

		if db: self.db = db

		data = self.__getData()
		step = self._step
		heartbeat = self._heartBeat

		hasMax = False
		datasources = DefaultDict( [] )
		ordermap = {}
		orderkey = 0
		last = None
		maxTS = 0
		for set in data:
			vmax = 'U'
			if len(set) == 3: ts,desc,value = set
			if len(set) == 4: ts,desc,value,vmax = set
			if vmax != 'U': hasMax = True
			maxTS = max(maxTS,ts)

			if not ordermap.has_key(str(desc)):
				ordermap[str(desc)] = orderkey
				orderkey += 1
			key = (ordermap[str(desc)], str(desc))

			last = ts
			update = (str(ts), str(value), str(vmax), str(self.inter[desc][ts]))
			datasources[key].append(':'.join(update))

		defs = RRDDef()
		defs.hasMax = hasMax
		defs.maxTS = maxTS
		defs.maxDS = self._max
		defs.maxVal = self._maxVal
		for (ds,desc),update in datasources.items():
			rrdname = self.getFilename(ds,injectPath=self.datapath)
			start = str(int(update[0].split(':')[0])-1)
			rrdtool.create(rrdname,
				'--start', start, '--step', str(int(self._resolution*step)),
				'DS:ds:GAUGE:%d:U:U' % int(self._resolution*heartbeat*step),
				'DS:max:GAUGE:%d:U:U' % int(self._resolution*heartbeat*step),
				'DS:inter:GAUGE:%d:U:U' % int(self._resolution*heartbeat*step),
				'RRA:LAST:0.5:1:10000',
				#'RRA:AVERAGE:0.5:7:1200',
				'RRA:MAX:0.5:1:10000',)
			rrdtool.update(rrdname,'--template','ds:max:inter', *update)
			defs.dataSources.append((ds,rrdname,desc,self._miscDsInfo[desc]))
		defs.dataSources.sort()

		self.storeDefs(defs)
		self.l.end()

	def age(self):
		defs = self.loadDefs()
		if not defs: return None
		return time.time()-defs.creationTime

	def graph(self,maxage=None):
		self.l.start("""Grapher.graph(profile='%s',maxage=%s)""" % (self._profile,maxage))
		if not maxage:
			maxage = self.maxage

		defs = self.loadDefs()
		if defs:
			age = self.age()
			self.l.show("Definations found, age: %3.2f seconds" % age)
		if not defs:
			self.l.show("No definations found, attempting forced update()")
			self.update()
			defs = self.loadDefs()
		if maxage and self.age() > maxage:
			self.l.show("Definations too old, attempting forced update()")
			self.update()
			defs = self.loadDefs()

		title = self.getTitle()
		base = self._base
		upper = self._upperLimit
		ttype = self._textType

		colors = self.getColors(defs.dataSources)

		rest = []
		if self.graphstart:
			rest.append( '--start' )
			rest.append( toRRDTime(self.graphstart) )
		if self.graphend:
			rest.append( '--end' )
			rest.append( toRRDTime(self.graphend) )
		if self.imageheight:
			rest.append( '--height' )
			rest.append( self.imageheight )
		if self.imagewidth:
			rest.append( '--width' )
			rest.append( self.imagewidth )
		
		# This code sets X-axis legends without week numbers.
		duration = None
		if self.graphend and self.graphstart:
			duration = int(toRRDTime(self.graphend)) - int(toRRDTime(self.graphstart)) 

		if duration <= 24*60*60 and duration > self._resolution:
			rest.append( '--x-grid' )
			rest.append( 'MINUTE:10:HOUR:1:HOUR:1:0:%H')
		elif duration > 15*24*60*60 and duration < 6*30*24*60*60: # Greater than two weeks, less than 6 months
			rest.append( '--x-grid' )
			rest.append( 'WEEK:1:MONTH:1:MONTH:1:0:%b' )
		elif duration > 24*60*60 and duration < 14*24*60*60: # Greater than 1 day, less or equal to two weeks
			rest.append( '--x-grid' )
			rest.append( 'DAY:1:WEEK:1:DAY:1:0:%d' )
		elif duration > 365*24*60*60: # Greater than 1 year
			rest.append( '--x-grid' )
			rest.append( 'MONTH:1:YEAR:1:YEAR:1:0:%Y' )

		inter = []
		for ds,rrd,desc,misc in defs.dataSources:
			gtype = misc.get('graphType',self._graphType)
			options = misc.get('graphOption',self._graphOption)
			if options == None:
				 if gtype[:3] != 'AREA': options = ''
				 else: options = 'STACK'
			if options and options[0] != ':': options = ':' + options

			color = colors[ds]+misc.get('colorAlpha','ee')

			rest.append( 'DEF:%s=%s:ds:LAST'%(ds,rrd) )
			desc = desc.replace('\\','\\\\').replace(':','\\:')
			
			if ttype and ttype[0] == 'Current':
				rest.append( 'VDEF:%slast=%s,LAST'%(ds,ds) )
				rest.append( '%s:%s%s:%-20s\:%s'%(gtype,ds,color,desc,options) )
				rest.append( 'GPRINT:%slast:%s\l' % (ds,ttype[1]))
			elif ttype and ttype[0] == 'PercentMax':
				rest.append( 'DEF:ds%smax=%s:max:MAX'%(ds,rrd) )
				rest.append( 'DEF:ds%s=%s:ds:MAX'%(ds,rrd) )
				rest.append( 'VDEF:cur%smax=ds%smax,LAST'%(ds,ds) )
				
				rest.append( 'CDEF:ds%sused=ds%smax,ds%s,*,100,/'%(ds,ds,ds) )
				rest.append( 'VDEF:cur%sused=ds%sused,LAST'%(ds,ds) )

				rest.append( 'VDEF:cur%spuse=ds%s,LAST'%(ds,ds) )

				rest.append( '%s:%s%s:%-15s\:%s'%(gtype,ds,color,desc,options) )
				rest.append( 'GPRINT:cur%smax:%s' % (ds,ttype[1]) )
				rest.append( 'GPRINT:cur%sused:%s' % (ds,ttype[2]) )
				rest.append( 'GPRINT:cur%spuse:%s\l' % (ds,ttype[3]) )
				
				defs.hasMax = False
			else:
				if misc['hide']:
					rest.append( '%s:%s%s'%(gtype,ds,color) )
				else:
					rest.append( '%s:%s%s:%s %s'%(gtype,ds,color,desc,options) )
				rest.append( 'VDEF:%slast=%s,LAST'%(ds,ds) )
				#rest.append( '%s:%slast%s:%s\l%s'%('TICK',ds,color,desc,'') )
				#rest.append( 'GPRINT:%s:%%S' % ds )
				#rest.append( 'DEF:%s-=%s:ds:AVERAGE'%(ds,rrd) )
				#rest.append( 'LINE2:%s-%s:%s'%(ds,'#1133cc',defs.maxDS) )

			if defs.hasMax and ds == defs.dataSources[-1][0]:
				rest.append( 'DEF:%s-max=%s:max:MAX'%(ds,rrd) )
				rest.append( 'LINE2:%s-max%s:%s'%(ds,'#1133cc',defs.maxDS) )
			
			rest.append( 'DEF:%s-inter=%s:inter:MAX'%(ds,rrd) )
			#rest.append( 'TICK:%s-inter#cccccc55:1.0'%ds )
			inter.append( '%s-inter' % ds )
		if inter:
			inter.append(str(len(inter)))
			inter.append('AVG')
			rest.append( 'CDEF:inter=%s'%(','.join(inter)) )
			rest.append( 'TICK:inter#cccccc55:1.0' )

		#rest.append( 'COMMENT: \l' )
		#rest.append( 'COMMENT:Updated\: %s' % time.ctime(defs.creationTime).replace(":","\:") )

		if not self.hidetitle:
			rest.append( '--title' )
			rest.append( title )

		if self._maxCap and defs.maxVal:
			upper = str(self._maxCap * defs.maxVal)
			rest.append( '--rigid' )

		filename = self.getFilename(ending=self.format.lower(),injectPath=self.imagepath)
		self.__info = rrdtool.graph(
			str(filename),
			'--imgformat', str(self.format),
			# hide / transparent
			'--color', 'BACK#ffffff00',
			'--color', 'CANVAS#bbbbbb11',
			'--color', 'SHADEA#ffffff00',
			'--color', 'SHADEB#ffffff00',
			
			# frame for legend boxes, pure back
			'--color', 'FRAME#000000ff',
			# text color, dark gray
			'--color', 'FONT#505050ff',

			# stuff
			#'--color', 'GRID#000000ff',
			#'--color', 'MGRID#ffffff00',
			#'--color', 'ARROW#ffffff00',
			#'--color', 'AXIS#000000ff',

			# TODO Reinstate fonts, does not work on all distros
			#'--font', 'DEFAULT:0:/usr/share/fonts/corefonts/arial.ttf',
			#'--font', 'TITLE:8:/usr/share/fonts/corefonts/arialbd.ttf',
			#'--font', 'AXIS:0:/usr/share/fonts/corefonts/arial.ttf',
			#'--font', 'UNIT:0:/usr/share/fonts/corefonts/arial.ttf',
			#'--font', 'LEGEND:0:/usr/share/fonts/corefonts/cour.ttf',
			'--upper-limit', str(upper),
			'--lower-limit', '0',
			'--slope-mode',
			'--width', '350',
			'--imginfo', '%s',
			'--base', base,
			*rest)
		self.l.show("imgname: %s" % self.__info[2][0])
		self.l.show("width: %d - height: %d" % self.__info[0:2])
		self.l.end()

	def getNextColor(self,hashobj=None):
		if hashobj:
			cindex = generateHash(hashobj) % len(self.__colors)
			if cindex == (self.__cindex-1) % len(self.__colors): pass
			else: self.__cindex = cindex

		color = self.__colors[self.__cindex]
		self.__cindex += 1
		self.__cindex %= len(self.__colors)

		return color

	def getColors(self,dataSources=None):
		if dataSources==None: return self.__colors
		self.resetColors()
		colors = {}
		if len(dataSources) > 1:
			used = {}
			descMap = {}
			for ds,rrd,desc,misc in dataSources:
				if misc['colorLike']: continue
				descMap[desc] = ds
				color = self.getNextColor(desc)
				if not used.has_key(color):
					colors[ds] = color
				else:
					colors[ds] = None
				used[color] = 1

			for ds,color in colors.items():
				if not color:
					for c in self.__colors:
						if not used.has_key(c):
							color = c
							used[color] = 1
							break
					if not color:
						color = self.getNextColor(desc)
					colors[ds] = color
			
			for ds,rrd,desc,misc in dataSources:
				if misc['colorLike']: colors[ds] = colors[descMap[misc['colorLike']]]
		else:
			colors[dataSources[0][0]] = self.getNextColor()
		return colors

	def resetColors(self):
		self.__cindex = 0

	def getImagename(self):
		return self.getFilename(ending=self.format.lower(),appendPath=False,injectPath=self.imagepath)

	def getFullPathImagename(self):
		return self.getFilename(ending=self.format.lower(),injectPath=self.imagepath)

	def getImagewidth(self):
		return self.__info[0]

	def getImageheight(self):
		return self.__info[1]

	def getParams(self):
		keymap = {}
		for key in self.getKeywords((str,unicode,list,tuple,int,type(None),datetime.datetime)):
			if not key in ['path','imagepath','datapath']:
				value = self.getKeyword(key)
				if type(value) is datetime.datetime: value = toRRDTime(value)
				keymap[key] = value

		return keymap
	
	def getStaticTitle(self):
		return self._title
	def getStart(self):
		return toRRDTime( self.graphstart ) 
	def getEnd(self):
		return toRRDTime( self.graphend )
	def getTitle(self):
		return self.getKeyword('title',self.getStaticTitle())

	def processMovingAverage(self, data,days=30):
		#return self.processLowpass(data)
		"""http://en.wikipedia.org/wiki/Moving_average#Prior_moving_average"""
		
		# TODO: Change this to Central moving average or fancier
		newData = []
		avgList = []

		assert not self._maxVal

		for entry in data[0:days]:
			ts,name,value = entry[0:3]
			avgList.append(float(value))
		self._max = '%d Day Moving Average' % len(avgList)

		for entry in data:
			ts,name,value = entry[0:3]
			avgList.pop(0)
			avgList.append(float(value))
			avg = sum(avgList)/float(len(avgList))
			self._maxVal = max(avg,self._maxVal)
			newData.append((ts,name,value,avg))
		return newData

	def processLowpass(self,data,alpha=0.1):
		self._max = '2x Low-Pass' % alpha

		data = map(lambda x: [x[0],x[1],float(x[2]),float(x[2])],data)
		data[0][3] = data[0][2]

		assert not self._maxVal

		# forward pass
		for i in range(1,len(data)):
			prev = data[i-1]
			row = data[i]
			row[3] = prev[3] + alpha * (row[3]-prev[3])

		# reverse pass
		for i in range(len(data)-2,-1,-1):
			prev = data[i+1]
			row = data[i]
			row[3] = prev[3] + alpha * (row[3]-prev[3])

			self._maxVal =  max(self._maxVal,row[3])

		return data

	def processWeightedMovingAverage(self, data, span=21):
		#return self.processLowpass(data)
		dataMap = DefaultDict([])
		stableKeys = [] # to keep stable order
		anyTsMap = {}
		for entry in data:
			name = entry[1]
			anyTsMap[entry[0]] = 1
			if not dataMap.has_key(name): stableKeys.append(name)
			dataMap[name].append(entry)

		self._max = 'Moving Average'
		assert not self._maxVal

		#from math import e,log
		#scale = span/(e-1)

		newData = []
		for key in stableKeys:
			data = dataMap[key]
			hasMax = len(data[0]) > 3
			for center in range(len(data)):
				start = max(0,center-span)
				end = min(center+span,len(data)-1)

				totalWeight = 0.0
				sum = 0.0
				msum = 0.0
				
				for index in range(start,end):
					value = span-abs(center-index)
					#weight = log((scale+value)/scale)
					weight = value**2/float(span)
					#if center == 100: print weight
					totalWeight += weight

					sum += float(data[index][2])*weight
					if hasMax: msum += float(data[index][3])*weight

				avg = totalWeight and sum/totalWeight
				self._maxVal = max(avg,self._maxVal)
				mavg = totalWeight and msum/totalWeight

				newEntry = list(data[center][0:3])+[avg,]
				newData.append(newEntry)

		return newData

	def processInterpolation(self,data,missingIsZero=None):
		dataMap = DefaultDict([])
		stableKeys = [] # to keep stable order
		anyTsMap = {}
		for entry in data:
			name = entry[1]

			anyTsMap[entry[0]] = 1
			if not dataMap.has_key(name): stableKeys.append(name)
			dataMap[name].append(entry)

		newData = []
		for key in stableKeys:
			data = dataMap[key]
			hasMax = len(data[0]) > 3
			for no,entry in zip(range(len(data)),data):
				ts,value = entry[0],float(entry[2])
				if hasMax: mval = float(entry[3])

				newData.append(entry)

				next = no+1
				if next >= len(data): break

				nextTs,nextVal = data[next][0],float(data[next][2])
				if hasMax: nextMval = float(data[next][3])


				if not missingIsZero:
					tsDiff = float(nextTs-ts)
					diff = (nextVal-value)/tsDiff
					if hasMax: mDiff = (nextMval-mval)/tsDiff
				zero = missingIsZero

				newTs = ts+self._resolution
				while nextTs>newTs:
					if zero == None and anyTsMap.has_key(newTs): zero = True

					if zero:
						newEntry = [newTs,key,0]
						if hasMax: newEntry.append(0)
					else:
						newDiff = newTs-ts
						newVal = float(value+newDiff*diff)
						newEntry = [newTs,key,newVal]
						if hasMax: newEntry.append(float(mval+newDiff*mDiff))
						self.inter[key][newTs] = 1

					newData.append(newEntry)

					newTs += self._resolution

		return newData

	def processExtrapolation(self,data):
		# TODO:
		# http://en.wikipedia.org/wiki/Extrapolation
		return data

class NoDataException(Exception):
	def __init__(self,value): self.value = value
	def __str__(self): return repr(self.value)

class BadDataException(Exception):
	def __init__(self,value): self.value = value
	def __str__(self): return repr(self.value)

class DailyBackup(Grapher):
	_profile = "DailyBackup"
	_title = "Daily Amount of Backup"
	_base = '1024'

	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'schedulefilter': {'Hash':1,'EscapeFilter':1},
		}
	_query = '''
                     select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                            'Daily Transfer' ds,
                            sum(bytes) val
                       from summary s,
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
                      where activity='BACKUP'
                        and s.entity = n.node_name
                        and (@schedulefilter@ is null or
                             ifnull(schedule_name,'') like @schedulefilter@)
                   group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		#return self.processMovingAverage(self.processInterpolation(data,missingIsZero=True))
		return self.processWeightedMovingAverage(self.processInterpolation(data,missingIsZero=True),span=15)
		#return self.processLowpassTest(self.processInterpolation(data,missingIsZero=True),alpha=.1)
class DailyRestore(Grapher):
	_profile = 'DailyRestore'	
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			}
	_title = 'Daily Amount Restored'
	_base  =  '1024'

	_query = ''' select ts,
                             'Daily Transfer' ds,
                             sum(bytes) val
                        from summary_daily_restore
                       where (node_name like @nodefilter@ or node_name in @nodelist@)
                         and (domain_name like @domainfilter@ or domain_name in @domainlist@)
                    group by ts; '''
	def postProcess(self, data):
		return self.processMovingAverage(self.processInterpolation(data,missingIsZero=True))
class TotalArchive(Grapher):
	_profile = 'TotalArchive'
	_title = 'Total Amount in Archive'
	_base = '1024'
	_textType = ['Current','%6.0lf %SB (current size)']
	_params = {
				'nodefilter': {'Hash':1,'EscapeFilter':1},
				'nodelist': {'Hash':1,'EscapeList':1},
				'domainfilter': {'Hash':1,'EscapeFilter':1},
				'domainlist': {'Hash':1,'EscapeList':1},
			}
	#_query = ''' select s.ts,
                             #o.stgpool_name ds,
       #round(sum(logical_bytes_arch)) value
  #from occupancy_snapshots_mv o,
       #( select max(s.snap_id) snap_id,
                #unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
           #from snapshots s
          #where s.completed = true
         #group by date_format(s.start_date,'%Y-%m-%d') ) s
 #where s.snap_id = o.snap_id
   #and (o.node_name like @nodefilter@ or o.node_name in @nodelist@)
   #and (o.domain_name like @domainfilter@ or o.domain_name in @domainlist@)
                    #group by o.stgpool_name, s.ts
                    #order by o.stgpool_name asc, s.ts; '''
	_query = '''
  select unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts,
         o.stgpool_name, o.value
    from snapshots s,
         ( select snap_id, stgpool_name,
                  round(sum(logical_bytes_arch)) value
             from occupancy_snapshots_mv
            where (node_name like @nodefilter@ or node_name in @nodelist@)
              and (domain_name like @domainfilter@ or domain_name in @domainlist@)
         group by snap_id, stgpool_name ) o
   where s.completed = true
     and s.snap_id = o.snap_id
group by date_format(s.start_date,'%Y-%m-%d'), stgpool_name
order by s.start_date;'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class TotalBackup(Grapher):
	_profile = 'TotalBackup'
	_title = 'Total Amount in Backup'
	_base = '1024'
	_textType = ['Current','%6.0lf %SB (current size)']
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			}
	#_query = ''' select s.ts,
                             #o.stgpool_name ds,
       #round(sum(logical_bytes_bkup)) value
  #from occupancy_snapshots_mv o,
       #( select max(s.snap_id) snap_id,
                #unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
           #from snapshots s
          #where s.completed = true
         #group by date_format(s.start_date,'%Y-%m-%d') ) s
 #where s.snap_id = o.snap_id
   #and (o.node_name like @nodefilter@ or o.node_name in @nodelist@)
   #and (o.domain_name like @domainfilter@ or o.domain_name in @domainlist@)
                    #group by o.stgpool_name, s.ts
                    #order by o.stgpool_name asc, s.ts; '''
	_query = '''
  select unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts,
         o.stgpool_name, o.value
    from snapshots s,
         ( select snap_id, stgpool_name,
                  round(sum(logical_bytes_bkup)) value
             from occupancy_snapshots_mv
            where (node_name like @nodefilter@ or node_name in @nodelist@)
              and (domain_name like @domainfilter@ or domain_name in @domainlist@)
         group by snap_id, stgpool_name ) o
   where s.completed = true
     and s.snap_id = o.snap_id
group by date_format(s.start_date,'%Y-%m-%d'), stgpool_name
order by s.start_date;'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class TotalBackupSimple(Grapher):
	_profile = 'TotalBackupSimple'
	_title = 'Total Amount in Backup'
	_base = '1024'
	#_textType = ['Current','%6.0lf %SB (size)']
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			}
	#_query = '''
#select s.ts,'Total Backup',
       #round(sum(logical_bytes_bkup)) value
  #from occupancy_snapshots_mv o,
       #( select max(s.snap_id) snap_id,
                #unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
           #from snapshots s
          #where s.completed = true
         #group by date_format(s.start_date,'%Y-%m-%d') ) s
 #where s.snap_id = o.snap_id
   #and (o.node_name like @nodefilter@ or o.node_name in @nodelist@)
   #and (o.domain_name like @domainfilter@ or o.domain_name in @domainlist@)
#group by s.ts
#order by s.ts;'''
	_query = '''
  select unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts,
         'Total Backup', o.value
    from snapshots s,
         ( select snap_id,
                  round(sum(logical_bytes_bkup)) value
             from occupancy_snapshots_mv
            where (node_name like @nodefilter@ or node_name in @nodelist@)
              and (domain_name like @domainfilter@ or domain_name in @domainlist@)
         group by snap_id ) o
   where s.completed = true
     and s.snap_id = o.snap_id
group by date_format(s.start_date,'%Y-%m-%d')
order by s.start_date;'''
	def postProcess(self, data):
		#return self.processMovingAverage(self.processInterpolation(data),days=60)
		return self.processWeightedMovingAverage(self.processInterpolation(data),span=30)
class StorageUtilization(Grapher):
	_profile = 'StorageUtilization'
	_params = {
			'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
			'stgpoollist': {'Hash':1,'EscapeList':1},
			}
	_title = 'Utilization History'
	_base = '1024'
	_upperLimit = '100'
	_graphType = 'LINE2'
	#_textType = ['PercentMax','%6.0lf %SB (size)\t\:','%6.0lf %SB (used)\t\:','%3.0lf%%']
	_query = ''' select s.ts,
                             v.stgpool_name ds,
                             100*sum(est_used_bytes)/
                             sum(est_capacity_bytes) val
                        from volumes_snapshots_summary_mv v,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = v.vol_snap_id
                         and (v.stgpool_name like @stgpoolfilter@ or v.stgpool_name in @stgpoollist@)
                    group by v.stgpool_name, s.ts; '''
	def postProcess(self, data):
		return self.processInterpolation(data)
class StorageAggregatedUtilization(Grapher):
	_profile = 'StorageAggregatedUtilization'
	_params = {
			'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
			'stgpoollist': {'Hash':1,'EscapeList':1},
			}
	_title = 'Utilization History'
	_base = '1024'
	_upperLimit = '100'
	_graphType = 'LINE2'
	#_textType = ['PercentMax','%6.0lf %SB (size)\t\:','%6.0lf %SB (used)\t\:','%3.0lf%%']
	_query = ''' select s.ts,
                             'Estimated Utilization' ds,
                             100*sum(est_used_bytes)/
                             sum(est_capacity_bytes) val
                        from volumes_snapshots_summary_mv v,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = v.vol_snap_id
                         and (v.stgpool_name like @stgpoolfilter@ or v.stgpool_name in @stgpoollist@)
                    group by s.ts; '''
	def postProcess(self, data):
		return self.processInterpolation(data)
class VolumeCountOld(Grapher):
	_profile = 'VolumeCount'
	_title = 'Volume Count History'
	_graphType = 'LINE2'
	_textType = ['Current','%5.0lf volume(s)']
	_params = {
				'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
				'stgpoollist': {'Hash':1,'EscapeList':1},
				}
	_query = ''' select s.ts,
                             v.stgpool_name ds,
                             count(1)
                        from volumes_snapshots_summary_mv v,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = v.vol_snap_id
                         and (v.stgpool_name like @stgpoolfilter@ or v.stgpool_name in @stgpoollist@)
                    group by v.stgpool_name, s.ts
                    order by v.stgpool_name, s.ts; '''
	def postProcess(self, data):
		return self.processInterpolation(data)
class VolumeCount(Grapher):
	_profile = 'VolumeCount'
	_title = 'Volume Count History'
	#_graphType = 'LINE2'
	_textType = ['Current','%5.0lf volume(s)']
	_params = {
				'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
				'stgpoollist': {'Hash':1,'EscapeList':1},
				}
	#_query = ''' select s.ts,
                             #concat(vs.access,'+',vs.status) ds,
                             #count(1)
                        #from volumes v, volumes_snapshots vs,
                             #( select max(s.snap_id) snap_id,
                                      #unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 #from snapshots s
                                #where s.completed = true
                             #group by date_format(s.start_date,'%Y-%m-%d') ) s
                       #where s.snap_id = vs.snap_id
                         #and v.volume_name = vs.volume_name
                         #and (v.stgpool_name like @stgpoolfilter@ or v.stgpool_name in @stgpoollist@)
                    #group by concat(vs.access,'+',vs.status), s.ts; '''
	_query = '''
  select unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts,
         v.volume_status, v.value
    from snapshots s,
         ( select snap_id,
                  volume_status,
                  sum(volume_count) value
             from volumes_snapshots_status_mv
            where (stgpool_name like @stgpoolfilter@ or stgpool_name in @stgpoollist@)
         group by snap_id, volume_status ) v
   where s.completed = true
     and s.snap_id = v.snap_id
group by date_format(s.start_date,'%Y-%m-%d'), v.volume_status
order by s.start_date;'''
	def postProcess(self, data):
		return self.processInterpolation(data)
class StoragePoolUsage(Grapher):
	_profile = 'StoragePoolUsage'
	_title = 'Usage History'
	#_graphType = 'LINE2'
	#_textType = ['Special1']
	#_textType = ['Current','%6.0lf %SB']
	_max = 'Estimated Capacity'
	_params = {
				'stgpoolfilter': {'Hash':1,'EscapeFilter':1},
				'stgpoollist': {'Hash':1,'EscapeList':1},
				}
	_query = '''
  select s.ts,
         'Estimated Used',
         sum(est_used_bytes) val,
         sum(est_capacity_bytes) max
    from volumes_snapshots_summary_mv,
         ( select max(s.snap_id) snap_id,
                  unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
             from snapshots s
            where s.completed = true
         group by date_format(s.start_date,'%Y-%m-%d') ) s
   where s.snap_id = vol_snap_id
     and (stgpool_name like @stgpoolfilter@ or stgpool_name in @stgpoollist@)
group by s.ts
   union all
  select s.ts,
         'Estimated Reclaimable',
         sum(est_reclaimable_bytes) val,
         sum(est_capacity_bytes) max
    from volumes_snapshots_summary_mv,
         ( select max(s.snap_id) snap_id,
                  unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
             from snapshots s
            where s.completed = true
         group by date_format(s.start_date,'%Y-%m-%d') ) s
   where s.snap_id = vol_snap_id
     and (stgpool_name like @stgpoolfilter@ or stgpool_name in @stgpoollist@)
group by s.ts'''
	def postProcess(self, data):
		return self.processInterpolation(data)
class SessionBackupDuration(Grapher):
	_profile = 'SessionBackupDuration'
	_graphType = 'LINE2'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'schedulefilter': {'Hash':1,'EscapeFilter':1},
		}
	_maxCap = 1.6
	_title = 'Backup Session Duration'
	_query = '''
                     select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                            'Duration in Minutes' ds,
                            avg(unix_timestamp(end_time)-unix_timestamp(start_time))/60 val
                       from summary s,
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
                      where activity='BACKUP'
                        and s.entity = n.node_name
                        and (@schedulefilter@ is null or
                             ifnull(schedule_name,'') like @schedulefilter@)
                   group by date_format(start_time,'%Y-%m-%d') '''

	def postProcess(self, data):
		return self.processWeightedMovingAverage(self.processInterpolation(data))

class SessionSuccessRate(Grapher):
	_profile = 'SessionSuccessRate'
	_graphType = 'LINE2'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'schedulefilter': {'Hash':1,'EscapeFilter':1},
		}
	_upperLimit = 100
	_title = 'Session Object Backup Success Rate'
	_query = '''
                     select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                            'Percent of Successful Objects' ds,
                            ifnull(avg(affected/(failed+affected)),1)*100 val
                       from summary s,
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
                      where activity='BACKUP'
                        and s.entity = n.node_name
                        and (@schedulefilter@ is null or
                             ifnull(schedule_name,'') like @schedulefilter@)
                   group by date_format(start_time,'%Y-%m-%d')
 '''

	def postProcess(self, data):
		return self.processInterpolation(data)


class SessionReclamationDuration(Grapher):
	_profile = 'SessionReclamationDuration'
	_graphType = 'LINE2'
	#_params = {
			#'nodefilter': {'Hash':1,'EscapeFilter':1},
			#'nodelist': {'Hash':1,'EscapeList':1},
			#'domainfilter': {'Hash':1,'EscapeFilter':1},
			#'domainlist': {'Hash':1,'EscapeList':1},
		#}
	_title = 'Reclamation Session Duration'
	_query = ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Duration in Minutes' ds,
                             avg(unix_timestamp(end_time)-unix_timestamp(start_time))/60 val
                        from summary s
                       where activity='RECLAMATION'
                    group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processMovingAverage(data)

class SessionExpirationDuration(Grapher):
	_profile = 'SessionExpirationDuration'
	_graphType = 'LINE2'
	#_params = {
			#'nodefilter': {'Hash':1,'EscapeFilter':1},
			#'nodelist': {'Hash':1,'EscapeList':1},
			#'domainfilter': {'Hash':1,'EscapeFilter':1},
			#'domainlist': {'Hash':1,'EscapeList':1},
		#}
	_title = 'Expiration Session Duration'
	_query = ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Duration in Minutes' ds,
                             avg(unix_timestamp(end_time)-unix_timestamp(start_time))/60 val
                        from summary s
                       where activity='EXPIRATION'
                    group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processMovingAverage(data)

class SessionActivity(Grapher):
	_resolution = 60
	_graphType = 'LINE1'
	def __init__(self,*arg,**keywords):
		if keywords.has_key('graphstart') and not keywords.has_key('start'):
			keywords['start'] = keywords['graphstart']
		if keywords.has_key('graphend') and not keywords.has_key('end'):
			keywords['end'] = keywords['graphend']
		
		assert keywords.has_key('start') and keywords.has_key('end')

		start = int(int(toRRDTime(keywords['start']))/86400)*86400
		keywords['graphstart'] = fromRRDTime(start)
		keywords['graphend'] = fromRRDTime(start+86400)

		keywords['start'] = fromRRDTime(keywords['start'])
		keywords['end'] = fromRRDTime(keywords['end'])

		keywords['title'] = 'for %s to %s' % (keywords['start'].date(),keywords['end'].date())

		Grapher.__init__(self,*arg,**keywords)

	def postProcess(self, data):
		if len(data) < 2: return data
		
		dataMap = DefaultDict(DefaultDict(0))
		
		dataStart = DefaultDict(DefaultDict(0))
		dataEnd = DefaultDict(DefaultDict(0))

		for ts,ds,val in data:
			val = float(val)
			dataMap[ds][ts] += val
			if val > 0:
				dataStart[ds][ts] = val
			elif val < 0:
				dataEnd[ds][ts] = val


		averageOnly = False
		sortKeys =  dataMap.keys()
		sortKeys.sort()
		if len(dataMap[sortKeys[-1]]) == 1: to = sortKeys.pop()
		else: to = sortKeys[-1]
		total = float(len(sortKeys))
		if total > 1:
			sortKeys.append(None)
			average = 'Average'
			

			if (total+1)>len(self.getColors()):
				averageOnly = True

				self._miscDsInfo[average]['graphType'] = 'LINE2'
				
				minmax = 'Max/Min'
				minmaxLow = 'mmL'

				self._miscDsInfo[minmax]['graphType'] = 'AREA'
				self._miscDsInfo[minmax]['graphOption'] = 'STACK'
				#self._miscDsInfo[minmax]['colorAlpha'] = '99'
	
				self._miscDsInfo[minmaxLow]['graphType'] = 'AREA'
				self._miscDsInfo[minmaxLow]['graphOption'] = ''
				self._miscDsInfo[minmaxLow]['colorAlpha'] = '00'
				self._miscDsInfo[minmaxLow]['hide'] = True

				stddev = 'Std Dev'
				stddevLow = 'sdL'

				self._miscDsInfo[stddev]['graphType'] = 'AREA'
				self._miscDsInfo[stddev]['graphOption'] = 'STACK'

				self._miscDsInfo[stddevLow]['graphType'] = 'AREA'
				self._miscDsInfo[stddevLow]['graphOption'] = ''
				self._miscDsInfo[stddevLow]['colorAlpha'] = '00'
				self._miscDsInfo[stddevLow]['hide'] = True

			else:
				self._miscDsInfo[average]['graphType'] = 'LINE3'
				self._miscDsInfo[average]['colorAlpha'] = 'AA'

		newData = []
		count = DefaultDict(0)
		start = int(toRRDTime(self.getKeyword('graphstart')))
		for key in sortKeys:
			if key != None:
				i = ''.join(key.split()[1:])
				startDs = '%s s' % key
				endDs = '%s e' % key

			for ts in range(0,86400,self._resolution):
				newTs = ts+start
				if key == None:
					history = dataMap['history'][ts]
					avgValue = sum(history)/total
					if averageOnly:
						minValue = min(history)
						maxValue = max(history)
						newData.append([newTs,minmaxLow,minValue])
						newData.append([newTs,minmax,maxValue-minValue])

						from math import sqrt
						#stdValue = 
						minValue = avgValue-sqrt(sum(map(lambda x: min(x-avgValue,0)**2,history))/total)
						maxValue = avgValue+sqrt(sum(map(lambda x: max(x-avgValue,0)**2,history))/total)
						newData.append([newTs,stddevLow,minValue])
						newData.append([newTs,stddev,maxValue-minValue])
					newData.append([newTs,average,avgValue])
				else:
					count[i] += dataMap[key][ts]
					if dataMap['history'][ts] == 0: dataMap['history'][ts] = []
					dataMap['history'][ts].append(count[i])

					if not averageOnly:
						newData.append([newTs,key,count[i]])

					#newData.append([newTs,startDs,dataStart[key][ts]])
					#newData.append([newTs,endDs,dataEnd[key][ts]])

			self._miscDsInfo[startDs]['hide'] = True
			self._miscDsInfo[startDs]['graphType'] = 'AREA'
			self._miscDsInfo[startDs]['colorLike'] = key

			self._miscDsInfo[endDs]['hide'] = True
			self._miscDsInfo[endDs]['graphType'] = 'AREA'
			self._miscDsInfo[endDs]['colorLike'] = key

		return newData

	def getNextColor(self,hashobj=None):
		if hashobj and type(hashobj) in (str,unicode):
			if hashobj[0] == 'M': return '#1E9DA3'
			elif hashobj[0] == 'S': return '#D5217A'
			elif hashobj[0] == 'A': return '#FEC724'
		return Grapher.getNextColor(self,hashobj)

class SessionActivityCount(SessionActivity):
	_profile = 'SessionActivityCount'
	_params = {
		'start': {'Hash':1,'Escape':1},
		'end': {'Hash':1,'Escape':1},
		'nodefilter': {'Hash':1,'EscapeFilter':1},
		'nodelist': {'Hash':1,'EscapeList':1},
		'domainfilter': {'Hash':1,'EscapeFilter':1},
		'domainlist': {'Hash':1,'EscapeList':1},
		'schedulefilter': {'Hash':1,'EscapeFilter':1},
	}
	_title = 'Running Backup Sessions'
	#_query = '''
        #select ts,ds,value
          #from (
          #select time_to_sec(date_format(greatest(start_time,@start@),'%H:%i:00')) ts,
#--                 date_format(greatest(start_time,@start@),'%Y-%m-%d') ds,
                 #concat(date_format(greatest(start_time,@start@),'%Y-%m-%d'),if(activity='BACKUP',' (backup)',' (other)')) ds,
                 #count(1) value
            #from summary use index(idx_start,idx_end)
           #where end_time >= @start@ and start_time <= @end@
#--             and activity='BACKUP'
        #group by ds,ts
        #union all
          #select time_to_sec(date_format(least(end_time,@end@),'%H:%i:00')) ts,
#--                 concat(date_format(least(end_time,@end@),'%Y-%m-%d') ds,
                 #concat(date_format(least(end_time,@end@),'%Y-%m-%d'),if(activity='BACKUP',' (backup)',' (other)')) ds,
                 #-count(1) value
            #from summary use index(idx_start,idx_end)
           #where end_time >= @start@ and start_time <= @end@
#--             and activity='BACKUP'
        #group by ds,ts ) u
        #order by ds,ts,value desc'''
	_query = '''
        select ts,ds,value
          from (
          select time_to_sec(date_format(greatest(start_time,@start@),'%H:%i:00')) ts,
                 date_format(greatest(start_time,@start@),'%Y-%m-%d') ds,
                 count(1) value
            from summary use index(idx_start,idx_end),
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
           where end_time >= @start@ and start_time <= @end@
             and activity='BACKUP'
             and entity = n.node_name
             and (@schedulefilter@ is null or ifnull(schedule_name,'') like @schedulefilter@)
        group by ds,ts
        union all
          select time_to_sec(date_format(least(end_time,@end@),'%H:%i:00')) ts,
                 date_format(least(end_time,@end@),'%Y-%m-%d') ds,
                 -count(1) value
            from summary use index(idx_start,idx_end),
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
           where end_time >= @start@ and start_time <= @end@
             and activity='BACKUP'
             and entity = n.node_name
             and (@schedulefilter@ is null or ifnull(schedule_name,'') like @schedulefilter@)
        group by ds,ts ) u
        order by ds,ts,value desc'''


class SessionActivityTXRate(SessionActivity):
	_profile = 'SessionActivityTXRate'
	_params = {
		'start': {'Hash':1,'Escape':1},
		'end': {'Hash':1,'Escape':1},
		'nodefilter': {'Hash':1,'EscapeFilter':1},
		'nodelist': {'Hash':1,'EscapeList':1},
		'domainfilter': {'Hash':1,'EscapeFilter':1},
		'domainlist': {'Hash':1,'EscapeList':1},
		'schedulefilter': {'Hash':1,'EscapeFilter':1},
	}
	_title = 'Backup Sessions Transfer Rate'
	_query = '''
        select ts,ds,value
          from (
          select time_to_sec(date_format(greatest(start_time,@start@),'%H:%i:00')) ts,
                 date_format(greatest(start_time,@start@),'%Y-%m-%d') ds,
                 sum(bytes/(0.5+unix_timestamp(end_time)-unix_timestamp(start_time))) value
            from summary use index(idx_start,idx_end),
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
           where end_time >= @start@ and start_time <= @end@
             and activity='BACKUP'
             and bytes
             and entity = n.node_name
             and (@schedulefilter@ is null or ifnull(schedule_name,'') like @schedulefilter@)
        group by ds,ts
        union all
          select time_to_sec(date_format(least(end_time,@end@),'%H:%i:00')) ts,
                 date_format(least(end_time,@end@),'%Y-%m-%d') ds,
                 -sum(bytes/(0.5+unix_timestamp(end_time)-unix_timestamp(start_time))) value
            from summary use index(idx_start,idx_end),
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
           where end_time >= @start@ and start_time <= @end@
             and activity='BACKUP'
             and bytes
             and entity = n.node_name
             and (@schedulefilter@ is null or ifnull(schedule_name,'') like @schedulefilter@)
        group by ds,ts ) u
        order by ds,ts,value desc'''

class SessionExpireDuration(Grapher):
	_profile = 'SessionDuration'
	_graphType = 'LINE2'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
		}
	_title = 'Average Session Duration'
	_query = ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Duration in Minutes' ds,
                             avg(unix_timestamp(end_time)-unix_timestamp(start_time))/60 val
                        from summary s, nodes n, nodes_snapshots ns
                       where activity='BACKUP'
                         and s.entity = n.node_name
                         and n.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and n.nodetype = 'CLIENT'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processMovingAverage(data)

class SessionBackupCount(Grapher):
	_profile = 'SessionCount'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'schedulefilter': {'Hash':1,'EscapeFilter':1},
		}
	_title = 'Daily Number of Backup Sessions'
	_graphType = 'LINE2'
	_query = '''
                     select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                            'Number of Sessions' ds,
                            count(1) val
                       from summary s,
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
                      where activity='BACKUP'
                        and s.entity = n.node_name
                        and (@schedulefilter@ is null or
                             ifnull(schedule_name,'') like @schedulefilter@)
                   group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processWeightedMovingAverage(self.processInterpolation(data,missingIsZero=True))

class TransferBackupSpeed(Grapher):
	_profile = 'TransferBackupSpeed'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'schedulefilter': {'Hash':1,'EscapeFilter':1},
		}
	_title = 'Average Backup Speed'
	_base = '1024'
	_graphType = 'LINE2'
	_query = ''' 
                     select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                            'Speed Bytes/Sec' ds,
                            sum(bytes)/
                            sum(unix_timestamp(end_time)-unix_timestamp(start_time)) val
                       from summary s,
                            ( select node_name
                                from nodes left join nodes_snapshots using (node_name,snap_id)
                               where nodetype = 'CLIENT'
                                 and (node_name like @nodefilter@ or node_name in @nodelist@)
                                 and (domain_name like @domainfilter@ or domain_name in @domainlist@) ) n
                      where activity='BACKUP'
                        and s.entity = n.node_name
                        and (@schedulefilter@ is null or
                             ifnull(schedule_name,'') like @schedulefilter@)
                   group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processMovingAverage(self.processInterpolation(data))

class TransferReclamationSpeed(Grapher):
	_profile = 'TransferReclamationSpeed'
	#_params = {
			#'nodefilter': {'Hash':1,'EscapeFilter':1},
			#'nodelist': {'Hash':1,'EscapeList':1},
			#'domainfilter': {'Hash':1,'EscapeFilter':1},
			#'domainlist': {'Hash':1,'EscapeList':1},
		#}
	_title = 'Average Reclamation Speed'
	_base = '1024'
	_graphType = 'LINE2'
	_query = ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Speed Bytes/Sec' ds,
                             sum(bytes)/
                             sum(unix_timestamp(end_time)-unix_timestamp(start_time)) val
                        from summary s
                       where activity='RECLAMATION'
                    group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processMovingAverage(data)

class TransferExpirationSpeed(Grapher):
	_profile = 'TransferExpirationSpeed'
	#_params = {
			#'nodefilter': {'Hash':1,'EscapeFilter':1},
			#'nodelist': {'Hash':1,'EscapeList':1},
			#'domainfilter': {'Hash':1,'EscapeFilter':1},
			#'domainlist': {'Hash':1,'EscapeList':1},
		#}
	_title = 'Average Expiration Speed'
	_base = '1024'
	_graphType = 'LINE2'
	_query = ''' select unix_timestamp(date_format(max(start_time),'%Y-%m-%d')) ts,
                             'Speed Objects/Sec' ds,
                             sum(examined)/
                             sum(unix_timestamp(end_time)-unix_timestamp(start_time)) val
                        from summary s
                       where activity='EXPIRATION'
                    group by date_format(start_time,'%Y-%m-%d') '''
	def postProcess(self, data):
		return self.processMovingAverage(data)

class Filespaces(Grapher):
	_profile = 'Filespaces'
	_title = 'Filespaces Utilization'
	_upperLimit = '100'
	_graphType = 'LINE2'
	_base = '1024'
	_params = { 'node': {'Hash':1,'Escape':1} }
	_textType = ['PercentMax','%6.0lf %SB (size)\t\:','%6.0lf %SB (used)\t\:','%3.0lf%%']

	_query = ''' select s.ts,
                             concat( f.filespace_name, ' (', f.filespace_id, ')') name,
                             fs.pct_util value,
                             fs.capacity*1024*1024 max
                        from filespaces_mv f, filespaces_snapshots fs,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = fs.snap_id
                         and f.filespace_id = fs.filespace_id
                         and f.node_name = fs.node_name
                         and not f.virtual_fs = 1
                         and f.node_name = @node@
                    order by ts'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class FilespacesStorage(Grapher):
	_profile = 'FilespacesStorage'
	_title = 'Filespaces in Storage'
	#_upperLimit = '100'
	#_graphType = 'LINE2'
	_base = '1024'
	_params = { 'node': {'Hash':1,'Escape':1} }
	#_textType = ['PercentMax','%6.0lf %SB (size)\t\:','%6.0lf %SB (used)\t\:','%3.0lf%%']

	_query = ''' select s.ts,
                             concat( f.filespace_name, ' (', f.filespace_id, ')') name,
                             round(sum(o.logical_mb) * 1024 * 1024) value
                        from occupancy_snapshots o, filespaces f,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = o.snap_id
                         and f.filespace_id = o.filespace_id
                         and f.node_name = o.node_name
                         and f.node_name = @node@
                    group by f.filespace_id, s.ts;'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class FilespacesAggregatedStorage(Grapher):
	_profile = 'FilespacesAggregatedStorage'
	_title = 'Filespace Storage Usage'
	_base = '1024'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'fsid': {'Hash':1,'Escape':1,'Default':None},
		}
	_query = ''' select s.ts,
                             if( o.type = 'Bkup', 'In Backup', 'In Archive' ) ds,
                             round(sum(o.logical_mb) * 1024 * 1024) value
                        from occupancy_snapshots o,
                             nodes n, nodes_snapshots ns,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = o.snap_id
                         and o.node_name = n.node_name
                         and o.node_name = ns.node_name
                         and n.snap_id = ns.snap_id
                         and o.logical_mb > 0
                         and o.type in ('Bkup','Arch')
                         and (@fsid@ is null or o.filespace_id = @fsid@)
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by o.type, s.ts;'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class FilespacesAggregated(Grapher):
	"Displays a number of filespaces as if it were one"
	_profile = 'FilespacesAggregated'
	_title = 'Filespaces Utilization'
	#_upperLimit = '100'
	#_graphType = 'AREA'
	#_heartBeat = 10
	_base = '1024'
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			'fsid': {'Hash':1,'Escape':1,'Default':None},
		}
	_query = ''' select s.ts,
                             'Used' name,
                             sum(fs.capacity*pct_util/100)*1024*1024 value,
                             sum(fs.capacity)*1024*1024 max
                        from nodes_snapshots ns, filespaces_snapshots fs,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = fs.snap_id
                         and s.snap_id = ns.snap_id
                         and ns.node_name = fs.node_name
                         and (@fsid@ is null or fs.filespace_id = @fsid@)
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by s.ts'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class LocalWork(Grapher):
	# Just tmp. Throw me away
	_heartBeat = 7
	_profile = 'LocalWork'
	_title = 'Work per day'
	_graphType = 'LINE2'
	_params = { 'nodefilter': {'Hash':1,'Escape':1} }
	_query = ''' select starttime date, 'Work per day', sum(duration/3600) work from work where job_id = 17 group by date_format(  from_unixtime(starttime), '%Y-%m-%d') order by starttime '''
	def __init__(self,*arg,**keywords):
		Grapher.__init__(self,*arg,**keywords)

class LocalDatabaseSize(Grapher):
	_profile = 'LocalDatabaseSize'
	_title = 'Local Database Size'
	_graphType = 'LINE2'
	_base = '1024'
	_params = { 'nodefilter': {'Hash':1,'Escape':1} }
	_query = ''' select unix_timestamp(start_date) ts, 'Size in Bytes',size
                 from local_db, snapshots
                 where local_db.snap_id = snapshots.snap_id order by start_date'''
	def postProcess(self, data):
		return self.processInterpolation(data)

class CollectorVersion(Grapher):
	_profile = 'CollectorVersion'
	_title = 'Collector Version History'
	_graphType = 'LINE2'
	_base = '1024'
	_params = { 'nodefilter': {'Hash':1,'Escape':1} }
	_query = ''' select unix_timestamp(start_date) ts, 'Version Revision Number',version
                 from local_db, snapshots
                 where local_db.snap_id = snapshots.snap_id order by start_date '''
	def postProcess(self, data):
		return self.processInterpolation(data)

class ActlogGraph(Grapher):
	_profile = 'ActlogGraph'
	_title = 'Actlog'
	_base = '1000'
	_query = ''' select ts, ds, val
                 from actlog_graph_mv;'''

class TSMDatabaseSize(Grapher):
	_profile = 'TSMDatabaseSize'
	_title = 'TSM Database Size'
	#_upperLimit = '100'
	_base = '1024'
	#_graphType = 'AREA'
	_max = 'Max Capacity'
	_params = { 'nodefilter': {'Hash':1,'Escape':1} }
	_query = ''' select ts,'Database Size',
                 pct_utilized*avail_space_mb*1024*1024/100 size,
                 avail_space_mb*1024*1024 max
                 from db,    ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                 where db.snap_id = s.snap_id order by ts

       			'''
	def postProcess(self, data):
		return self.processInterpolation(data)
	#def postProcess(self, data):
		#return self.processMovingAverage(data,days=60)
class TSMLogSize(Grapher):
	_profile = 'TSMLogSize'
	_title = 'TSM Log Size'
	_upperLimit = '100'
	_graphType = 'LINE2'
	_params = { 'nodefilter': {'Hash':1,'Escape':1} }
	_query = ''' select ts, 'Percent Utilized',pct_utilized
                 from log,    ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                 where log.snap_id = s.snap_id order by ts
       			'''
	def postProcess(self, data):
		#return self.processMovingAverage(self.processInterpolation(data),days=7)
		return self.processWeightedMovingAverage(self.processInterpolation(data),span=7)
class NodeCount(Grapher):
	_profile = 'NodeCount'
	_title = 'Number of Nodes'
	_graphType = 'LINE2'
	_textType = ['Current','%3.0lf node(s)']
	
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			}
	_query = ''' select ts,
                             ifnull(n.platform_name, 'Unknown') ds,
                             count(1)
                        from nodes_snapshots ns, nodes n,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = ns.snap_id
                         and ns.node_name = n.node_name
                         and n.nodetype = 'CLIENT'
                         and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                         and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by n.platform_name, s.ts
                    order by ifnull(n.platform_name, 'ZZZ') asc, s.ts; '''
	def postProcess(self, data):
		data = self.processInterpolation(data)
		''' Read it and cry '''
		
		"""((0,'Linux',20)
		 (1,'Linux',20)
		 (2,'Linux',20),
		 (0,'AIX',1),
		 (1,'AIX',1),
		 (2,'AIX',1),
		 (0,'Windows',15)
		 (1,'Windows',15)
		 (3,'Windows',15))

		((0,'Linux',20)
		 (1,'Linux',20)
		 (2,'Linux',20),
		 (0,'Other',16),
		 (1,'Other',16),
		 (2,'Other',16))
		
		Linux: [(0,20),(1,20),(2,20)]
		Windows: [(0,15),(1,15),(2,15)]
		AIX: [(0,1),(1,1),(2,1)]"""

		datasources = DefaultDict( [] )
		oscount = {}
		for ts,os,val in data:
			datasources[os].append((ts,val))
			oscount[os] = val
		osList = oscount.keys()
		osList.sort(key=lambda x: oscount[x])
		osList.reverse()

		osmap = {}
		for os in osList[:5]:
			osmap[os] = os
		for os in osList[5:]:
			osmap[os] = 'Other'

		dictOs = DefaultDict( DefaultDict( 0 ) )
		for os in osList:
			for ts,val in datasources[os]:
				dictOs[osmap[os]][ts] += val
		data = []
		for os in osList + ['Other']:
			dictTimestamp = dictOs[os]
			for timestamp, val in dictTimestamp.items():
				data.append([timestamp,os,val])

		# TODO rewrite
		data.sort(key=lambda x: x[0])

		"""Linux: [(0,20),(1,20),(2,20)]
		Other: [(0,17),(1,17),(2,17)]
		
		((0,'Linux',20)
		 (1,'Linux',20)
		 (2,'Linux',20),
		 (0,'Other',16),
		 (1,'Other',16),
		 (2,'Other',16))"""

		return Grapher.postProcess(self, data)

class DomainNodeCount(Grapher):
	_profile = 'DomainNodeCount'
	_title = 'Number of Nodes per Domain'
	_graphType = 'LINE2'
	_textType = ['Current','%3.0lf node(s)']
	
	_params = {
			'nodefilter': {'Hash':1,'EscapeFilter':1},
			'nodelist': {'Hash':1,'EscapeList':1},
			'domainfilter': {'Hash':1,'EscapeFilter':1},
			'domainlist': {'Hash':1,'EscapeList':1},
			}
	_query = ''' select ts,
                             ns.domain_name ds,
                             count(1)
                        from nodes_snapshots ns, nodes n,
                             ( select max(s.snap_id) snap_id,
                                      unix_timestamp(date_format(max(s.start_date),'%Y-%m-%d')) ts
                                 from snapshots s
                                where s.completed = true
                             group by date_format(s.start_date,'%Y-%m-%d') ) s
                       where s.snap_id = ns.snap_id
                         and ns.node_name = n.node_name
                         and n.nodetype = 'CLIENT'
                          and (ns.node_name like @nodefilter@ or ns.node_name in @nodelist@)
                          and (ns.domain_name like @domainfilter@ or ns.domain_name in @domainlist@)
                    group by ns.domain_name, s.ts
                    order by s.ts;'''

def main():
	l = Logger()
	
	l.start("Begin Grapher Self Test")

	db = datasource.MySQLDataSource(l,host='statmon.basis.is')
	rest = {
		'domainfilter' : '*',
		'nodefilter' : '*',
		#'nodelist' : None,
		#'domainlist' : None,
		#'node' : 'BLADE2.HUGSMIDJAN.IS',
		'path' : '',
		'datapath' : '/tmp/',
		'imagepath' : '/tmp/',
		'db' : db,
		'logger' : l,
		'update' : False,
		'graph' : True,
		'maxage' : 10,
		'imagewidth' : 400,
		'imageheight' : 150,
		#'graphstart' : datetime.datetime(2007, 7, 13, 0, 0),
		'maxage' : 1,
	}

	for key,value in {'domainfilter': '*',
	#'start' : '2008-09-11',
	#'end' : '2008-09-30',
	#'graph' : False,
	'domainlist': None,
	#'graphstart': datetime.datetime(2008, 9, 17, 0, 0),
	#'graphend': datetime.datetime(2008, 10, 06, 0, 0),
	'end' : '1223251200',
	'start' : '1221609600',
	'imagewidth': '1100',
	#'node': u'GR8POKER.COM',
	#'nodefilter': 'GR8POKER.COM',
	#'nodelist': [u'GR8POKER.COM'],
	#'schedule': 'DAGLEGT_03_05',
	'schedulefilter' : '?*',
	'stgpoolfilter': '*',
	'stgpoollist': ['DBOCK_DUP']}.items(): rest[key] = value

	#{'nodefilter': '%', 'node': None, 'domainfilter': '%', 'nodelist': None, 'stgpoollist': None, 'domainlist': None, 'schedule': '', 'graphend': datetime.datetime(2008, 10, 6, 0, 0), 'graphstart': datetime.datetime(2008, 9, 17, 0, 0), 'imagewidth': 700, 'stgpoolfilter': None} 


	#profile = 'NodeFilespaces'
	#g = Grapher(profile = profile, **rest)

	#profile = 'NodesCount'
	#g = Grapher(profile=profile, **rest)

	#profile = 'NodeSessionDuration'
	#g = Grapher(profile=profile, **rest)

	#profile = 'NodeSessionCount'
	g = SessionActivityTXRate(**rest)

	#print g.getParams()
	#g = SessionActivity
	#import cPickle
	#cPickle.dumps(g.getParams())

	l.end()

if __name__ == '__main__': main( )
