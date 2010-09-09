#!/usr/bin/python

import sys, os

configPath = '%s/statmonConfig.xml'
postSQLPath = '%s/statmon/fakematviews.sql'

if __name__ == '__main__':
	path = os.path.dirname(os.path.abspath(sys.argv[0]))
	root = os.path.abspath(path+'/../')
	sys.path.append(root)

	configPath = configPath % root
	postSQLPath = postSQLPath % root

	print 'Looking for config at %s ..' % configPath,
	if os.path.isfile(configPath): print 'OK'
	else:
		print 'ERR'
		sys.exit(-1)

	print 'Looking for post SQL at %s ..' % postSQLPath,
	if os.path.isfile(postSQLPath): print 'OK'
	else:
		print 'ERR'
		sys.exit(-1)
else:
	assert(0) # not a importable module

import core.utils
import datasource
import datetime
import re
import warnings
from statmon.defaultConfig import config,configStatmonMisc

from os import popen
#from datasource import *

__all__ = [ 'jobs', 'Collector' ]

__version__ = '$Revision: 1008 $'.split()[-2:][0]

def main():
	
	l = core.utils.Logger()

	l.start("Begin Collection")
	config.loadXML(configPath)

	tsm = datasource.TSMDatasource(logger=l)
	local = datasource.MySQLDataSource(logger=l)
	
	Jobs = [Filespaces, Filespaces_snapshots,
				Storagepools, Storagepools_snapshots,
				Domains_snapshots,Nodes_snapshots,
					Domains,Nodes,Occupancy_snapshot,Summary,
					Volumes, Volumes_snapshots,Actlog,
					Status,Log,Db,Client_schedules,Associations,
					LocalDBSize
				]
	Jobs += [Clientopts,Cloptsets,Bu_Copygroups]
	try:
		collector = Collector(tsm=tsm,local=local)
		for i in Jobs: collector.addJob(i)
		collector.run()
		execFile(postSQLPath,local)
	except datasource.DataBaseException,e:
		print
		for i in e.parsed_results:
			print i[0]
		print 'Query:', e.query
		print
	l.end()

class Collector:
	def __init__(self,tsm,local):
		self.__jobList = []
		self.__retrievalDatasource = tsm
		self.__storeDatasource = local
		self.__scheduler = None
		self.__version = __version__
	def addJob(self, job):
		self.__jobList.append(job)
	def setScheduler(self, scheduler):
		self.__scheduler = scheduler
	def run(self):
		snap = self.createNewSnap()
		for i in self.__jobList:
			tmp = i(snap=snap,tsmDatasource=self.__retrievalDatasource, mysqlDatasource=self.__storeDatasource)
			tmp.run()
		self.__storeDatasource.commit()
		self.completeSnap(snap)
		self.__storeDatasource.commit()
		pass
	def createNewSnap(self):
		db = self.__storeDatasource
		dt = datetime.datetime.now().isoformat()
		query = """insert into snapshots (start_date, version) values ('%s', %s)"""%(dt, self.__version)
		db.query( query )
		return db.cursor.connection.insert_id()
	def completeSnap(self,snap):
		db = self.__storeDatasource
		dt = datetime.datetime.now().isoformat()
		query = """update snapshots set end_date='%s', completed=true where snap_id=%s """%(dt,snap)
		db.query( query )


class Job:
    tablename = 'nodes'
    items = 'node_name'
    selectQuery = 'select %s s'
    insertQuery = 'insert into nodes (%s) values(%s) on duplicate key update %s'
    translationScheme = None
    updateQuery = ''
    def __init__(self,snap,tsmDatasource,mysqlDatasource):
        self.tsm = tsmDatasource
        self.local = mysqlDatasource
        self.snap = snap
        self.results = None
    def start(self):
        self.selectQuery = self.selectQuery%self.items
        self.results = self.tsm.query(self.selectQuery)
    def process(self):
        pass
    def end(self):
        for row in self.results:
            tmp = []
            for col in row:
                col = self.local.escape(col)
                tmp.append( col )
            values = ','.join(tmp)
            #print self.insertQuery
            query = self.insertQuery%(self.items,self.snap,values,self.updateQuery)
            #print query
            self.local.query(query)
    def run(self):
        self.start()
        self.process()
        self.translateColumnNames()
        self.createDuplicateString()
        self.end()
        self.updateLastSnap()
    def updateLastSnap(self):
        pass
    def escapeQuotas(self, string):
        # First convert \ to \\
        # Then convert all ' to \'
        result = re.sub(r'\\', r'\\\\', string)
        result = re.sub("'", "\\'", result)
        return result
    def createDuplicateString(self):
        tmp = []
        for i in self.items.split(','):
            tmp.append('%s = VALUES(%s)'%(i,i))
        self.updateQuery = ','.join(tmp)
    def translateColumnNames(self):
        '''
        This function is used if we have columns on the TSM server
        that are keywords in mysql.
        
        This function should be run before commiting to mysql and after
        collecting all data from TSM.
        '''
        if not self.translationScheme: return
        items = self.items.replace(' ','')
        items = items.split(',')
        newItems = []
        for item in items:
            if self.translationScheme.has_key(item):
                item = self.translationScheme[item]
            newItems.append(item)
        self.items = ','.join(newItems)
        #print self.items

