
from core.baseControllers import SpecialController

from mod_python import apache

import model
import datetime
import sys

class HobitCheckController(SpecialController):
	def handleRequest(self):
		report = {}

		try:
			snapshots = model.getSnapshots(orderby='snap_id desc limit 15')
			if not len(snapshots):
				raise 'Check Failure', 'No collection found in DB'

			report['last_end_date'] = snapshots[0].end_date
			report['last_start_date'] = snapshots[0].start_date
			report['last_timedelta'] = datetime.datetime.now()-report['last_end_date']
			if report['last_timedelta'] > datetime.timedelta(days=2):
				raise 'Check Failure', 'Too long since last collection'
			report['last_duration'] = report['last_end_date']-report['last_start_date']
			if report['last_duration'] > datetime.timedelta(hours=2):
				raise 'Check Failure', 'Last collection duration too long'

			from __init__ import __version__
			try:
				report['version_collector'] = snapshots[0].version
			except: pass
			report['version_web'] = __version__

			local_db = model.getLocalDB()
			report['db_size'] = local_db[-1].size

			if len(local_db) > 1:
				report['last_snap_size'] = local_db[-1].size-local_db[-2].size

			self.req.write("OK\n")
			self.writeReport(report)
			return apache.OK
		except:
			error = sys.exc_info()[0]
			message = sys.exc_info()[1]

		# status must be set before any req.write!
		self.req.status = apache.HTTP_INTERNAL_SERVER_ERROR
		self.req.write("ERROR\n")

		self.writeReport(report,error,message)
		return apache.DONE

	def writeReport(self,report,error=None,message=None):
		self.req.write('\n')
		if error:
			self.req.write("error: %s\n" % error)
			if message:
				self.req.write("message: %s\n" % message)
			self.req.write('\n')

		keys = report.keys()
		keys.sort()
		for key in keys:
			self.req.write("%s: %s\n" % (key, report[key]))
