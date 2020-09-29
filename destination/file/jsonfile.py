"""
	Store results in a json file
"""

import json
from ..base import BaseDestination

class JsonDestination(BaseDestination):

	def __init__(self,config):
		super(JsonDestination,self).__init__(config)
		self.type = "file.json"
		self.location = "/tmp/pgmon.out"
		self.append = False
		self.parse_cfg(config)

	def parse_cfg(self,config):
		self.name = config["Name"]
		self.location = config["Location"]
		if config["Append"] == 1:
			self.apend = True


	def add_result(self,name,result,ts):
		self.results[name] = {"data":result,"ts":ts}

	def send(self):
		if self.append is True:
			mode = "a"
		else:
			mode = "w"

		with open(self.location,mode) as jf:
			json.dump(self.results,jf)

		self.results = {}
			

def load(config):
	return JsonDestination(config)
