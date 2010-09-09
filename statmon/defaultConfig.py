""" Default Config Settings - DO NOT EDIT """

try:
	from core.config import config
except:
	import sys
	sys.path.append('..')
	from core.config import config

config.registerSetting(path='.statmon', description='Configurations for Statmon')

# graph stuff
config.statmon.registerSetting(path='.grapher', description='Settings used by Grapher')

config.statmon.grapher.registerSetting(path='.graphStart',default=30*6,
	description='Default graph start time in days from current time.')
config.statmon.grapher.registerSetting(path='.graphEnd',default=1,
	description='Default graph end time in days from current time.')
config.statmon.grapher.registerSetting(path='.graphWidth', default=700,
	description='Default graph width (in pixels).')
config.statmon.grapher.registerSetting(path='.graphHeight', default=100,
	description='Default graph height (in pixels).')

# settings for local db
config.statmon.registerSetting(path='.localDB', description='Settings for Local MySQL database')

config.statmon.localDB.registerSetting(path='.user', default='statmon',
	description='Local MySQL username to use.')
config.statmon.localDB.registerSetting(path='.passwd', default='statmon',
	description='Local MySQL user password.')
config.statmon.localDB.registerSetting(path='.db', default='statmon',
	description='Local MySQL database to use.')
config.statmon.localDB.registerSetting(path='.host', default='localhost',
	description='Local MySQL host to use.')
config.statmon.localDB.registerSetting(path='.port', default=3306,
	description='Local MySQL port to use.')

# for tsm server
config.statmon.registerSetting(path='.tsm', description='Settings required for TSM collection')

config.statmon.tsm.registerSetting(path='.user', default='statmon',
	description='TSM user to use when collecting.')
config.statmon.tsm.registerSetting(path='.pass', default='statmon',
	description='TSM user password.')
config.statmon.tsm.registerSetting(path='.server', default='localhost',
	description='TSM server to collect from.')

# misc
config.statmon.registerSetting(path='.misc', description='Misc Settings')

config.statmon.misc.registerSetting(path='.actlogIgnoreList', default=[ 45778, 147830, 147876 ],
	description='Actlog messages-IDs that should never stored. Can dramatically reduce space requirements for local DB, but can also break current or future features that may depend on given message-ID')
config.statmon.misc.registerSetting(path='.backupHistoryStart', default=20,
	description='Number of days shown by default when viewing backup history.')
config.statmon.misc.registerSetting(path='.TDPSuffixes', default=[],
	description='')

# TODO remove
configStatmon = config.statmon
configStatmonGrapher = config.statmon.grapher
configStatmonLocalDB = config.statmon.localDB
configStatmonTSM = config.statmon.tsm
configStatmonMisc = config.statmon.misc

if __name__ == '__main__': config.saveXML(comments=True)
	#config.__class__._debug = True
	#config.loadXML('test.xml')
	#config.saveXML()
