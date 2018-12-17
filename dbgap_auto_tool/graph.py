import json
from os.path import join

from node import Node
# from errors import UserError, DictionaryError
# from generator import generate_list_numbers

EXCLUDED_NODE = ["program", "root", "data_release"]

class Graph(object):
	"""
	Graph representation class
	"""

	def __init__(self, dictionary, program, project):
		"""
		Graph constructor

		Args:
			dictionary(DataDictionary): a dictionary instance
			program(str): program name
			project(str): project name

		Outputs:
			None
		"""
		self.dictionary = dictionary
		self.root = None
		self.program = program
		self.project = project
		self.nodes = []

	def prelimary_dictionary_check(self):
		"""
		raise exception if dictionary has not initialized yet
		"""
		if self.dictionary is None:
			raise UserError("Dictionary is not initialized!!!")
		return True

	def _get_list_of_node_names(self):
		"""
		return a list of node names
		"""
		return [k for k in self.dictionary.schema if k not in EXCLUDED_NODE]

	def generate_nodes_from_dictionary(self):
		"""
		generate nodes from dictionary

		"""
		# logger.info('Start simulating data')
		for node_name in self._get_list_of_node_names():
			node = Node(node_name, self.dictionary.schema[node_name], self.project)
			if node_name == "project":
				self.root = node
			self.nodes.append(node)
	
	def get_node_with_name(self, node_name):
		"""
		get node object given name

		Args:
			node_name(str): node name

		Outputs:
			Node: node object
		"""
		for node in self.nodes:
			if node.name == node_name:
				return node
		return None

	def _add_required_link_to_node(
		self, node, link_node_name, link_name, multiplicity=None, skip=True
	):
		"""
		assign required links to a node

		Args:
			node(Node): node object
			link_node_name(str): link node name
			multiplicity(str): link type (one_to_one, one_to_many, ..etc.)
			skip(bool): skip raising an exception to terminate

		Outputs:
			None or raise exception

		"""
		# skip all the links to Project node
		if link_node_name in EXCLUDED_NODE:
			return
		node_parent = self.get_node_with_name(link_node_name)

		if not node_parent:
			msg = "Node {} have a link to node {} which does not exist".format(
					node.name, link_node_name
				)
			if skip:
				logger.error(msg)
			else:
				raise DictionaryError(message=msg)

		node.required_links.append(
			{"node": node_parent, "multiplicity": multiplicity, "name": link_name}
		)
	
	def graph_validation(self, required_only=False):
		"""
		Call to all node validation to validate
		"""
		self.prelimary_dictionary_check()
		self.graph_required_link_validation()
		return all(
			[
				node.node_validation(required_only=required_only)[0]
				for node in self.nodes
			]
		)

	def graph_required_link_validation(self):
		"""
		Validate node links
		"""
		for node in self.nodes:
			# validate required links
			if not node.required_links and node.name != "project":
				logger.error("Node {} does not have any required link".format(node.name))

	def construct_graph_edges(self):
		"""
		Construct edges between nodes. Ignore option links
		"""

		# Link nodes together to create graph
		for node in self.nodes:
			if node == self.root:
				continue
			if not node.links:
				logger.error(
					"ERROR: {} should have at least one link to other node".format(
						node.name
					)
				)
			try:
				node_links = node.links

				if not isinstance(node_links, list):
					node_links = [node_links]

				# expect node_links contains list of links
				for link in node_links:
					if isinstance(link, dict):
						if not link.get("required"):
							continue
						if "target_type" in link:
							self._add_required_link_to_node(
								node,
								link["target_type"],
								link.get("name"),
								link.get("multiplicity"),
							)

						if "sub_group" in link or "subgroup" in link:
							sub_links = link.get("sub_group") or link.get("subgroup")
							if not isinstance(sub_links, list):
								sub_links = [sub_links]

							# just pick one of sub-group links
							for sub_link in sub_links:
								if "target_type" in sub_link:
									self._add_required_link_to_node(
										node,
										sub_link["target_type"],
										sub_link.get("name"),
										sub_link.get("multiplicity"),
									)
									break

			except TypeError as e:
				raise DictionaryError(
					"Node {} have non-list links. Detail {}".format(
						node.name, e.message
					)
				)

	def generate_submission_order_path_to_node(self, node, submission_order):
		"""
		Generate submission order so that the current node can be submitted

		Args:
			node(Node): current node object
			submission_order(list): submission order list

		Outputs:
			None

		Side effects:
			submission_order is updated interatively

		"""
		if node in submission_order:
			return
		for linked_node_dict in node.required_links:
			if linked_node_dict["node"] not in submission_order:
				self.generate_submission_order_path_to_node(
					linked_node_dict["node"], submission_order
				)
		submission_order.append(node)

	def generate_submission_order(self):
		"""
		Generate submission order for the graph
		"""
		submission_order = []
		for node in self.nodes:
			if node not in submission_order:
				path_order = []
				self.generate_submission_order_path_to_node(node, path_order)
				for item in path_order:
					if item not in submission_order:
						submission_order.append(item)

		return submission_order