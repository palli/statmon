
from core.environment import logger

import datasource

# exception pass-through
from datasource import NoSuchTable, DuplicateEntry

from core.utils import *
import re
import copy

_db = None
def getDB():
	global _db
	
	if not _db:
		_db = datasource.MySQLDataSource(logger=logger)
	return _db

def setDB(db):
	global _db
	
	_db = db

def getNodes(nodefilter=None,nodelist=None,domainfilter=None,domainlist=None,
	contactfilter=None,contactlist=[],orderby=None,invert=False,invertNodelist=False,fields=None,countOnly=False):

	where = []
	if nodefilter:
		where.append( 'node_name like %s' % getDB().escapeFilter(nodefilter) )
	if nodelist != None:
		where.append( 'node_name in %s' % getDB().escapeList(nodelist) )
		if invertNodelist:
			where[-1] = 'not ' + where[-1]
	if domainfilter:
		where.append( 'domain_name like %s' % getDB().escapeFilter(domainfilter) )
	if domainlist != None:
		where.append( 'domain_name in %s' % getDB().escapeList(domainlist) )
	if contactfilter:
		where.append( 'contact like %s' % getDB().escapeFilter(contactfilter) )
	if contactlist:
		where.append( 'contact in %s' % getDB().escapeList(contactlist) )

	if countOnly:
		orderby = None
		fields = {
			'count':'count(1)'
		}
		return __getData('nodes_mv',where=where,orderby=orderby,invert=invert,fields=fields)[0].count

	return __getData('nodes_mv',where=where,orderby=orderby,invert=invert,fields=fields)

def getVolumes(): return __getData('volumes')

def getDomains(domainfilter=None,domainlist=[],orderby=None,countOnly=False):
	where = []
	if domainfilter:
		where.append( 'domain_name like %s' % getDB().escapeFilter(domainfilter) )
	if domainlist:
		where.append( 'domain_name in %s' % getDB().escapeList(domainlist) )

	if countOnly:
		orderby = None
		fields = {
			'count':'count(1)'
		}
		return __getData('domains_mv',where=where,orderby=orderby,fields=fields)[0].count

	return __getData('domains_mv',where=where,orderby=orderby)

def getSummary(end_start_time=None,start_time=None,start_end_time=None,
	end_time=None,entityfilter=None,entitylist=None,activity=None,schedulefilter=None,
	minDuration=0,orderby='start_time',limit=None,countOnly=False):

	where = []
	if end_start_time:
		where.append( 'end_time >= %s'% getDB().escape(str(end_start_time)) )
	if start_time:
		where.append( 'start_time >= %s'% getDB().escape(str(start_time)) )
	if start_end_time:
		where.append( 'start_time <= %s'% getDB().escape(str(start_end_time)) )
	if end_time:
		where.append( 'end_time <= %s'% getDB().escape(str(end_time)) )
	if entityfilter:
		where.append( 'entity like %s '% getDB().escapeFilter(entityfilter) )
	if entitylist != None:
		where.append( 'entity in %s '% getDB().escapeList(entitylist) )
	if activity:
		where.append( 'activity = %s '% getDB().escape(activity) )
	if schedulefilter:
		where.append( 'schedule_name like %s '% getDB().escapeFilter(schedulefilter) )
	if minDuration and not countOnly:
		where.append( 'unix_timestamp(end_time)-unix_timestamp(start_time) >= %d '% minDuration )
	if limit and not countOnly:
		orderby += ' limit %d' % limit

	fields = None
	groupby = None
	if countOnly:
		orderby = None
		groupby = """date_format(start_time, '%Y-%m-%d'), date_format(end_time, '%Y-%m-%d')"""
		fields = {
			'count_all':'count(1)',
			'count_duration':'sum(if(unix_timestamp(end_time)-unix_timestamp(start_time) >= %d,1,0))'% minDuration,
			'start_time':'min(start_time)',
			'end_time':'max(end_time)',
		}
	return __getData('summary',where=where,orderby=orderby,groupby=groupby,fields=fields)