class Nodes(Job):
    items = "node_name,platform_name,contact,lastacc_time,reg_time,reg_admin,nodetype,url,tcp_name,tcp_address"
    selectQuery = 'select %s from nodes'
    insertQuery = "INSERT INTO nodes (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE snap_id=VALUES(snap_id),%s"
class Domains(Job):
    items = 'domain_name,description,set_last_activated,activate_date, defmgmtclass,chg_time,chg_admin,profile'
    selectQuery = 'select %s from domains'
    insertQuery = "insert into domains (snap_id,%s) values(%s,%s) on duplicate key update snap_id=VALUES(snap_id), %s "
class Filespaces(Job):
    items = 'node_name,filespace_id,filespace_name,filespace_type'
    selectQuery = 'select %s from filespaces'
    insertQuery = "insert into filespaces (snap_id,%s) values (%s,%s) on duplicate key update snap_id=VALUES(snap_id), %s"
class Storagepools(Job):
    items = 'stgpool_name, pooltype, devclass,nextstgpool, access,description,ovflocation,cache,collocate'
    selectQuery = 'select %s from stgpools'
    insertQuery = "INSERT INTO stgpools (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE snap_id=VALUES(snap_id), %s"

class Occupancy_snapshot(Job):
    items = 'node_name,filespace_id,stgpool_name,type,num_files,physical_mb,logical_mb'
    selectQuery = 'select %s from occupancy'
    insertQuery = "insert into occupancy_snapshots (snap_id,%s) values (%s,%s) on duplicate key update %s"
class Summary(Job):
    items = 'entity,activity,start_time,end_time,schedule_name,examined,affected,failed,bytes,successful'
    selectQuery = 'select %s from summary'
    insertQuery = "insert into summary (snap_id,%s) values (%s,%s) on duplicate key update %s"
    def process(self):
        for i in self.results:
            if i[0] == None: i[0] = "''"
class Volumes(Job):
    items = 'volume_name,stgpool_name,devclass_name,est_capacity_mb,scaledcap_applied,pct_utilized,status,access,pct_reclaim,scratch,error_state,num_sides,times_mounted,write_pass,last_write_date,last_read_date,pending_date,write_errors,read_errors,location,mvslf_capable,chg_time,chg_admin,begin_rclm_date,end_rclm_date'
    selectQuery = 'select %s from volumes'
    insertQuery = "INSERT INTO volumes (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE snap_id=VALUES(snap_id), %s"
class Filespaces_snapshots(Job):
    items = 'node_name,filespace_id,capacity,pct_util,backup_start,backup_end,delete_occurred'
    selectQuery = 'select %s from filespaces'
    insertQuery = "insert into filespaces_snapshots (snap_id,%s) values (%s,%s) on duplicate key update %s"
class Nodes_snapshots(Job):    
    items = 'node_name, domain_name, client_version, client_release,client_level, client_sublevel,option_set'
    selectQuery =  'select %s from nodes'
    insertQuery = "INSERT INTO nodes_snapshots (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
class Domains_snapshots(Job):    
    items = 'domain_name, num_nodes, backretention, archretention'
    selectQuery = 'select %s from domains'
    insertQuery = "INSERT INTO domains_snapshots (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
class Storagepools_snapshots(Job):
    items = 'stgpool_name,est_capacity_mb,pct_utilized,pct_migr,pct_logical,highmig,lowmig,migprocess,maxsize,reclaim,maxscratch,numscratchused,reusedelay'
    selectQuery = 'select %s from stgpools'
    insertQuery = "INSERT INTO stgpools_snapshots (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
class Status(Job):
    items = 'server_name , server_hla , server_url , availability , actlogretention, summaryretention , licensecompliance , scheduler , eventretention , platform , version, release, level, sublevel'
    selectQuery = 'select %s from status'
    insertQuery = "INSERT INTO status (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
    translationScheme = { 'level':'server_level', 'release':'server_release', 'sublevel':'server_sublevel', 'version':'server_version'  }
class Db(Job):
    items = 'avail_space_mb , capacity_mb , max_extension_mb , max_reduction_mb , pct_utilized , max_pct_utilized , cache_hit_pct , last_backup_date'
    selectQuery = 'select %s from db'
    insertQuery = "INSERT INTO db (dummy_key,snap_id,%s) VALUES(1,%s,%s) ON DUPLICATE KEY UPDATE %s"
class Log(Job):
    items = 'avail_space_mb , capacity_mb , max_extension_mb , max_reduction_mb , pct_utilized , max_pct_utilized'
    selectQuery = 'select %s from log'
    insertQuery = "INSERT INTO log (dummy_key,snap_id,%s) VALUES(1,%s,%s) ON DUPLICATE KEY UPDATE %s"    
