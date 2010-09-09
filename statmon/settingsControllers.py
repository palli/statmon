
from statmonControllers import StatmonController
from core.tableControllers import TableController,TH
from core.inputControllers import InputController,II
from core.utils import StringToBool

import model

from urllib import urlencode
from cgi import escape

from defaultConfig import configStatmonMisc

class SettingsController(StatmonController):
	_title = 'Settings'
	#_filename = 'psp/login.psp'
	def createContent(self):
		#self.password = self.req.get_basic_auth_pw()
		#self.user = self.req.user
		
		#self.session = Session.Session(self.req)
		#try:
			#self.session['hits'] += 1
		#except:
			#self.session['hits'] = 1

		#self.session.save()
		pass
		
	def getContent(self):
		##session = Session.Session(self.req)
		return 'Place Holder'
		#return '''Place Holder<br/>
					#user: %s<br/>
					#pass: %s<br/>
					#hits: %d''' % (self.user, self.password, self.session['hits'])

class LoginController(StatmonController):
	_title = 'Login'
	_filename = 'psp/login.psp'

	def createContent(self):
		self.user = self.getField('user','')
		self.remember = StringToBool(self.getField('remember',False))
		self._highlightController = LoginController
		self.action = ''
		if StringToBool(self.getField('logout')):
			self.action = self.getSuffix()
			if not self.action:
				self.action = './'

# users - overview
class UsersController(StatmonController):
	_title = 'Users'
	_filename = 'psp/users.psp'

	from controllers import MASTER_ACCESS, USER_ACCESS, ACL_EDIT_ACCESS, DEV_ACCESS
	MASTER_TYPE = MASTER_ACCESS|ACL_EDIT_ACCESS
	ADMIN_TYPE = MASTER_ACCESS
	USER_TYPE = USER_ACCESS
	DEBUG_TYPE = DEV_ACCESS
	TYPE_MAP = { MASTER_TYPE:'Master', ADMIN_TYPE:'Admin', USER_TYPE:'User' }

	def updateSessions(self,user,access):
		pass

	def getAccessType(self,access):
		accessType = self.TYPE_MAP.get(access&~self.DEBUG_TYPE,'None')
		if access&self.DEBUG_TYPE:
			accessType += ' (debug)'
		return accessType

	def processInputs(self,allowBlankUser=True):
		update = StringToBool(self.getField('update'))
		addUser = InputController(self.req,'Add/Update User',applyButton='Add/Update User',defaultButton=None,parent=self)
		user = addUser.processInput(II('user','Username',II.TEXT,allowBlank=True))
		pass1 = addUser.processInput(II('pass1','Password',II.PASS,allowBlank=True))
		pass2 = addUser.processInput(II('pass2','Retype Password',II.PASS,allowBlank=True))

		originalUser = None
		if user:
			originalUser = model.getStatmonUser(user)

		accessOpt = self.USER_TYPE
		if not update:
			if originalUser and originalUser.access:
				accessOpt = originalUser.access
		options=((self.MASTER_TYPE,'Master'),(self.ADMIN_TYPE,'Admin'),(self.USER_TYPE,'User'))
		if self.getAccessLevel()&self.DEBUG_TYPE:
			for option in options:
				options += ((option[0]|self.DEBUG_TYPE,option[1]+' (debug)'),)

		access = addUser.processInput(II('access','Access Type',II.DROPDOWN,allowBlank=False,options=options,default=accessOpt))
		try: access = int(access)
		except: access = 0

		badval = False
		password = None
		passany = (pass1 or pass2)
		if passany:
			if pass1 == pass2:
				password = pass1
			else:
				addUser.updateInput('pass1',badval=True)
				addUser.updateInput('pass2',badval=True)
				badval = True

		self.addAlert(user and passany and not password,'E','Passwords do not match! Changes not applied.')

		if user:
			if not badval and update:
				if originalUser and not self.getAccessLevel()&self.DEBUG_TYPE:
					# only another debug user can remove debug
					access |= originalUser.access&self.DEBUG_TYPE

				model.updateStatmonUser(user,password,access)
				if originalUser:
					self.addMessage('User <span class="condition">%s</span> updated.' % self.escape(user))
				else:
					self.addMessage('User <span class="condition">%s</span> added.' % self.escape(user))
				if not password:
					if not originalUser or not originalUser.password:
						self.addAlert(True,'W','No password set! User <span class="condition">%s</span> will not be able to login until it has been set.' %user)
					else:
						self.addMessage('Old password was left unchanged.')
				if originalUser and originalUser.access != access:
					oldType = self.getAccessType(originalUser.access)
					newType = self.getAccessType(access)
					self.addMessage('Access Type change from <span class="condition">%s</span> to <span class="condition">%s</span>.' % (oldType,newType) )

		if not user and (passany or not allowBlankUser):
			addUser.updateInput('user',badval=True)

		self.addAlert(update and not user,'E','Bad Username! Changes not applied.')
		self.addAlert(not update and not user and not allowBlankUser,'W','Enter valid username before applying!')

		self.addUser = addUser.getContent()

		return (update and not badval), user

	def createContent(self):
		self.processInputs(allowBlankUser=True)

		delete = self.getField('delete',None)
		if delete:
			model.deleteStatmonUser(delete)
			self.addMessage('User <span class="condition">%s</span> deleted.' % self.escape(delete))

		self.userTable = userTable = TableController(self.req,'users','Users',emptyMessage='No users defined')

		linkUser = lambda x: '<a href="%s?user=%s">%s</a>' % (
			self.getControllerURI(UserController), x, x )

		userTable.addHeader(TH('user', 'User',TH.TEXT,linkUser,sorted=True))
		userTable.addHeader(TH('password', 'Password',TH.TEXT,dbOrder=False))
		userTable.addHeader(TH('access', 'Access Type',TH.HTML,dbOrder=False))
		userTable.addHeader(TH('reg_date', 'Date Added',TH.DATE))
		userTable.addHeader(TH('last_login', 'Last Login',TH.DATE))
		userTable.addHeader(TH('ops', 'Operations',TH.HTML,sortable=False))

		try:
			users = model.getStatmonUsers(orderby=userTable.getOrderBy())
		except model.NoSuchTable, e:
			users = []
			userTable.setEmptyMessage('User table does not exist in DB.<br/>Please create it for this functionality.')

		for i in users:
			i.access = self.getAccessType(i.access)

			if i.password: i.password = 'Yes'
			else: i.password = 'No'
			
			p = {}
			p['delete'] = i.user
			i.ops = '<a href="?%s">Delete</a>' % escape(urlencode(p))

			userTable.addRow(**i)

		self.userRedirect = self.getControllerURI(UserController)

