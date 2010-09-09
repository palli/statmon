
import sys,os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from statmon.defaultConfig import config

configFile = os.path.abspath(os.path.dirname(__file__))+'/statmonConfig.xml'

try:
	config.loadXML(configFile)
except: pass

from core.environment import nameEnvironment,logger,getTempPath,getInstanceId
nameEnvironment(__file__)

if not __name__ == '__main__':
	from core.baseControllers import SpecialController,setRootPath
	
	import posixpath
	
	setRootPath(os.path.dirname(__file__))
	from statmon.statmonControllers import OfflineStatmonController

	from mod_python import apache
	import statmon.controllers

def handler(req):
	"""
	Handles mod_python main request handler.
	
	Returns page as provided by BaseController or SpecialController
	(if one exists for given controller= provided with the GET method)
	"""

	logger.start('New request',reset=True)
	logger.show('ip: %s' % req.connection.remote_ip)
	logger.show('uri: %s' % req.unparsed_uri)
	req.get_options()['mod_python.dbm_session.database_directory'] = getTempPath()
	req.get_options()['mod_python.session.cookie_name'] = getInstanceId()

	flush = True
	try: ret, flush = handleRequest(req)
	except:
		# force log fush and raise
		logger.flush()
		raise
	logger.end(close=flush)
	return ret

def handleRequest(req):
	# Portability posixpath vs os.path ?!
	extension = posixpath.splitext(req.filename+max(req.path_info,''))[1]
	if extension in ['.png','.js','.css','.pdf','.gif','.htc']:
		if not os.path.exists(req.filename):
			raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND
		req.sendfile(req.filename)
		return apache.OK, False
	elif extension:
		raise apache.SERVER_RETURN, apache.HTTP_FORBIDDEN

	# outer most exception handling, all errors
	# "should" have been handled before this, but just in case
	try:
		controller = SpecialController(req)
		code = controller.handleRequest()
		if code != None: return code, False # handled by special controller

		controller = OfflineStatmonController(req,parent=controller)
		return controller.handleRequest(), True
	except(apache.SERVER_RETURN):
		# rethrow server returns
		raise
	except:
		import cgitb
		req.content_type = 'text/html'
		cgitb.Hook(file = req).handle()

	return apache.OK, True

def main():
	config.saveXML()

if __name__ == '__main__': main()
