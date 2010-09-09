#!/usr/bin/python

import re
import MySQLdb
try:
	from core.utils import *
except:
	import sys
	sys.path.append('..')
	from core.utils import *
from os import popen
import datetime

from defaultConfig import configStatmonLocalDB,configStatmonTSM

# simplified error objects for catching exceptable common errors
import exceptions
class NoSuchTable(exceptions.Exception): pass
class DuplicateEntry(exceptions.Exception): pass

class MySQLDataSource:

	def __init__(self,logger = NullLogger(), host=None,user=None,passwd=None,db=None,port=3306):
		self.hostname = configStatmonLocalDB.host.getValue(defaultOverride=host)
		self.username = configStatmonLocalDB.user.getValue(defaultOverride=user)
		self.port = configStatmonLocalDB.port.getValue(defaultOverride=port)
		self.password = configStatmonLocalDB.passwd.getValue(defaultOverride=passwd)
		self.database = configStatmonLocalDB.db.getValue(defaultOverride=db)

		self.l = logger
		self.l.start("MySQLDataSource.__init__(...)")

		self.l.show("host = %s" % self.hostname)
		self.l.show("user = %s" % self.username)
		self.l.show("passwd = %s" % (len(self.password) * '*'))
		self.l.show("db = %s" % self.database)
		
		self._connect()
		self.l.end()
	def _connect(self):
		if hasattr(self, 'connection'):
			try: self.connection.close()
			except: pass
		self.connection = MySQLdb.connect(
			host = self.hostname,
			user = self.username,
			port = self.port,
			passwd = self.password,
			db = self.database,
			charset = 'utf8' )
		self.cursor = self.connection.cursor()		
	def query(self, string):
		self.l.start("MySQLDataSource.query(...)")
		self.l.show("query = ")
		for line in string.splitlines():
			if line:
				self.l.show(line,'+')
		if type(string) != unicode:
			string = unicode(string,'latin1')
		count = result = None
		try:
			count = self.cursor.execute(string)
		except MySQLdb.OperationalError, e:
			l = FileLogger('/tmp/debug.log')
			l.show(e)
			if e[0] == 2006:
				l.start("Trying to reconnect")
				self._connect()
				l.show("self_connect() is finished")
				count = self.cursor.execute(string)
				l.show("self.cursor.execute(string) is finished")
				l.end()
			else:
				raise
		except MySQLdb.ProgrammingError, e:
			if e[0] == 1146: raise NoSuchTable, e[0]
			else: raise
		except MySQLdb.IntegrityError, e:
			if e[0] == 1062: raise DuplicateEntry, e[0]
			else: raise
		self.l.end("count: %d" % count)
		return count, self.cursor.fetchall()
	def commit(self):
		self.connection.commit()
	def escape(self,string,addQuotes=True):
		if string == None: return 'null'
		if type(string) == datetime.datetime: string = str(string)
		if type(string) == type(1): return str(string)
		if addQuotes:
			return '\'%s\'' % MySQLdb.escape_string(string)
		else:
			return '%s' % MySQLdb.escape_string(string)
	def escapeFilter(self,string):
		return self.escape(string).replace('*','%').replace('?','_')
	def escapeList(self,items):
		if not items: return '(null)'
		return '(%s)' % ', '.join(map(self.escape,items))
	def close(self):
		return self.cursor.close()
class TSMDatasource:
	def __init__(self,logger=NullLogger()):
		self.username = configStatmonTSM.user.getValue()
		# TODO: fix
		self.password = configStatmonTSM._get('.pass').getValue()
		self.server = configStatmonTSM.server.getValue()
		self.l = logger

		self.l.start("TSMDatasource.__init__(...)")
		self.l.show('username = %s' % self.username)
		self.l.show('password = %s' % (len(self.password) * '*'))
		self.l.show('server = %s' % self.server)
		self.l.end()

	def query(self, query):
		self.l.start("TSMDataSource.query(...)")
		self.l.show("query = ")
		self.l.show(query)
		query = re.sub('"',"'", query) 
		command = '''/usr/bin/dsmadmc -id=%s -pa=%s -server=%s -tabd "%s" ''' %\
				(self.username,self.password,self.server,query)
		tsm_result = popen(command)

		tmp = None
		# Header ist hier
		while tmp != 'ANS8000I' :
			# the big wtf, how does this not inf loop if ANS8000I is not found
			row = tsm_result.readline()

			if row == '\n': continue
			tmp = row.split()[0]
			assert tmp != 'ANS1217E', 'Server name `%s\' not found in System Options File' % self.server

		# Data ist hier
		parsed_results = []
		for row in tsm_result.readlines():
			row = row.strip('\n')
			tmp = row[:9]
			if tmp == '': continue
			if tmp == 'ANS8002I ': break
			if tmp == 'ANR2034E ': break
			if tmp == 'ANS8001I ': raise DataBaseException( row, query, parsed_results )
			items = row.split('\t')
			row = []
			for i in items:
				#i = re.sub("'", r"\'",i)
				if i == '': row.append( None )
				else: row.append( "%s"%i)
			parsed_results.append ( row )
		
		# Hier ist footah
		self.l.end("count: %d" % len(parsed_results) )
		return parsed_results

class DataBaseException(Exception):
    def __init__(self, value, query, parsed_results):
        self.value = value
        self.query = query
        self.parsed_results = parsed_results
        Exception.__init__(self)
    def __str__(self):
        return self.__repr__()
    def __repr__(self):
        return "Error: %s"%self.value


def main():
	"""Unit tests for datasource.py"""
	#import config

	l = Logger()
	
	l.start("Begin Database Self Test")

	db = MySQLDataSource(l)

	count, results = db.query('show table status from %s;' % db.database)
	
	l.start("Display Results: ")
	for result in results:
		table = result[0]
		rows = result[4]
		l.show("""table: %-30s rows: %6s""" % (table, rows))
	l.end()
	
	testobj = ['test', '_t\\e\'st%','?est*',1,'',None]
	
	for obj in testobj:
		l.start("escape: %s" % obj)
		l.end(str(db.escape(obj)))

	for obj in testobj:
		l.start("escapeFilter: %s" % obj)
		l.end(str(db.escapeFilter(obj)))

	l.start("escapeList: %s" % testobj)
	l.end(str(db.escapeList(testobj)))

	l.end()

	#
	# TSM Datasource tests
	#

	l.start("Begin TSM Datasource test")
	tsm = TSMDatasource()
	l.start("select server_name from status")
	try:
		q = tsm.query("select SERVER_NAME from status")
		row1 = q[0]
		col1 = row1[0]
		if col1 == 'EISBOCK': l.end('success')
		else: raise 'failure'
	except:
		l.end('failure')
	try:
		l.start("select ERROR from ERROR")
		q = tsm.query("select ERROR from ERROR")
		l.show(q)
		l.end('failure')
	except DataBaseException:
		l.end('success')


if __name__ == '__main__': main()
