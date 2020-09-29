"""
	Send results to a http endpoint
"""

from ..base import BaseDestination
import requests
import json


class HttpConfigError(Exception):
	pass


class HttpDestination(BaseDestination):
	def __init__(self, config):
		super(HttpDestination, self).__init__(config)
		self.type = "net.http"
		self.location = "http://127.0.0.1"
		self.http_verb = "POST"
		self.persist_connection = False
		self.format = "json"
		self._verb_map = {"GET": self._get, "POST": self._post, "PUT": self._put}
		self._formatter = {"json": self.json_formatter, "csv":self.csv_formatter}
		self.parse_config(config)

	def __verb_is_valid(self, verb):
		return verb.upper() in self._verb_map.keys()

	def parse_config(self, config):
		if "Name" in config:
			self.name = config["Name"]
		else:
			raise HttpConfigError('Missing "Name" in http destination config.')

		if "Location" in config:
			self.location = config["Location"]
		else:
			raise HttpConfigError('Missing "Location" from http destination config')

		if "Format" in config:
			if config["Format"] in self._formatter.keys():
				self.format = config["Format"]
			else:
				raise HTTPConfigError(
					f"Invalid Format of {config['Format']} specified.  Must be one of {self._formatter.keys()}")

		if "Verb" in config:
			if self.__verb_is_valid(config["Verb"]):
				self.http_verb = f'{config["Verb"]}'.upper()
			else:
				raise HTTPConfigError(
					f"Invalid HTTP verb ({config['Verb']}) in config.  Must be one of {self._verb_map.keys()}"
				)

		if "PostVariable" in config:
			self.parent_key = config["PostVariable"]

		if "Persist" in config:
			self.persist_connection = config["Persist"]

	def _get(self,url,params=None):
		return requests.get(url,params=params)

	def _post(self,url,params=None):
		return requests.post(url,data=params)

	def _put(self,url,params=None):
		return requests.put(url,data=params)

	def _delete(self,url):
		# no reason to implement this
		pass

	def add_result(self, base_id, results, ts):
		self.results[base_id] = {'timestamp': ts, 'values': {}}
		for result in results:
			for (id,value) in result.items():
				self.results[base_id]['values'].update({id: value})

	def format_data(self,fmt):
		return self._formatter[fmt](self.data)

	def json_formatter(self,data):
		return json.dumps(data)

	def csv_formatter(self,data):
		return f'{f",".join(data.keys())}\n{f",".join(data.items())}'

	def send(self):
		if self.has_results is True:
			response = self.__make_request()
			if response.status_code != requests.codes.ok:
				raise HttpDestinationError(
					f"Unable to {self.http_verb} to {self.location}. Received {response.status_code} code"
				)
			else:
				print(response.json())

	def __make_request(self):
		data = {}
		if self.parent_key:
			data[self.parent_key] = self._formatter[self.format](self.results)
		else:
			data = self._formatter[self.format](self.results)
		return self._verb_map[self.http_verb](self.location, data)


def load(config):
	return HttpDestination(config)