def getSummaryStatistics(end_start_time=None,start_time=None,start_end_time=None,
	end_time=None,entityfilter=None,entitylist=None,activity=None,schedulefilter=None,
	orderby=None,groupby='entity'):

	where = []
	if end_start_time:
		where.append( 'end_time >= %s'% getDB().escape(str(end_start_time)) )
	if start_time:
		where.append( 'start_time >= %s'% getDB().escape(str(start_time)) )
	if start_end_time:
		where.append( 'start_time <= %s'% getDB().escape(str(start_end_time)) )
	if end_time:
		where.append( 'end_time <= %s'% getDB().escape(str(end_time)) )
	if entityfilter:
		where.append( 'entity like %s '% getDB().escapeFilter(entityfilter) )
	if entitylist != None:
		where.append( 'entity in %s '% getDB().escapeList(entitylist) )
	if activity:
		where.append( 'activity = %s '% getDB().escape(activity) )
	if schedulefilter != None:
		where.append( 'ifnull(schedule_name,"") like %s '% getDB().escapeFilter(schedulefilter) )

	fields = {
		'entity' :			'entity',
		'successful' :		'sum(if(successful = "YES",1,0))',
		'unsuccessful' :	'sum(if(successful = "NO",1,0))',
		'avg_transfer' :	'avg(bytes)',
		'max_transfer' :	'max(bytes)',
		'sum_transfer' :	'sum(bytes)',
		'avg_duration' :	'sec_to_time(avg(unix_timestamp(end_time)-unix_timestamp(start_time)))',
		'max_duration' :	'sec_to_time(max(unix_timestamp(end_time)-unix_timestamp(start_time)))',
		'sum_duration' :	'sec_to_time(sum(unix_timestamp(end_time)-unix_timestamp(start_time)))',
		'avg_examined' :	'avg(examined)',
		'max_examined' :	'max(examined)',
		'sum_examined' :	'sum(examined)',
		'avg_affected' :	'avg(affected)',
		'max_affected' :	'max(affected)',
		'sum_affected' :	'sum(affected)',
		'avg_failed' :		'avg(failed)',
		'max_failed' :		'max(failed)',
		'sum_failed' :		'sum(failed)', 
		'avg_successp' :	'avg(affected/(failed+affected))*100',
		'max_successp' :	'(1-min(failed/(failed+affected)))*100',
	}
	return __getData('summary',where=where,orderby=orderby,groupby=groupby,fields=fields)

def getSummaryActivities():
	'''Returns distinct list of possible activities'''
	return __getData('summary_activities_mv')
	
def getSnapshots(orderby=None): return __getData('snapshots',orderby=orderby)
def getLocalDB(): return __getData('local_db')
def getFailedFiles(start_date,countOnly=False):
	fields = None
	if countOnly:
		fields = {'count' : 'count(1)'}
		return __getData('actlog_failed_files_mv',fields=fields,where="date_time>'%s'"%start_date)[0].count
	return __getData('actlog_failed_files_mv',fields=fields,where="date_time>'%s'"%start_date,optimize_performance=True)
def getFilespaces(nodefilter=None,domainfilter=None,domainlist=[],nodelist=[],node_name=None,orderby=None):
	if node_name:
		return __getData('filespaces_mv', where="node_name='%s'"%node_name,orderby=orderby)
	where = []
	if nodefilter:
		where.append( 'node_name like %s' % getDB().escapeFilter(nodefilter) )
	if nodelist:
		where.append( 'node_name in %s' % getDB().escapeList(domainlist) )
	if domainfilter:
		where.append( 'domain_name like %s' % getDB().escapeFilter(domainfilter) )
	if domainlist:
		where.append( 'domain_name in %s' % getDB().escapeList(domainlist) )

	return __getData('filespaces_mv',where=where,orderby=orderby)
def getAlertStoragepools():
	return __getData('alert_stgpools_view')
def getStoragepools(stgpoolfilter='*',stgpoollist=[],orderby=None):
		where = '''(stgpool_name like %s or stgpool_name in %s)''' % (
				getDB().escapeFilter(stgpoolfilter),
				getDB().escapeList(stgpoollist))
		return __getData('stgpools_mv',where=where,orderby=orderby)
