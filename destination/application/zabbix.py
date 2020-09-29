"""
	Module for zabbix
"""

import json
import subprocess
import socket
from datetime import datetime
from tempfile import NamedTemporaryFile
from ..base import BaseDestination

class ZabbixSendError(Exception):
	def __init__(self,popts,data,result):
		self.process_args = popts
		self.data = data
		self.result = result

	def __str__(self):
		return "Call to zabbix_sender failed. Command: ({0}) Data: ({1}) Result: ({2})".format(" ".join(self.popts), self.data, self.result)

class ZabbixItemError(Exception):
	#DO SOMETHING HERE
	pass

class ZabbixConfigError(ValueError):
	pass

class ZabbixDestination(BaseDestination):
	def __init__(self,jsonobj):
		self.results = {}
		self.zabbix_host = ""
		self.local_host = socket.getfqdn()
		self.port = 10051
		self.type = "application.zabbix"
		self.zabbix_sender = "/usr/bin/zabbix_sender"
		self.parse_config(jsonobj)

	def parse_config(self,jsonobj):
		if "Name" in jsonobj:
			self.name = jsonobj["Name"]
		else:
			raise ZabbixConfigError('Missing "Name" in zabbix destination config.')

		if "Server" in jsonobj:
			self.zabbix_host = jsonobj["Server"]
		else:
			raise ZabbixConfigError('Missing "Server" from zabbix destination config')

		if "Host" in jsonobj:
			self.local_host = jsonobj["Host"]

		if "Port" in jsonobj:
			self.port = jsonobj["Port"]

		if "SenderLocation" in jsonobj:
			self.zabbix_sender = jsonobj["SenderLocation"]

	def add_result(self,base_id,results,ts):
		for result in results:
			for (id,value) in result.items():
				try:
					for (colname, colval) in value.items():
						final_id = f'{base_id}.{colname}[{id}]'
						self.results[final_id] = [colval,ts]
				except AttributeError:
					final_id = f'{base_id}.{id}'
					self.results[final_id] = [value,ts]

	def send(self):
		with NamedTemporaryFile() as tmpfile:
			for (id,result) in self.results.items():
				tmpfile.write("{0} {1} {2} {3}\n".format(self.local_host, id, result[1], result[0]).encode())
			tmpfile.flush()
			self.call_zabbix(tmpfile.name)
		self.results = {}

	def call_zabbix(self,tmpfile):
		commandops = [self.zabbix_sender
					,'-z',self.zabbix_host
					,'-p',str(self.port)
					,'-s',self.local_host
					,'-T'
					,'-i',tmpfile]
		try:
			result = subprocess.check_output(commandops, stderr=subprocess.STDOUT)
		except subprocess.CalledProcessError as cpe:
			if cpe.returncode == 1:
				# Failed to Send
				raise ZabbixSendError(commandops, cpe.output)
			elif cpe.returncode == 2:
				# Sent fine, an item wasn't accepted (not configured/bad value/etc)
				raise ZabbixItemError("Some items failed to update. Check zabbix logs")
			else:
				# Unknown Error
				raise Exception("Unknown error occurred running zabbix_sender. Code: {0}".format(cpe.returncode))

def load(config):
	return ZabbixDestination(config)
