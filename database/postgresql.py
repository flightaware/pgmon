"""
	Interface for postgres database
"""

from .base import *
import psycopg2
import time

class PostgresDatabase(BaseDatabase):

	def __init__(self,config):
		self.name = config["Name"]
		self.type = config["Type"]
		self.host = config["Host"]
		self.port = config["Port"]
		self.user = config["Username"]
		self.password = config["Password"]
		self.statement_timeout = 10000 #10 seconds
		self._last_query_time = None

		self._dbconn = None

		DEC2FLOAT = psycopg2.extensions.new_type(
						psycopg2.extensions.DECIMAL.values,
						'DEC2FLOAT',
						lambda value, curs: float(value) if value is not None else None)
		psycopg2.extensions.register_type(DEC2FLOAT)

	@property
	def is_connected(self):
		try:
			if self._dbconn.closed == 0:
				return True
			else:
				return False
		except AttributeError:
			return False

	@property
	def query_time(self):
		return self._last_query_time

	def connect(self):
		try:
			self._dbconn = psycopg2.connect(host=self.host,port=self.port,dbname=self.name,user=self.user,password=self.password,options="-c statement_timeout={0}".format(self.statement_timeout))
			self._dbconn.autocommit = False
		except psycopg2.OperationalError as e:
			raise DBConnectionError(e)

	def disconnect(self):
		try:
			self._dbconn.rollback()
			self._dbconn.close()
		except:
			pass
		

	def query(self,query_string,multi_row=False):

		if self.is_connected is False:
			self.connect()

		try:
			output = []
			cur = self._dbconn.cursor()
			start = time.time()
			cur.execute(query_string)
			end = time.time()
			self._last_query_time = end - start
			colnames = [desc[0] for desc in cur.description]
			for r, result in enumerate(cur):
				output.append(dict(zip(colnames,result)))

		finally:
			"""
				we are only doing selects and shouldn't be modifying the database
				this ensures that, and allows future queries to happen in case one fails
			"""
			self._dbconn.rollback()
		return output

def load(config):
	return PostgresDatabase(config)