def getActlog(message=None,nodefilter=None,msgno=None,
		start=None,end=None,orderby=None,messageCutLength=None,countOnly=False):
	where = '1=1 '
	if message: where+= " and message like %s" % getDB().escapeFilter( message )
	if msgno: where+= " and msgno = %s"% getDB().escapeFilter( msgno )
	if nodefilter:
		where+= " and ( nodename like %s"% getDB().escapeFilter( nodefilter )
		where+= "       or (nodename is null and message like %s ) )" % getDB().escapeFilter( '* %s *' % nodefilter )
	if start: where+= " and date_time>=%s"% getDB().escape( str(start) )
	if end: where+= " and date_time<=%s"% getDB().escape( str(end) )

	fields = {}
	override = {}
	if not countOnly:
		orderby += " limit 1000"
		if messageCutLength:
			override['message'] = '''if(length(message)>%d,concat(left(message,%d),
				' ...'),message)''' % (messageCutLength,messageCutLength-4)
	else:
		orderby=None
		fields['count'] = 'count(1)'

	actlog = __getData('actlog',where=where,optimize_performance=True,
		orderby=orderby,fields=fields,overrideFields=override)
	if countOnly: return actlog[0]['count']
	return actlog
def getOccupancy(stgpool=None,orderby=None):
	where=None
	if stgpool:
		where='stgpool_name = %s' % getDB().escape(stgpool)
	return __getData('occupancy_mv',where=where,orderby=orderby)
def getBackupHistory(start=0):
	dbResult = __getData('actlog_backup_history_mv',where="date_time > '%s'"%start,optimize_performance=True)
	finalResult = []
	for i in dbResult:
		# TODO: Refactor this code to collector
		expr = ''
		if i['msgno'] == 2579:
			''' ANR2579E Schedule DAGLEGT_03_05 in domain CUSTOMERS for node EXCHANGE.HUGSANDIMENN.IS failed (return code 12). (SESSION: 68105) '''
			expr = r'ANR2579E Schedule .* in domain .* for node (.*) failed.*'
			#split = i['message'].split()
			#i['nodename'] = split[8]
			#i['domainname'] = split[5]
		elif i['msgno'] == 2578:
			'''ANR2578W Schedule DAGLEGT_22_07 in domain LSH for node VALUESAP.SIMI.IS has missed its scheduled start up window.'''
			expr = r'ANR2578. Schedule .* in domain .* for node (.*) has missed its .*'
		elif i['msgno'] == 2507:
			''' ANR2507I Schedule DAGLEGT_03_05 for domain CUSTOMERS started at 04/03/2007 03:00:00 AM for node VIPER.ALP.IS completed successfully at 04/03/2007 04:05:16 AM. (SESSION: 68102)  '''
			''' ANR2507I Schedule SQL_LOG_1815 for domain SJOVA started at 04/24/07 18:15:00 for node SJOVA-SLP-DB1.SJOVA.LOCAL_SQL comp... '''
			expr = r'^ANR2507I Schedule .* for domain .* started at .* for node (.*) completed .*'
			#split = i['message'].split()
			#i['nodename'] = split[13]
			#i['domainname'] = split[5]
		i['nodename'] = re.sub( expr, r'\1', i['message'])
		finalResult.append( i )
		
	return finalResult
def getStatus(): return __getData('status', orderby='snap_id desc limit 1')
def getDb(): return __getData('db', orderby='snap_id desc limit 1')
def getLog(): return __getData('log', orderby='snap_id desc limit 1')

def getClientSchedules(domainfilter=None,schedulefilter=None,orderby=None):
	where = "1=1 " 
	if schedulefilter != None:
		where += " and schedule_name like %s "% getDB().escapeFilter (schedulefilter)
	if domainfilter != None:
		where +=  " and domain_name like %s " % getDB().escapeFilter(domainfilter)	
	return __getData('client_schedules',where=where,orderby=orderby)
def getClientSchedule(schedule_name):
	where="schedule_name='%s'"%schedule_name
	return __getData('client_schedules', where=where)
def getAssociations(schedule_name=None,node_name=None,domain_name=None,orderby=None):
	where = '1=1 '
	if schedule_name:
		where += " and schedule_name = %s "% getDB().escape(schedule_name)
	if node_name:
		where += " and node_name = %s "% getDB().escape(node_name)
	if domain_name:
		where +=  " and domain_name = %s " % getDB().escape(domain_name)
	return __getData('associations_view',where=where,orderby=orderby)
def getClientopts(node_name=None):
	if node_name:
		where = "node_name = %s"%getDB().escape(node_name)
	else:
		where = None
	return __getData('clientopts_view',where=where)

