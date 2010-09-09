
# ...

# 1 get data

# ???

# 3 provide data interface

if __name__ == '__main__':
	from sys import path, argv
	import os

	p = os.path.abspath(os.path.dirname(os.curdir+'/'+argv[0]).replace('/core',''))
	path.append(p)

	p = os.path.abspath(p+'/../../ext/')
	path.append(p)

import statmon.datasource

from utils import Logger,NullLogger,DefaultDict

import QuantLib

import time
import datetime

# queries

# simple:		ts, data
# multi col:	ts, data1, data2, data3
# named data:	ts, name, data
# mixed:		ts, name, data1, data2
# mixed comp:	ts, name1, data1, data2, name2, data3, data4
# unique/desc:	ts, unique, desc, val

# sort order?

# interpolation factor?
# e.g. how far from nearest data (bottom/top)

# real data points/samples

#            name
#           /    \
#       unique   desc

#           common name
#            /   |   \  `  ...
#          min  val  max  other1 ... othern

#     streamline operations
#       /   |   \   ` ...
#    min   avg   max  mdev ... othern

# multi queries?

class DataFetcher:
	_queries = [ '''select now() ts, 0 val, 5 uid, 'name' name;''' ]
	_datasets = [
		{	'ds':'test',
			'ts':0,
			'val':1, # type??
			'uid':2,
			'name':3,
		}
	]

	def __init__(self,db,logger=NullLogger()):
		self._empty = True
		self._l = logger
		self._dataValues = DefaultDict(DefaultDict({}))
		self._dataTimes = DefaultDict(None)
		self._dataAttributes = DefaultDict(DefaultDict(0))
		self._interdata = DefaultDict({})
		self._resolution = {}

		count, data = self._getData(db)
		if count:
			self._parseData(data)
			if self.getDatasets(): self._empty = False

	def _getQuery(self):
		return self._queries[0]

	def _getData(self,db):
		return db.query(self._getQuery())

	def _parseData(self,data):
		col2ds = DefaultDict([])
		for ds in self._datasets:
			for name,col in ds.items():
				if type(col) == int and name not in ('ts','uid'):
					col2ds[col].append((ds,ds.get('ts'),ds.get('uid',None),name))

		for row in data:
			for col in col2ds.keys():
				for ds,ts,uid,name in col2ds[col]:
					ts = row[ts]
					key = ds['ds']
					if uid: key += '_%s' % row[uid]
					value = row[col]

					dataset = self._dataValues[key]
					dataset[ts][name] = value
					self._dataAttributes[key][name] += 1

					superset = self._dataValues[None]
					if superset[ts].has_key(name): superset[ts][name].append(value)
					else: superset[ts][name] = [value]
					self._dataAttributes[None][name] += 1

		for ds in self._dataValues.keys():
			timestamps = self._dataValues[ds].keys()
			timestamps.sort()
			self._dataTimes[ds] = timestamps

	def __preProcess(self,dataset=None,attribute=None,listop=sum):
		dataValues = self._dataValues[dataset]
		dataTimes = self._dataTimes[dataset]

		if type(dataValues[dataTimes[0]][attribute]) == list:
			fetch = lambda x: float(listop(dataValues[x][attribute]))
		else: 
			fetch = lambda x: float(dataValues[x][attribute])
		
		if type(dataTimes[0]) ==  datetime.datetime:
			convert = lambda x: time.mktime(x.timetuple())
		else:
			convert = lambda x: float(x)

		xArray = map(convert,dataTimes)
		yArray = map(fetch,dataTimes)

		return xArray,yArray
	
	def __postProcess(self,dataset=None,attribute=None,listop=sum,accuracy=7,falloff=1):
		xArray,yArray = self.__preProcess(dataset=dataset,attribute=attribute,listop=listop)
		
		res = self.getResolution(dataset=dataset)

		convert = lambda x: x
		if type(res) == datetime.timedelta:
			convert = lambda x: x.days * 86400 + x.seconds + x.microseconds / 1000000.0
		
		invRes = 1.0/convert(res)
		sqrtFalloff = falloff**.5
		weightCurve = lambda x1, x2: sqrtFalloff/(falloff+((x2-x1)*invRes)**2)*.5

		# calculate central moving average/stddev using normal like curve: (1+a)/sqrt(deltasteps^2+a)
		maArray = [] # moving average
		msArray = [] # moving standard deviation
		for i in range(len(xArray)):
			start = max(0,i-accuracy)
			end = min(i+accuracy+1,len(xArray))

			ySlice = []
			for j in range(start,end):
				weight = weightCurve(xArray[i],xArray[j])
				ySlice.append((yArray[j],weight))
			total = sum(map(lambda x: x[1], ySlice))
			ma = sum(map(lambda x: x[0]*x[1], ySlice))/total
			maArray.append(ma)

			ms = (sum(map(lambda x: (ma-x[0])**2*x[1], ySlice))/total)**.5
			msArray.append(ms)

		return xArray, yArray, maArray, msArray

	def __getPolator(self,linear=True):
		if linear:
			return QuantLib.LinearInterpolation
		return QuantLib.MonotonicCubicSpline

	def __getAverageSpacing(self,array,numerator=1,denominator=7):
		l = len(array)
		if l < 2:
			return None

		deltas = []
		for i in range(l)[1:]:
			deltas.append(array[i]-array[i-1])
		deltas.sort()

		assert(numerator*2<denominator)
		skip = numerator*l/denominator

		return sum(deltas[skip:l-skip-1],deltas[skip])/(l-skip*2)

	#def __time2Float(self,ts):
		#if type(ts) == datetime:
			#ts.

	def getResolution(self,dataset=None):
		if self._empty: return None
		if not self._resolution.has_key(dataset):
			assert(self._dataTimes.has_key(dataset))

			space = self.__getAverageSpacing(self._dataTimes[dataset])
			if type(space) == datetime.timedelta:
				space = space.days * 86400 + space.seconds + space.microseconds / 1000000.0

			days = space / 86400.0
			hours = space / 3600.0
			minutes = space / 60.0
			resolution = datetime.timedelta(seconds=round(space))
			if days > .8:
				resolution = datetime.timedelta(days=round(days))
			elif hours > .8:
				resolution = datetime.timedelta(seconds=round(hours)*3600)
			elif minutes > .8:
				resolution = datetime.timedelta(seconds=round(minutes)*60)

			self._resolution[dataset] = resolution

		return self._resolution[dataset]

	def getAverageOffset(self,dataset=None):
		# sum(ts%resolution)/count
		# ath, mdev?
		pass

	def getDatasets(self):
		return self._dataValues.keys()

	def getAttributes(self,dataset=None):
		assert(self._dataAttributes.has_key(dataset))
		return self._dataAttributes[dataset].keys()

	def getValue(self,ts,dataset=None,attribute=None,op='ma',listop=sum,linear=None):
		if self._empty: return None
		key = dataset
		if not dataset: key = listop
		else: assert(self._dataTimes.has_key(dataset))
	
		if attribute == None:
			attributes = self.getAttributes(dataset)
			assert(len(attributes)==1)
			attribute = attributes[0]

		if op and linear == None:
			linear = False
		if not op:
			op = 'y'
		polatorKey = (op,linear)

		if not self._interdata.has_key(key):
			xArray,yArray,maArray,msArray = self.__postProcess(dataset=dataset,attribute=attribute,listop=listop)
			self._interdata[key]['y'] = (xArray,yArray)
			self._interdata[key]['ma'] = (xArray,maArray)
			self._interdata[key]['ms'] = (xArray,msArray)
		
		assert(self._interdata[key].has_key(op))
		
		if not self._interdata[key].has_key(polatorKey):
			polator = self.__getPolator(linear)
			self._interdata[key][polatorKey] = polator(*self._interdata[key][op])

		return self._interdata[key][polatorKey](time.mktime(ts.timetuple()),True)

	def getMinTime(self,dataset=None):
		if self._empty: return None
		assert(self._dataTimes.has_key(dataset))
		return self._dataTimes[dataset][0]

	def getMaxTime(self,dataset=None):
		if self._empty: return None
		assert(self._dataTimes.has_key(dataset))
		return self._dataTimes[dataset][-1]

	#def getValues(self,startTime,endTime):
		#pass

