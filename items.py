"""
	An item to check
"""

from datetime import datetime
import database


class Item(object):

	def __init__(self,item_dict):
		self.id = ""
		self.query = "select 1"
		self.destinations = []
		self._last_check = datetime.min
		self._check_result = None
		self._multi_item = False
		self._multi_row = False
		self.parse_cfg(item_dict)

	def parse_cfg(self,item_dict):
		if "Id" in item_dict:
			self.id = item_dict["Id"]
		else:
			raise ValueError("Item must contain an Id")

		if "Query" in item_dict:
			self.query = item_dict["Query"]
		else:
			raise ValueError("Item must contain a Query")

		if "Destination" in item_dict:
			"""
				Python 2/3 compat
			"""
			try:
				is_string = isinstance(item_dict["Destination"], basestring)
			except NameError:
				is_string = isinstance(item_dict["Destination"], str)

			if is_string:
				self.destinations.append(item_dict["Destination"])
			elif isinstance(item_dict["Destination"], list):
				self.destinations = item_dict["Destination"]
			else:
				raise ValueError("Destination must be a list or a single item")

		if "MultiItem" in item_dict:
			if item_dict["MultiItem"] == 1:
				self._multi_item = True
			else:
				self._multi_item = False

		if "MultiRow" in item_dict:
			"""
				Python 2/3 compat
			"""
			try:
				is_string = isinstance(item_dict["MultiRow"], basestring)
			except NameError:
				is_string = isinstance(item_dict["MultiRow"],str)

			if (is_string and item_dict["MultiRow"] != "") or (isinstance(item_dict["MultiRow"],int) and item_dict["MultiRow"] > 0):
				self._multi_row = item_dict["MultiRow"]
			else:
				raise ValueError("MultiRow must be either a string column name or integer representing the column to use for item key")

	def parse_results(self,results):
		# we need to take a row from the multi_row result, pull out the column that is going to be the id
		if self.multi_row:
			try:
				parsed_results = []
				for row in results:
					rowid = row.pop(self._multi_row)
					parsed_row = {rowid: {}}
					for key,value in row.items():
						parsed_row[rowid].update({key: value})
					parsed_results.append(parsed_row)
				return parsed_results
			except KeyError as e:
				raise Exception(f'Configured MultiRow column {self._multi_row} does not exist in the result set')
		else:
			return results

	def check(self,db):
		self._check_result = self.parse_results(db.query(self.query,self.multi_row))
		self._last_check = datetime.utcnow()

	def result(self):
		return self._check_result

	def last_check(self):
		return self._last_check

	def multi_item(self):
		return self._multi_item

	def multi_row(self):
		return self._multi_row

	last_check = property(fget=last_check)
	result = property(fget=result)
	multi_item = property(fget=multi_item)
	multi_row = property(fget=multi_row)
