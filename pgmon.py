"""
	The main PGMon program
"""

import os
import sys
import errno
import syslog
import random
from argparse import ArgumentParser
from datetime import datetime
from datetime import timedelta
from calendar import timegm
from time import sleep
from config import PgmonConfig
from database.base import DBConnectionError
from database import *
from daemon import *

VERSION = "1.0.0"

class CriticalError(Exception):
	"""
		Error that cannot be recovered from and needs to exit immediately.
	"""
	pass

class PGMon(Daemon):
	def __init__(self,configFile="pgmon.conf",foreground=False):
		#,appname="pyDaemon",background=True,chrootdir=None,workdir="/",umask=0,pidfile=None,uid=None,gid=None,signals=None,stdin=None,stdout=None,stderr=None
		self.appname = "pgmon"
		self.lastCheck = datetime.min
		self.checkResults = dict()
		self.dbConn = None
		self.config_file = configFile
		self.load_config()
		if foreground is True:
			self.background = False
		self.signal_map = dict({signal.SIGHUP:self.reload,signal.SIGTERM:self.close})
		super(PGMon,self).__init__(appname=self.appname,background=self.background,pidfile=self.pidfile,uid=self.uid,gid=self.gid,signals=self.signal_map)
		log_info("pgmon initialized",self.background)

	
	def run(self):
		## Run the program
		
		self.db_connect()

		while True:
			try:
				self.lastCheck = datetime.utcnow()
				if self.do_checks() > 0:
					self.send_results()
				sleep(((self.last_check + self.interval) - datetime.utcnow()).total_seconds())
			except CriticalError as exc:
				raise exc
			except DBConnectionError as exc:
				self.db_connect()
			except Exception as exc:
				log_error("{exc}".format(exc=exc),self.background)

	def db_connect(self):
		attempts = 0
		while self.dbConn.is_connected is False:
			try:
				attempts+=1
				self.dbConn.connect()
				log_info("Connected to the database",self.background)
			except DBConnectionError as exc:
				log_error("Unable to connect to the database: {exc}. Retrying".format(exc=exc),self.background)
				sleep(min(300,((2 * attempts) + (random.randint(0, 1000) / 1000.0))))

	def load_config(self):
		## load the configuration file
		try:
			config = PgmonConfig(self.config_file)
			self.background = config.daemon
			self.pidfile = config.pidfile
			self.interval = config.interval
			self.destinations = config.destinations
			self.items = config.items
			self.connections = config.connections
			self.dbConn = config.db
			self.uid = get_uid_from_name(config.user)
			self.gid = get_gid_from_name(config.group)
		except OSError as exc:
			if exc.errno == errno.ENOENT:
				raise CriticalError("Configuration file not found at {0}".format(self.config_file))
			else:
				raise CriticalError(exc)
		except TypeError as exc:
			raise CriticalError("Unable to parsse configuration: {exc}".format(exc=exc))
			

	def do_checks(self):
		## run the configured queries and return the results
		did_check = 0
		for (id,item) in self.items.items():
			if datetime.utcnow() - self.interval > item.last_check:
				try:
					item.check(self.dbConn)
					did_check+=1
					"""
						Add the results of the item check to each destionation configured.
						If the item is "MultiItem", then add the value of each column in the result and append the column name to the base item name
						Eg, if you've got an item name of "postgres.transactions" and your multiItem has a column named "committed" the destination will get "postgres.transactions.committed"
					"""
					for item_destination in item.destinations:
						self.destinations[item_destination].add_result(item.id, item.result,timegm(item.last_check.timetuple()))
				except DBConnectionError as dbe:
					log_error("Db connection lost, attempting to reconnect",self.background)
					self.db_connect()
				except Exception as e:
					ie = Exception('Unable to run check {id}: ({etype}) {exc}'.format(id=id,exc=e,etype=type(e)))
					log_error("{exc}".format(exc=ie),self.background)
			else:
				log_info("Didn't wait long enough. Skipping check {0}".format(item.id),self.background)
		self.last_check = datetime.utcnow()
		log_info("Ran {0} checks of {1} configured".format(did_check, len(self.items)),self.background)
		return did_check

	def send_results(self):
		## send the results of the check to the configured destination
		did_send = 0
		for (id,dest) in self.destinations.items():
			if dest.has_results is True:
				try:
					dest.send()
					did_send+=1
				except Exception as e:
					de = Exception('Unable to send results to {id}: {exc}'.format(id=id,exc=e))
					log_error("{exc}".format(exc=de),self.background)
			else:
				log_info("Destination {0} has no available results, skipping".format(dest.name),self.background)
		log_info("Sent items to {0} destinations of {1} configured".format(did_send, len(self.destinations)),self.background)

	def reload(self, etype=None, evalue=None, traceback=None):
		log_info("Re-reading configuration file")
		self.load_config()

	def close(self, etype=None, evalue=None, traceback=None):
		## close DB
		## terminate subprocesses
		self.dbConn.disconnect()
		super(PGMon,self).close()
		if traceback is not None:
			log_info("Exiting with error: {tb}".format(tb=traceback),self.background)
		else:
			log_info("Exiting")
		print("Exiting!")
		os._exit(0)

def init_logging(appname):
	 syslog.openlog(ident=appname,logoption=syslog.LOG_PID,facility=syslog.LOG_LOCAL0)

def log_info(message,dosyslog=True):
	if dosyslog:
		syslog.syslog(syslog.LOG_INFO,message)
	else:
		print("INFO: {0}".format(message))

def log_warn(message,dosyslog=True):
	if dosyslog:
		syslog.syslog(syslog.LOG_WARNING,message)
	else:
		print("WARN: {0}".format(message))

def log_error(message,dosyslog=True):
	if dosyslog:
		syslog.syslog(syslog.LOG_ERR,message)
	else:
		print("ERROR: {0}".format(message))


def setup_args():
	parser = ArgumentParser(description="Monitor database using a persistent connection")

	parser.add_argument (
		"-f",
		"--forground",
		action	= "store_true",
		dest	= "forground",
		help	= "Run in the forground and don't daemonize.  If specified, this overrides the configuration file",
	)

	parser.add_argument (
		"-c",
		"--config",
		action	= "store",
		dest	= "config",
		default	= "pgmon.conf",
		help	= "The location of the configuration file to load",
	)

	parser.add_argument (
		"-v",
		"--version",
		action = "version",
		version = VERSION
	)

	return parser.parse_args()