# users/user - add/edit user

class UserController(UsersController):
	_title = 'User'
	_filename = 'psp/user.psp'
	_highlightController = UsersController

	def createContent(self):
		update, user = self.processInputs(allowBlankUser=False)

		updateNodes = StringToBool(self.getField('updateNodes'))

		# checked="checked"
		jsScript = '''<input class="checkbox" type="checkbox" name="_ALL_" onchange="SetAllCheckBoxes(this,this.checked);"/>'''
		extraFooter = '''<input class="submit commit" value="Add/Update User" type="submit">'''

		self.nodeTable = nodeTable = TableController(self.req,'nodes','Nodes',emptyMessage='No Matching Nodes Found',extraFooter=extraFooter,extraFooterClass='button')
		nodeTable.addHeader(TH('show_hide', jsScript,TH.HTML,sortable=False,escapeName=False))
		#nodeTable.addHeader(TH('view', 'View',TH.TEXT))
		nodeTable.addHeader(TH('node_name', 'Node Name',TH.TEXT,self.linkNode,sorted=True))
		nodeTable.addHeader(TH('domain_name', 'Domain Name',TH.TEXT,self.linkDomain))
		nodeTable.addHeader(TH('platform_name', 'Platform',TH.TEXT,sortDesc=False))
		nodeTable.addHeader(TH('node_version', 'Version',TH.NUMBER,sum=False))
		nodeTable.addHeader(TH('contact', 'Contact',TH.TEXT))

		self.addHiddenValue('user',user)
		domainfilter = self.processInput(self.standardInputs['domain'])
		nodefilter = self.processInput(self.standardInputs['node'])

		# TODO: ehrm.. something
		contacts = map( lambda x: (x['contact'],'%s (%d)' % (x['contact'],x['count'])), model.getAnzaContacts() )
		contactfilter = self.processInput(II('contact','Contact',II.DROPDOWN,options=contacts,allowBlank=True,blankVal=''))

		currentOpts = [('','-'),('1','Currently Seen'),('2','Currently Not Seen')]
		current = self.processInput(II('current','User Nodes',II.DROPDOWN,options=currentOpts,allowBlank=True,blankVal=''))

		invertOpts = [('','No'),('1','Yes')]
		invert = self.processInput(II('invert','Invert Result',II.DROPDOWN,options=invertOpts,allowBlank=True,blankVal=''))

		aclNodes = {}
		nodelist = []
		if user:
			for node in model.getStatmonACL(user,'node_name'):
				aclNodes[node] = True
				if current: nodelist.append(node)
		if not current: nodelist = None

		nodes = model.getNodes(
			nodefilter=nodefilter,
			nodelist=nodelist,
			domainfilter=domainfilter,
			contactfilter=contactfilter,
			orderby=nodeTable.getOrderBy(),
			invert=invert,
			invertNodelist=(current=='2'),
		)

		protected = model.getNodes(
			nodefilter=nodefilter,
			nodelist=nodelist,
			domainfilter=domainfilter,
			contactfilter=contactfilter,
			invert=not invert,
			invertNodelist=(current=='2'),
		)
		newAcl = {}
		if protected:
			self.inputHidden = False
			for node in protected:
				if aclNodes.has_key(node.node_name):
					newAcl[node.node_name] = True


		for node in nodes:
			checkname = '_%s_' % node.node_name

			old = checked = aclNodes.get(node.node_name,False)
			if updateNodes:
				checked = bool(self.getField(checkname,False))
			if checked:
				newAcl[node.node_name] = True
				node['oddevenclass'] = 'Checked'
			if not update and (old != checked):
				node['oddevenclass'] = 'Pending'

			check = ''
			if checked: check = 'checked="checked"'
			node['show_hide'] = '''<input class="checkbox" name="%s" type="checkbox" %s/>''' % (checkname, check)

			nodeTable.addRow(**node)

		if updateNodes:
			if update:
				intersect = {}
				deleted = {}
				added = {}
				union = {}
				for node in newAcl.keys():
					union[node] = True
					if aclNodes.has_key(node): intersect[node] = True
					else: added[node] = True
				for node in aclNodes.keys():
					union[node] = True
					if newAcl.has_key(node): intersect[node] = True
					else: deleted[node] = True
				self.addMessage('Node list updated: <span class="varible">%d</span> nodes affected, <span class="varible">%d</span> unchanged, <span class="varible">%d</span> added and <span class="varible">%d</span> deleted.' % (len(union),len(intersect),len(added),len(deleted)))
				model.updateStatmonACL(user,'node_name',newAcl)
			else:
				self.addMessage('Node list changes in red not applied, see above error.')