class TestA(DataFetcher):
	_queries = [ '''-- daily backup
     select from_unixtime(avg(unix_timestamp(end_time))) ts, sum(bytes) val
       from summary s, nodes n, nodes_snapshots ns
      where activity='BACKUP'
        and s.entity = n.node_name
        and n.node_name = ns.node_name
        and n.snap_id = ns.snap_id
        and n.nodetype = 'CLIENT'
   group by date_format(end_time,'%Y-%m-%d');''' ]
	_datasets = [
		{	'ds':'dailybackup',
			'ts':0,
			'val':1,
			#'uid':2,
			#'name':3,
		}
	]

def dump(obj=test,it=None,ds=None):
	start = obj.getMinTime()
	end = obj.getMaxTime()
	if it:
		diff = (end-start)/it
	else:
		diff = test.getResolution()
	while start <= end:
		print start.isoformat(), obj.getValue(start,dataset=ds)
		start += diff

def main():
	global test
	#count, data = self.db.query(query)
	l = Logger()
	
	l.start("Begin DataFetcher Self Test")

	db = statmon.datasource.MySQLDataSource(l,host='statmon.basis.is')

	test = TestA(db=db)
	#test = DataFetcher(db=db,logger=l)
	#l.show(test.getDatasets())

	l.end()

if __name__ == '__main__': main( )