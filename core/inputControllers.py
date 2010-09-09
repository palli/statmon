
from standardControllers import StandardController
from utils import DefaultDict

from random import randrange

import time
import datetime
import copy

class InputItem:
	# types
	DATE = "date"
	DROPDOWN = "dropdown"
	NUMBER = "number"
	TEXT = "text"
	PASS = "pass"

	# for sanity checks only
	TYPES = [ DATE, DROPDOWN, NUMBER, TEXT, PASS, ]

	def __init__(self,sname,name,itype,default='',options=None,allowBlank=False,blankVal=None,postProcess=None):
		assert(itype in self.TYPES)
		self.sname = sname
		self.name = name
		self.itype = itype
		self.default = default
		self.options = copy.deepcopy(options)
		self.val = None
		self.badval = False
		self.allowBlank = allowBlank
		self.blankVal = blankVal
		self.postProcess = postProcess
		
		self.selected = DefaultDict('')
		
		self.unique = randrange(10000,99999)
		
		if self.itype == self.DROPDOWN:
			if self.allowBlank:
				# check if there is empty option
				#if reduce(lambda x, y: min(x[0],y[0]), options):
				hasBlank = False
				for name,value in options:
					if not name:
						hasBlank = True
						break
				if not hasBlank:
					# add one if not
					self.options.insert(0,('',''))
			self.options = map(lambda x: (unicode(x[0]),x[1]), self.options)
			if self.default: self.default = unicode(self.default)

	def getNameClass(self):
		c = []
		if self.badval: c.append('badval')
		return ' '.join(c)

	def getValClass(self):
		c = []
		c.append(self.itype)
		return ' '.join(c)

	#def getColspan(self):
		#if self.itype == self.DATE: return '1'
		#return '2'
	
	def getTypeID(self,suffix='misc'):
		return '%s-%d-%s' % (self.sname,self.unique,suffix)

class II(InputItem):
	pass

class InputController(StandardController):
	_filename = 'psp/input.psp'
	def __init__(self,req,name=None,applyButton='Apply',defaultButton='Default',omitFormTag=False,parent=None):
		StandardController.__init__(self,req,createContent=False,parent=parent)

		self.name = name
		self.hiddenVars = {}
		self.items = []
		self.itemsMap = {}
		self.hasBadInput = False

		self.applyButton = applyButton
		self.defaultButton = defaultButton
		self.omitFormTag = omitFormTag

		self.unique = hash(name)

	def processInput(self,inputItem):
		self.items.append(inputItem)
		assert(not self.itemsMap.has_key(inputItem.sname))
		self.itemsMap[inputItem.sname] = inputItem

		return self.updateInput(inputItem.sname)

	def addHiddenValue(self,name,value):
		self.hiddenVars[name] = value

	def updateInput(self,sname,newval=None,badval=None,default=None):
		item = self.itemsMap[sname]
		if badval:
			item.badval = badval
		if default or self.getField('default%s' % self.unique):
			item.val = item.default
		elif newval == None:
			item.val = self.getField(sname,item.default)
		else:
			item.val = newval

		item.selected[item.val] = 'selected="selected"'

		if not item.val:
			if not item.allowBlank: self.hasBadInput = item.badval = True
			if item.blankVal: return item.blankVal
			if item.allowBlank: return item.val

		if item.postProcess:
			item.val = item.postProcess(item.val)

		if item.itype == II.NUMBER:
			try: item.val = int(item.val)
			except: item.val = 0

		if item.itype == II.DATE:
			item.val = self.parseDate(item.val)
			try: return datetime.datetime(*time.strptime(item.val, '%Y-%m-%d')[0:6])
			except: self.hasBadInput = item.badval = True

		if item.badval and item.default != None: return item.default
		return item.val

	def hasInputs(self):
		return len(self.items) != 0