class Cloptsets(Job):
    items = "optionset_name,description,last_update_by,profile"
    selectQuery = 'select %s from cloptsets'
    insertQuery = "INSERT INTO cloptsets (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE snap_id=VALUES(snap_id),%s"
class Bu_Copygroups(Job):
    items = "domain_name,set_name,class_name,copygroup_name,verexists,verdeleted,retextra,retonly,mode,serialization,frequency,destination,toc_destination,chg_time,chg_admin,profile"
    selectQuery = 'select %s from bu_copygroups'
    insertQuery = "INSERT INTO bu_copygroups (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE snap_id=VALUES(snap_id),%s"
class Clientopts(Job):
    items = "optionset_name,option_name,seqnumber,option_value,force,obsolete,when_obsolete"
    selectQuery = 'select %s from clientopts'
    insertQuery = "INSERT INTO clientopts (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE snap_id=VALUES(snap_id),%s"    
    translationScheme = { 'force':'force_option' }
class Associations(Job):
    items = 'node_name,domain_name,schedule_name,chg_admin,chg_time'
    selectQuery = 'select %s from associations'
    insertQuery = "INSERT INTO associations (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"    
class Client_schedules(Job):
    items = 'domain_name , schedule_name , description , action, options,objects,priority,startdate,starttime,duration,durunits,period,perunits,dayofweek,expiration, chg_time, chg_admin, profile,sched_style, enh_month,dayofmonth,weekofmonth'
    selectQuery = 'select %s from client_schedules'
    insertQuery = "INSERT INTO client_schedules (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
class Volumes_snapshots(Job):
    items = 'volume_name,est_capacity_mb,pct_utilized,status,access,pct_reclaim,write_pass,write_errors,read_errors'
    selectQuery = 'select %s from volumes'
    insertQuery = "INSERT INTO volumes_snapshots (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"    
class Actlog(Job):
    tablename = 'actlog'
    selectQuery = "select %s from actlog "
    insertQuery = "INSERT INTO actlog (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
    items = 'msgno,date_time,severity,originator,nodename,ownername,domainname,sessid,session,process,message'
    def start(self):
        count,timestamp = self.local.query('select max(date_time) from actlog')
        t = timestamp[0][0]
        n = now = datetime.datetime.now()
        if not t:
            t =  datetime.datetime(1900,1,1,0,0,0)
        if t > now:
            warnings.warn("Latest actlog record happens in the future (check clock?)\n Now: %s\n Latest Record: %s"%(now,t) )
            t = datetime.datetime.now()
        
        # Fetch only records that are more recent than last recorded date_time
        # in local database
        timestamp = (t.year,t.month,t.day,t.hour,t.minute,t.second)
        self.selectQuery += " WHERE date_time>'%s-%s-%s %s:%s:%s.00'"%(timestamp)
        # Make sure actlog does not fetch records that happen in the future
        # TODO: Better make sure collector clock is correct.
        tsNow = (n.year,n.month,n.day,n.hour,n.minute,n.second)
        self.selectQuery += "  and date_time<'%s-%s-%s %s:%s:%s.00'"%(tsNow)
        
        # skip all records that are in specified ignore list
        ignorelist = configStatmonMisc.actlogIgnoreList.getValue()
        if ignorelist and len(ignorelist)>0:
            # Make sure ignorelist contains just integers
            for i in ignorelist:
                if type(i) != type(1):
                    raise "Only integers allowed in msgno ignore list"
                
            ignorelist = ','.join( map(str,ignorelist) )
            self.selectQuery += " and msgno not in (%s)"%ignorelist
        # And we are finished
        #print self.selectQuery
        Job.start(self)
    def process(self):
        # We need to convert ' that appear in some columns to \'
        for i,row in enumerate(self.results):
            tmp = []
            for column in row[:10]:
                tmp.append( column )
            message = ""
            for column in row[10:]:
                message += column
            tmp.append( message )
            self.results[i] = tmp

class LocalDBSize(Job):
    "This job collects the size of local db"
    selectQuery = "show table status"
    insertQuery = "insert into local_db (snap_id,%s) VALUES(%s,%s) ON DUPLICATE KEY UPDATE %s"
    items = 'size'
    def start(self):
        count,self.results = self.local.query(self.selectQuery)
    def process(self):
        totalSize = 0
        for i in self.results:
            #print i
            tableSize = i[6]
            indexSize = i[8]
            # Sizes can have a value of None
            if not tableSize: tableSize = 0
            if not indexSize: indexSize = 0
            totalSize += tableSize + indexSize
        self.results = []
        self.results.append( [str(totalSize)] )

def getCodelines(file):
	file = open(file,'r')
	lines = []
	for line in file.readlines():
		line = line.strip()
		if line and line[0] != '-': lines.append(line)

	lines = ' '.join(' '.join(lines).split()).split(';')
	return map(lambda x: x.strip(),lines)

def execFile(file,connection):
	lines = getCodelines(file)
	noExeced = 0
	for line in lines:
		if line:
			connection.query(line)
			noExeced += 1
	return noExeced

if __name__ == '__main__': main()