class UserStatsController(UsersController):
	_title = 'User Summary'
	_filename = 'psp/userStats.psp'

	def createContent(self):
		self.userTable = userTable = TableController(self.req,'users','User Statistic',emptyMessage='No users defined')

		linkUser = lambda x: '<a href="%s?user=%s">%s</a>' % (
			self.getControllerURI(UserController), x, x )

		userTable.addHeader(TH('user', 'User',TH.TEXT,linkUser,sorted=True))
		#userTable.addHeader(TH('access', 'Access Type',TH.HTML,dbOrder=False))
		#userTable.addHeader(TH('reg_date', 'Date Added',TH.DATE))
		#userTable.addHeader(TH('last_login', 'Last Login',TH.DATE))
		#userTable.addHeader(TH('ops', 'Operations',TH.HTML,sortable=False))
		userTable.addHeader(TH('node_count', 'File Nodes',TH.TEXT))
		userTable.addHeader(TH('extra_count', 'TDP Nodes',TH.TEXT))
		userTable.addHeader(TH('num_files_bkup', 'Files in Backup',TH.NUMBER))
		userTable.addHeader(TH('logical_bytes_bkup', 'Total Backup',TH.BYTES))
		userTable.addHeader(TH('num_files_arch', 'Files in Archive',TH.NUMBER))
		userTable.addHeader(TH('logical_bytes_arch', 'Total Archive',TH.BYTES))
		userTable.addHeader(TH('num_files_total', 'Total Files in Backup + Archive',TH.NUMBER,dbOrder=False,abbr='Total Files'))
		userTable.addHeader(TH('logical_total', 'Total Backup + Total Archive',TH.BYTES,dbOrder=False,abbr='Total Storage'))

		extraCount = configStatmonMisc.TDPSuffixes.getValue()

		stats = model.getStatmonUserStats(orderby=userTable.getOrderBy(),extraCount=extraCount)

		for row in stats:
			row['num_files_total'] = max(row['num_files_arch'],0)+max(row['num_files_bkup'],0)
			row['logical_total'] = max(row['logical_bytes_arch'],0)+max(row['logical_bytes_bkup'],0)
			userTable.addRow(**row)

