"""
	Base class for the datbase configuration
"""

from abc import ABCMeta

class DBConnectionError(Exception):
	"""
		There was some kind of issue with the db connection
	"""
	pass

class DBQueryError(Exception):
	"""
		A query failed for some reason
	"""
	pass

class BaseDatabase(object):
	__metaclass__ = ABCMeta

	def __init__(self,db_dict):
		self.name = "postgres"
		self.type = "postgresql"
		self.host = "127.0.0.1"
		self.port = 5432
		self.user = "postgres"
		self.password = "postgres"

	@classmethod
	def connect(self):
		pass

	@classmethod
	def disconnect(self):
		pass

	@classmethod
	def query(self,string):
		pass

