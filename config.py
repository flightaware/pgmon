"""
	Class for storing configuration data
"""

from datetime import timedelta
from datetime import datetime
from importlib import import_module
import destination
import database
import items
import json

class PgmonConfig:
	
	def __init__(self,cfgfile=None):
		self.destinations = dict()
		self.items = dict()
		self.connections = dict()
		self.db = dict()
		self.pidfile = "/var/run/pgmon/pgmon.pid"
		self.user = "pgmon"
		self.group = "pgmon"
		self.daemon = True
		self.interval = timedelta(seconds=30)

		if cfgfile:
			with open(cfgfile,'r') as cf:
				cf = open(cfgfile,'r')
				self.parse_cfg(json.load(cf))

	def parse_cfg(self,config):
		if "Config" not in config:
			raise ValueError("Missing Config section")
		else:
			config = config["Config"]

		if isinstance(config["Destinations"], list):
			for d in config["Destinations"]:
				self.add_destination(d)
		else:
			raise TypeError('"Destinations" section must contain an array/list')

		if isinstance(config["Items"], list):
			for item in config["Items"]:
				self.add_item(item)
		else:
			raise TypeError('"Items" section must contain an array/list')

		if isinstance(config["Database"], dict):
			self.add_db(config["Database"])
		else:
			raise TypeError(' "Database" section must be a dictionary')

		if isinstance(config["Pgmon"], dict):
			if "PidFile" in config["Pgmon"]:
				self.pidfile = config["Pgmon"]["PidFile"]

			if "User" in config["Pgmon"]:
				self.user = config["Pgmon"]["User"]

			if "Group" in config["Pgmon"]:
				self.group = config["Pgmon"]["Group"]

			if "Daemon" in config["Pgmon"]:
				if config["Pgmon"]["Daemon"] != 1:
					self.daemon = False
				else:
					self.daemon = True

			if "CheckInterval" in config["Pgmon"]:
				"""
					Python 2/3 compat
				"""
				try:
					is_int = isinstance(config["Pgmon"]["CheckInterval"], (int, long))
				except NameError:
					is_int = isinstance(config["Pgmon"]["CheckInterval"], int)
				if is_int:
					if config["Pgmon"]["CheckInterval"] > 0:
						self.interval = timedelta(seconds=int(config["Pgmon"]["CheckInterval"]))
					else:
						raise ValueError("CheckInterval must be an integer greater than zero")
				else:
					raise TypeError("interval must be an integer")
		else:
			raise TypeError('"Pgmon" section must be a dictionary')

	def add_destination(self,dest,overwrite=False):
		if dest["Name"] in self.destinations and overwrite == False:
			raise ValueError('Destination {0} already exists in configuration.'.format(dest["Name"]))
		else:
			try:
				module = import_module("destination.{0}".format(dest['Type']))
				destcls = getattr(module, "load")
				self.destinations[dest["Name"]] = destcls(dest)
			except Exception as e:
				raise Exception("Unable to add destination: {exc}".format(exc=e))

	def get_destination(self,name):
		if name in self.destinations:
			return self.destinations[name]
		else:
			raise ValueError('Destination {0} does not exist in configuration.'.format(name))

	def add_item(self,item,overwrite=False):
		if item["Id"] in self.items and overwrite == False:
			raise ValueError('Item {0} already exists in configuration.'.format(item["Id"]))

		"""
			Python 2/3 compat
		"""
		try:
			is_string = isinstance(item["Destination"], basestring)
		except NameError:
			is_string = isinstance(item["Destination"], str)

		if isinstance(item["Destination"],list):
			for dest in item["Destination"]:
				if dest not in self.destinations:
					raise ValueError('Item references destination that does not exist')
		elif is_string:
			if item["Destination"] not in self.destinations:
				raise ValueError('Item references destination that does not exist')
		else:
			raise TypeError('Item destination must be a string or an array')
	
		i = items.Item(item)
		self.items[i.id] = i

	def get_item(self,id):
		if id in self.items:
			return self.items[id]
		else:
			raise ValueError('Item {0} does not exist in configuration.'.format(id))

	def add_db(self,db,overwrite=False):
		if db["Name"] in self.db and overwrite == False:
			raise ValueError('Database {0} already exists in configuration.'.format(db["Name"]))
		else:
			module = import_module("database.{0}".format(db['Type']))
			dbcls = getattr(module, "load")
			self.db = dbcls(db)

