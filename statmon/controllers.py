
from core.baseControllers import registerController,ReturnLog

MASTER_ACCESS = 1 # master navigation
USER_ACCESS = 2 # user navigation
PRELOGIN = 4 # enable login
ACL_EDIT_ACCESS = 8 # enable user acl editing pages
LOGGED = 16 # enable logout
DEV_ACCESS = 32 # enable debug

import coreControllers
import userControllers
# Statmon Overview
#registerController(None, './', navTitle='General',grandparent=True)
registerController(coreControllers.OverviewController,		'./',grandparent=True,			accessLevel=MASTER_ACCESS)
registerController(userControllers.NodeListController,'./',grandparent=True,navTitle='Overview',accessLevel=USER_ACCESS)
registerController(userControllers.NodeListController,		'nodes',						accessLevel=USER_ACCESS)
registerController(userControllers.GraphsController,		'graphs',						accessLevel=USER_ACCESS)
registerController(coreControllers.ClientSchedulesController,'schedules',					accessLevel=MASTER_ACCESS)
registerController(coreControllers.ClientScheduleController,'schedules/schedule',child=True,accessLevel=MASTER_ACCESS)
registerController(coreControllers.NodeListController,		'nodes',						accessLevel=MASTER_ACCESS)
registerController(coreControllers.DomainController,		'domains/domain',	child=True,	accessLevel=MASTER_ACCESS)
registerController(coreControllers.NewNodesController,		'nodes/new',		child=True,	accessLevel=MASTER_ACCESS)
registerController(coreControllers.NodeController,			'nodes/node',		child=True,	accessLevel=MASTER_ACCESS|USER_ACCESS)
registerController(coreControllers.FilespacesController,	'filespaces',					accessLevel=MASTER_ACCESS)
registerController(coreControllers.GraphsController,		'graphs',						accessLevel=MASTER_ACCESS)
# TODO make proper child?
registerController(coreControllers.ZoomController,			'graphs/zoom',		navItem=False)

#registerController(None, 'server', navTitle='Server',										accessLevel=MASTER_ACCESS)
registerController(coreControllers.StoragePoolsController,	'pools',						accessLevel=MASTER_ACCESS)
registerController(coreControllers.StoragePoolController,	'pools/pool',		child=True,	accessLevel=MASTER_ACCESS)

# Reports
registerController(navTitle='Reports',grandparent=True,										accessLevel=MASTER_ACCESS|USER_ACCESS)
registerController(coreControllers.ActlogController,		'actlog',						accessLevel=MASTER_ACCESS)
registerController(coreControllers.ActlogStatsController,	'actlog/stats',		child=True,	accessLevel=MASTER_ACCESS)
registerController(coreControllers.BackupStatusController,	'backup',						accessLevel=MASTER_ACCESS)
registerController(userControllers.BackupStatusController,	'backup',						accessLevel=USER_ACCESS)
registerController(coreControllers.FailedFilesController,	'failed',						accessLevel=MASTER_ACCESS)
registerController(coreControllers.SessionsController,		'sessions',						accessLevel=MASTER_ACCESS)
registerController(coreControllers.StorageAbusersController,'abusers',						accessLevel=MASTER_ACCESS)
registerController(coreControllers.SummaryController,'summaries',							accessLevel=MASTER_ACCESS)
registerController(coreControllers.SummaryBackupStatisticController,'summaries/stats',child=True,accessLevel=MASTER_ACCESS)

import anzaControllers
# Custom Reports
registerController(navTitle='Custom Reports',grandparent=True,								accessLevel=MASTER_ACCESS)
registerController(anzaControllers.AnzaBackupReportController,	'custom/backup',			accessLevel=MASTER_ACCESS)
registerController(anzaControllers.AnzaUsageReportController,	'custom/usage',				accessLevel=MASTER_ACCESS)

# Statmon Settings
import settingsControllers
registerController(settingsControllers.UserStatsController,'users/stats',				accessLevel=ACL_EDIT_ACCESS)

import helpControllers
# Help
registerController(navTitle='Statmon',grandparent=True)
registerController(helpControllers.AboutController,	'about')

# Statmon Informations
registerController(coreControllers.SnapshotController,'stats',								accessLevel=MASTER_ACCESS)

# Help
registerController(None,	'help',navTitle='Help',accessLevel=MASTER_ACCESS)
registerController(helpControllers.HelpController,	'help',child=True,accessLevel=MASTER_ACCESS)
registerController(					uri='statmon/help/adminguide.pdf',	navTitle='Admin Manual',child=True,accessLevel=MASTER_ACCESS)
registerController(					uri='statmon/help/userguide.pdf',	navTitle='User Manual',child=True,accessLevel=MASTER_ACCESS)

#registerController(settingsControllers.SettingsController,'settings',						accessLevel=MASTER_ACCESS)
registerController(settingsControllers.UsersController,'users',child=False,					accessLevel=ACL_EDIT_ACCESS)
registerController(settingsControllers.UserController,'users/user',navItem=False,			accessLevel=ACL_EDIT_ACCESS)

registerController(None,'./?login=1',navTitle='Login',										accessLevel=PRELOGIN)
registerController(None, './?logout=1',navTitle='Logout',									accessLevel=LOGGED)

# other non-navmenu accessable controllers
import miscControllers
registerController(miscControllers.HobitCheckController,	'tests/hobitcheck',	navItem=False)

# for internal testing/devlopment only, allowed to fail
try:
	import core.testControllers
	registerController(core.testControllers.TestsController, 'tests',accessLevel=DEV_ACCESS,grandparent=True)
	registerController(core.testControllers.LogsViewer, 'tests/logs',accessLevel=DEV_ACCESS)
except: raise

registerController(ReturnLog, 'tests/raw/logs', navItem=False)