def getCopygroups(domain_name=None):
	if domain_name:
		where = "domain_name = %s"%getDB().escape(domain_name)
	else:
		where = None
	return __getData('bu_copygroups',where=where)
# Single returns
def getNode(node_name): return __getData('nodes_mv', where="node_name=%s"%getDB().escape(node_name))
def getDomain(domain_name): return __getData('domains_mv', where="domain_name=%s"%getDB().escape(domain_name))
def getStoragepool(stgpool_name): return __getData('stgpools_mv', where="stgpool_name=%s"%getDB().escape(stgpool_name))
def getLastSnapshot(): return __getData('last_snap_view')
def getActlogCount(orderby=None,messageCutLength=None):
	override = {}
	if messageCutLength:
		override['newest_message'] = '''if(length(newest_message)>%d,concat(left(newest_message,%d),
			' ...'),newest_message)''' % (messageCutLength,messageCutLength-4)

	return __getData('actlog_count_mv',orderby=orderby,overrideFields=override)

def getSchedules(start):
	fields = 'entity,start_time,successful'
	query = '''select %s from summary where activity = 'BACKUP' and start_time > '%s' order by entity'''
	print query%(fields,start)
	count,res = getDB().query(query%(fields,start))
	objects = []
	for row in res:
		do = DataObject('schedules', fields.split(','), row,optimize_performance=True)
		objects.append(do)
	return objects

# Here comes the private stuff
def __simpleSelect(tableName, where=None,
		orderby=None,groupby=None,fields=None,invert=False):
	fieldList = []
	fieldOrder = []
	for key,value in fields.items():
		if value:
			if key == value: fieldList.append(key)
			else: fieldList.append('%s %s' % (value, key))
			fieldOrder.append(key)

	query = 'select %s from %s'% (','.join(fieldList), tableName)

	if where:
		begin = ''
		end = ''
		if invert:
			begin = 'not ('
			end = ')'
		if type(where) == list:
			query += ' where ' + begin + ' and '.join( where ) + end
		else:
			query += ' where ' + begin + where + end
	if groupby != None:
		query += ' group by ' + groupby
	if orderby != None:
		query += ' order by ' + orderby


	count,res = getDB().query(query)

	return fieldOrder,res

def __getFields(tableName):
	count,results = getDB().query('describe %s'%tableName.split()[0])
	fields = {}
	for row in results:
		field,type,null,key,default,extra = row
		fields[field] = field

	return fields

_fieldCache = {}
def __getData(tableName,where=None,optimize_performance=False,
	orderby=None,groupby=None,fields=None,overrideFields={},invert=False):
	global _fieldCache
	if not fields:
		if not _fieldCache.has_key(tableName):
			_fieldCache[tableName] = __getFields(tableName)
		fields = _fieldCache[tableName]
	if overrideFields:
		fields = copy.deepcopy(fields)
		for key,value in overrideFields.items(): fields[key] = value

	(fieldOrder,result) = __simpleSelect(tableName,where=where,
		orderby=orderby,groupby=groupby,fields=fields,invert=invert)
	rows = []

	for values in result:
		rows.append( DataObject(tableName,fieldOrder,values, optimize_performance=optimize_performance) )

	return rows

# Class definitions
class DataObject(dict):
	'''A Generic data container. '''
	def __init__(self, className,fields,values,optimize_performance=False):
		self.name = className

		assert( len(values) == len(fields) )
		fields = map(str,fields)

		# TODO: optimize this non-sense some how
		for i in range(len(fields)):
			self[fields[i]] = values[i]

	def __getattr__(self,key):
		if key != 'has_key' and self.has_key(key): return self.get(key)
		return super(DataObject,self).__getattribute__(key)
	def __setattr__(self,key,value): self[key] = value
	def __getitem__(self, key): return self.get(key)
	def __str__(self):
		return self.__repr__()
	def __repr__(self):
		result = self.name + '\n'
		keys = self.keys()
		keys.sort()
		for k in keys:
			result += ' %s: %s \n'%(k,self[k])
		return result

__hasStatmonACL = None
def hasStatmonACL():
	global __hasStatmonACL
	if __hasStatmonACL == None:
		try:
			getDB().query('desc statmon_users')
			getDB().query('desc statmon_acl')
			__hasStatmonACL = True
		except NoSuchTable:
			__hasStatmonACL = False
	return __hasStatmonACL

