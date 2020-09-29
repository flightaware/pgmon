"""
	Base for destinations
"""

from abc import ABCMeta

class BaseDestination(object):
	__metaclass__ = ABCMeta

	def __init__(self,config):
		self.name = ""
		self.type = ""
		self.results = {}

	@property
	def has_results(self):
		if len(self.results) > 0:
			return True
		else:
			return False

	@classmethod
	def send(self):
		pass

	@classmethod
	def add_result(self,id,value,timestamp):
		pass

#def Destination(config):
#	print ("loading destination of type {0}".format(config['Type']))
#	module = import_module("destination.{0}".format(config['Type']))
#	return getattr(module, "load")(config)
	
