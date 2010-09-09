
from utils import generateHash,XMLLogger,getCurrentUser
import os

_subdirs = []
_instance = None
def getTempPath(subdir=None):
	global _tmpPath, _firstRun, _subdirs, _instance
	assert ( _instance )

	if not _tmpPath:
		# TODO: read from config
		_tmpPath = '/tmp'
		# append apache user id
		_tmpPath += '/%s' % getCurrentUser()
		# append hash generated from instance unique location
		_tmpPath += '/%s' % _instance

	tempPath = _tmpPath

	if _firstRun:
		_firstRun = False
		_initTemp()

	if subdir:
		tempPath = tempPath+'/'+subdir
		if subdir not in _subdirs:
			logger.show('Creating %s...' % tempPath )
			assert( not os.system( 'mkdir -p %s' % tempPath ) )
			_subdirs.append( subdir )

	return tempPath

def getInstanceId():
	return _instance

def nameEnvironment( root ):
	global _instance
	basename = os.path.basename( root ).replace(' ','.')
	rootname = '-'.join( basename.split('.')[:-1] )
	rootid = generateHash( root )
	_instance = '%s-%d' % ( rootname, rootid )
	return _instance

if not __name__ == '__main__': nameEnvironment( __file__ )
else: nameEnvironment( 'test.py' )

_tmpPath = None
_firstRun = True
def _initTemp():
	logger.start('Init Temp')
	tempPath = getTempPath()

	try: ppid = int(os.popen('cat %s/pid' % tempPath).read())
	except: ppid = None

	if ppid != os.getppid():
		commands = []
		logger.show('Deleting %s...' % tempPath )
		commands.append( 'rm -rf %s' % tempPath )
		logger.show('Creating %s...' % tempPath )
		commands.append( 'mkdir -p %s' % tempPath )
		logger.show('Creating %s/pid...' % tempPath )
		commands.append( 'echo %d > %s/pid' % (os.getppid(),tempPath) )
		assert( not os.system( ' && '.join( commands ) ) )

	logger.show('Touching %s/%d...' % (tempPath, os.getpid()) )
	os.system( 'touch %s/%d' % (tempPath, os.getpid()) )

	logger.end()

class delayedGetTempPath:
	def __init__(self,subdir=None,filename=None):
		self.subdir = subdir
		self.filename = filename
	def __str__(self):
		path = getTempPath(subdir=self.subdir)
		if self.filename:
			path += '/%s' % self.filename
		return path

logger = XMLLogger( delayedGetTempPath('logs', '%06d.xml' % os.getpid() ) )