def getStatmonUsers(orderby='user'):
	return __getData('statmon_users',orderby=orderby)

def getStatmonUserStats(orderby='user',extraCount=None):
	fields = {
		'user'					: 'u.user',
		'node_count'			: 'count( n.node_name )',
		'logical_bytes_arch'	: 'sum( logical_bytes_arch )',
		'physical_bytes_arch'	: 'sum( physical_bytes_arch )',
		'num_files_arch'		: 'sum( num_files_arch )',
		'logical_bytes_bkup'	: 'sum( logical_bytes_bkup )',
		'physical_bytes_bkup'	: 'sum( physical_bytes_bkup )',
		'num_files_bkup'		: 'sum( num_files_bkup )',
	}
	if extraCount:
		condition = "n.node_name like '%" + "' or n.node_name like '%".join(extraCount) + "'"
		
		fields['node_count'] = 'sum( if(not (%s),1,0) )' % condition
		fields['extra_count'] = 'sum( if(%s,1,0) )' % condition


	table = """statmon_users u left join statmon_acl a on (u.user=a.user and a.type='node_name')
left join nodes_mv n on (a.entity=n.node_name)"""

	return __getData(table,orderby=orderby,where="u.access != 9 and u.access != 1 and u.access != 41",fields=fields,groupby='u.user')

def updateStatmonUser(user,password=None,access=None):
	values = (getDB().escape(user),getDB().escape(password),int(access))
	query = 'insert into statmon_users ( user, password, access, reg_date ) values ( %s, password(%s), %s, now() )' % values
	if password or access:
		query += ' on duplicate key update'
		comma = ''
	if password:
		query += ' password=password(%s)' % getDB().escape(password)
		comma = ','
	if access:
		query += comma + ' access=%s' % int(access)
	try:
		getDB().query(query)
		getDB().query('commit')
	except DuplicateEntry: pass

def deleteStatmonUser(user):
	query = 'delete from statmon_users where user=%s' % getDB().escape(user)
	getDB().query(query)
	query = 'delete from statmon_acl where user=%s' % getDB().escape(user)
	getDB().query(query)
	getDB().query('commit')

def getStatmonUser(user,password=None):
	where = []
	where.append('user = %s' % getDB().escape(user))
	if password != None:
		where.append('password = password(%s)' % getDB().escape(password))
	users = __getData('statmon_users',where=where)
	if not users:
		return None
	assert(len(users)==1)
	return users[0]

def validateStatmonUser(user,password=None):
	query = [ 'update statmon_users',
				'set last_login = now(), login_count = login_count + 1',
				'where user = %s' % getDB().escape(user) ]
	if password != None:
		query.append('and password = password(%s)' % getDB().escape(password))
	count, rows = getDB().query('\n'.join(query))
	if count:
		getDB().query('commit')
		return True # loggin successful, commit last_login updates
	return False # loggin unsucessful, nothing to commit

def getStatmonACL(user,entityType):
	where = 'user=%s and type=%s' % (getDB().escape(user),getDB().escape(entityType))
	return map(lambda x: x.entity, __getData('statmon_acl',where=where))

def updateStatmonACL(user,entityType,entityList,replace=True):
	if replace:
		query = 'delete from statmon_acl where user=%s and type=%s' % (getDB().escape(user),getDB().escape(entityType))
		getDB().query(query)
	try:
		for entity in entityList:
			query = 'insert into statmon_acl ( user, type, entity ) values ( %s, %s, %s )'
			query = query % ( getDB().escape(user),getDB().escape(entityType), getDB().escape(entity) )
			try:
				getDB().query(query)
				getDB().query('commit')
			except DuplicateEntry: pass
	except:
		getDB().query('rollback')
		raise

# TODO: Integrate with the rest of the model
# e.g. 'de-anzafy' cause this could be handy
def getAnzaContacts():
	"""Returns a distinct list of all contacts Anza custom report"""
	
	#select contact from nodes where contact is not null group by contact;
	where = 'contact is not null group by contact'
	fields = {}
	fields['count'] = 'count(1)'
	fields['contact'] = 'contact'
	return __getData('occupancy_anza_node_view',where=where,fields=fields)

