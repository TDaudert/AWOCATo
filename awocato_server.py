'''
Written by Tobias Daudert
contact: firstname.lastname [at] insight-centre [dot] org
'''
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
import base64
import json
from bson import ObjectId
import pymongo
import datetime
from SocketServer import ThreadingMixIn
import threading
import collections
import numpy as np
import re
import sys

'''
Loads the configurations as stored in configuration.json
'''
with open("configuration.json") as f:
    CONFIGURATION = json.load(f)


'''
Specifies the MongoDB settings and initialises the connection: 
Sets the database to query, the collection, the port number, and the number of items in each query
'''
MONGO_URL = "mongodb://" + CONFIGURATION["mongodb_settings"]["url"] + ":" + str(CONFIGURATION["mongodb_settings"]["port"])

'''
Specification to connect to a remote database
'''
client=pymongo.MongoClient(MONGO_URL)
db=client[CONFIGURATION["mongodb_settings"]["database"]]
col=db[CONFIGURATION["mongodb_settings"]["collection"]]

'''
Specification to connect to the localhost
'''
# client=pymongo.MongoClient("mongodb://localhost:27017")
# db=client.database_name
# col=db.collection_name

PORT_NUMBER = CONFIGURATION["port_number"]
ITEMS_PER_QUERY = CONFIGURATION["mongodb_settings"]["items_per_query"]

'''
When the user sets the consolidation mode (in the configuration.json) to true, the tool begins with an 
automatic consolidation of the annotations stored in the MongoDB collection. 
Following, the consolidators can consolidate the remaining (non-consolidated) instances by logging into the interface.
'''
ANNOTATION_MODE = CONFIGURATION["annotation_mode"]
CONSOLIDATION_MODE = CONFIGURATION["consolidation_mode"]

'''
Specifies technical variables determined in the configuration.json; the variables are self-descriptive.
'''
FIELD_NAMES_TO_QUERY = {"_id": 1}
for query_field in CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_query"]:
	FIELD_NAMES_TO_QUERY[query_field] = 1
if (CONSOLIDATION_MODE):
	FIELD_NAMES_TO_QUERY["annotations"] = 1
	FIELD_NAMES_TO_QUERY["statistics"] = 1
FIELD_NAMES_TO_QUERY["entity_spans"] = 1

ANNOTATION_IDK_VALUE = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"]
ANNOTATION_DISPLAY_TEXT = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_display_text"]

FIELDS_TO_STORE_IN = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"]
NUMBER_FIELDS_TO_STORE_IN = len(FIELDS_TO_STORE_IN)

'''
Defines mode-specific variables
'''
if (ANNOTATION_MODE == "bi-classification" or ANNOTATION_MODE == "tri-classification"):
	ANNOTATION_CLASSES = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["class_names"]
	ANNOTATION_BUTTON_SIDE = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["button_at_side"]

if (ANNOTATION_MODE == "sentiment" or ANNOTATION_MODE == "sentiment-news"):
	ANNOTATION_DISPLAY_ENTITY = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_display_entity"]

if (ANNOTATION_MODE == "sentiment-news"):
	ANNOTATION_DISPLAY_TITLE = CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_display_title"]

'''
Defines the required consolidation values; further details of these are defined in the CONFIGURATION_MANUAL.txt
'''
if (CONSOLIDATION_MODE):
	MINIMUM_ANNOTATIONS = CONFIGURATION["consolidation_settings"]["minimum_annotations"]
	STANDARD_DEVIATION = CONFIGURATION["consolidation_settings"]["standard_deviation"]
	ACCEPTED_ANNOTATORS_ID = CONFIGURATION["consolidation_settings"]["accepted_annotators"]

	if ANNOTATION_MODE == "sentiment":
		SD_RELEVANCE = CONFIGURATION["mode_settings"]["sentiment"]["standard_deviation_relevance"]
		SAME_POLARITY = CONFIGURATION["mode_settings"]["sentiment"]["same_polarity_annotation"]
		POLARITY_THRESHOLD = CONFIGURATION["mode_settings"]["sentiment"]["polarity_threshold"]
	elif ANNOTATION_MODE == "sentiment-news":
		SD_RELEVANCE = CONFIGURATION["mode_settings"]["sentiment-news"]["standard_deviation_relevance"]
		SAME_POLARITY = CONFIGURATION["mode_settings"]["sentiment-news"]["same_polarity_annotation"]
		POLARITY_THRESHOLD = CONFIGURATION["mode_settings"]["sentiment"]["polarity_threshold"]
	else:
		print ("The consolidation mode currently only supports the modi 'sentiment' and 'sentiment-news'.")
		sys.exit()

'''
Loads and encrypts the defined usernames and password into the cache at script-startup; 
each unique hash is later on used to verify the log-in credentials. 
'''
KEY = []
for accounts in CONFIGURATION["accounts"]:
	KEY.append("Basic " + str(base64.b64encode(str(accounts["username"] + ":" + accounts["password"]))))

def finishstreams(self,*args,**kw):
	try:
		if not self.wfile.closed:
			self.wfile.flush()
			self.wfile.close()
	except socket.error:
		return
	self.rfile.close()

class JSONEncoder(json.JSONEncoder):
	def default(self, o):
		if isinstance(o, ObjectId):
			return str(o)
		return json.JSONEncoder.default(self, o)

'''
Finds the specified fields in nested documents
'''
def select_fulltext(doc, fieldnames):
	return_text = ""
	for field_names in fieldnames:
		temp_text = doc
		steps = 0
		for field_name in field_names:
			if (field_name in temp_text):
				steps = steps + 1
				temp_text = temp_text[field_name]
		if (steps == len(field_names)):
			return_text = temp_text
	return return_text

def highlight_consolidation_text(text,spans):
	sub = r"<mark>\1</mark>"
	for span in spans:
		pattern = re.compile("(" + re.escape(span) + ")")
		text = re.sub(pattern, sub, text)
	return text

def consolidate_text_spans(temp_spans_unfiltered):
	temp_spans = []
	temp_spans_noduplicate = []
	temp_spans_unfiltered_for_modification = temp_spans_unfiltered[:]
	for x in temp_spans_unfiltered:
		opt_substring_check_bool = True
		duplicate_check_bool = True
		for string1 in temp_spans:
			if x == string1:
				duplicate_check_bool = False
				opt_substring_check_bool = False
			elif x in string1:
				opt_substring_check_bool = False
		popitem = temp_spans_unfiltered_for_modification.pop(0)
		for string2 in temp_spans_unfiltered_for_modification:
			if x == string2:
				duplicate_check_bool = False
				opt_substring_check_bool = False
			elif x in string2:
				opt_substring_check_bool = False
		if duplicate_check_bool == True:
			temp_spans_noduplicate.append(x)
			if opt_substring_check_bool == True:
				temp_spans.append(x)
	return temp_spans,temp_spans_noduplicate

def prep_annotations(doc):
	returnlist = []
	if "entity_spans" in doc:
		for i in range(len(doc["entity_spans"])):
			JSON_annotations = {}
			JSON_annotations["sentiment_standard_deviation"] = round(doc["statistics"][i]["sentiment_standard_deviation"],4)
			JSON_annotations["relevance_standard_deviation"] = round(doc["statistics"][i]["relevance_standard_deviation"],4)
			JSON_annotations["sentiment_mean"] = round(doc["statistics"][i]["sentiment_mean"],4)
			JSON_annotations["relevance_mean"] = round(doc["statistics"][i]["relevance_mean"],4)
			JSON_annotations["text_spans_consolidated"] = doc["statistics"][i]["text_spans_consolidated"]
			JSON_annotations["annotations_sentiment"] = doc["statistics"][i]["annotations_sentiment"]
			JSON_annotations["annotations_relevance"] = doc["statistics"][i]["annotations_relevance"]
			JSON_annotations["majority_polarity"] = doc["statistics"][i]["majority_polarity"]
			if CONSOLIDATION_MODE:
				if "title_spans_consolidated" in doc["statistics"][i]:
					JSON_annotations["title_spans_consolidated"] = doc["statistics"][i]["title_spans_consolidated"]
			returnlist.append(JSON_annotations)
	else:
		i = 0
		JSON_annotations = {}
		JSON_annotations["sentiment_standard_deviation"] = round(doc["statistics"][i]["sentiment_standard_deviation"],4)
		JSON_annotations["relevance_standard_deviation"] = round(doc["statistics"][i]["relevance_standard_deviation"],4)
		JSON_annotations["sentiment_mean"] = round(doc["statistics"][i]["sentiment_mean"],4)
		JSON_annotations["relevance_mean"] = round(doc["statistics"][i]["relevance_mean"],4)
		JSON_annotations["text_spans_consolidated"] = doc["statistics"][i]["text_spans_consolidated"]
		JSON_annotations["annotations_sentiment"] = doc["statistics"][i]["annotations_sentiment"]
		JSON_annotations["annotations_relevance"] = doc["statistics"][i]["annotations_relevance"]
		JSON_annotations["majority_polarity"] = doc["statistics"][i]["majority_polarity"]
		if CONSOLIDATION_MODE:
			if "title_spans_consolidated" in doc["statistics"][i]:
				JSON_annotations["title_spans_consolidated"] = doc["statistics"][i]["title_spans_consolidated"]
		returnlist.append(JSON_annotations)
	return returnlist

def querydata(uid):
	returnJSON = []
	if (CONSOLIDATION_MODE):
		cursor = col.find({"consolidated_by": {"$nin": [uid,99999]}},FIELD_NAMES_TO_QUERY).limit(ITEMS_PER_QUERY)
		for doc in cursor:
			if (ANNOTATION_MODE == "sentiment"):
				JSON_annotations = prep_annotations(doc)
				for i_t, prepdoc in enumerate(JSON_annotations):
					returnJSON.append({"_id": doc["_id"], "text": highlight_consolidation_text(select_fulltext(doc,ANNOTATION_DISPLAY_TEXT),prepdoc["text_spans_consolidated"]), "entity": select_fulltext(doc,ANNOTATION_DISPLAY_ENTITY), "annotations": prepdoc})
			elif (ANNOTATION_MODE == "sentiment-news"):
				JSON_annotations = prep_annotations(doc)
				for i_t, prepdoc in enumerate(JSON_annotations):
					returnJSON.append({"_id": doc["_id"], "text": highlight_consolidation_text(select_fulltext(doc["entity_spans"][i_t],ANNOTATION_DISPLAY_TEXT),prepdoc["text_spans_consolidated"]), "title": highlight_consolidation_text(select_fulltext(doc,ANNOTATION_DISPLAY_TITLE),prepdoc["text_spans_consolidated"]), "entity": select_fulltext(doc["entity_spans"][i_t],ANNOTATION_DISPLAY_ENTITY), "annotations": prepdoc})
			else:
				doc_text = select_fulltext(doc,ANNOTATION_DISPLAY_TEXT)
				returnJSON.append({"_id": doc["_id"], "text": doc_text})

	else:
		cursor = col.find({"annotated_by": {"$nin": [uid]}},FIELD_NAMES_TO_QUERY).limit(ITEMS_PER_QUERY)
		for doc in cursor:
			if (ANNOTATION_MODE == "sentiment"):
				returnJSON.append({"_id": doc["_id"], "text": select_fulltext(doc,ANNOTATION_DISPLAY_TEXT), "entity": select_fulltext(doc,ANNOTATION_DISPLAY_ENTITY)})
			elif (ANNOTATION_MODE == "sentiment-news"):
				doc_title = select_fulltext(doc,ANNOTATION_DISPLAY_TITLE)
				for item in doc["entity_spans"]:
					returnJSON.append({"_id": doc["_id"], "text": select_fulltext(item,ANNOTATION_DISPLAY_TEXT), "title": doc_title, "entity": select_fulltext(item,ANNOTATION_DISPLAY_ENTITY)})
			else:
				doc_text = select_fulltext(doc,ANNOTATION_DISPLAY_TEXT)
				returnJSON.append({"_id": doc["_id"], "text": doc_text})
	return returnJSON

def get_maxannotations():
	return col.find().count()

def get_userprogress(uid):
	if (CONSOLIDATION_MODE):
		userprogress = col.find({"consolidated_by": {"$in": [uid,99999]}},{"_id": 1}).count()
	else:
		userprogress = col.find({"annotated_by": uid},{"_id": 1}).count()
	return userprogress

def update_database_annotation(_id,value1,value2,entity,spans,uid,currenttime):
	JSONannotation = {"userid": uid, "username": CONFIGURATION["accounts"][uid]["username"]}
	if (NUMBER_FIELDS_TO_STORE_IN == 1):
		JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]] = value1
	else:
		JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]] = value1
		JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]] = value2
	if (entity != ""):
		JSONannotation["entity"] = entity
	if (spans != ""):
		JSONannotation["spans"] = spans
	JSONannotation["timestamp"] = currenttime
	col.update({"_id": ObjectId(_id)}, {"$push": {"annotations": JSONannotation}, "$addToSet": {"annotated_by": uid}})

def update_database_consolidation(_id,value1,value2,entity,spans,spans_consolidated,uid,currenttime):
	JSONannotation = {"userid": uid, "username": CONFIGURATION["accounts"][uid]["username"]}
	if (NUMBER_FIELDS_TO_STORE_IN == 1):
		JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0] + "_consolidated"] = value1
	else:
		JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0] + "_consolidated"] = value1
		JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1] + "_consolidated"] = value2
	if (entity != ""):
		JSONannotation["entity"] = entity
	if (spans != ""):
		JSONannotation["text_spans"] = spans
	if (spans_consolidated != ""):
		JSONannotation["text_spans_consolidated"] = spans_consolidated
	JSONannotation["timestamp"] = currenttime
	col.update({"_id": ObjectId(_id)}, {"$push": {"consolidations": JSONannotation}, "$addToSet": {"consolidated_by": uid}})

'''
Consolidates all annotated documents - returns an error in case some are not annotated
'''
def consolidate_data():
	consol_cursor = col.find({"consolidated_by": {"$nin": [99998,99999]}},FIELD_NAMES_TO_QUERY)
	if (consol_cursor.count() > 0):
		if (ANNOTATION_MODE == "sentiment"):
			print ("Mode: "+ str(ANNOTATION_MODE))
			for cdoc in consol_cursor:
				JSON_consolidation = {}
				annotator_set = []
				temp_sentiments = []
				temp_relevances = []
				JSON_consolidation["annotations_sentiment"] = {}
				JSON_consolidation["annotations_relevance"] = {}
				temp_spans_unfiltered = []
				try:
					for an in cdoc["annotations"]:
						if an["userid"] not in annotator_set and an["userid"] in ACCEPTED_ANNOTATORS_ID:
							annotator_set.append(int(an["userid"]))
							if (NUMBER_FIELDS_TO_STORE_IN == 1):
								if an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]] != CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"]:
									JSON_consolidation["annotations_sentiment"][str(an["userid"])] = (float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
									temp_sentiments.append(float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
							else:
								if an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]] != CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"] and an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]] != CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"]:
									JSON_consolidation["annotations_sentiment"][str(an["userid"])] = (float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
									JSON_consolidation["annotations_relevance"][str(an["userid"])] = (float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]]))
									temp_sentiments.append(float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
									temp_relevances.append(float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]]))
							if "spans" in an:
								for sp in an["spans"]:
									temp_spans_unfiltered.append(sp["text_span"].strip())
					JSON_consolidation["sentiment_standard_deviation"] = np.std(temp_sentiments)
					JSON_consolidation["relevance_standard_deviation"] = np.std(temp_relevances)
					JSON_consolidation["sentiment_mean"] = np.mean(temp_sentiments)
					JSON_consolidation["relevance_mean"] = np.mean(temp_relevances)
					JSON_consolidation["text_spans_consolidated"], JSON_consolidation["text_spans_unique"] = consolidate_text_spans(temp_spans_unfiltered)
					JSON_consolidation["annotations_sentiment"] = collections.OrderedDict(sorted(JSON_consolidation["annotations_sentiment"].items()))
					JSON_consolidation["annotations_relevance"] = collections.OrderedDict(sorted(JSON_consolidation["annotations_relevance"].items()))
					#Check polarity of the annotations
					polarity_counts = {"pos":0,"neu":0,"neg":0}
					for ts in temp_sentiments:
						if ((ts >= 0.0) and (ts < POLARITY_THRESHOLD)) or ((ts < 0.0) and (ts > (0.0 - POLARITY_THRESHOLD))):
							polarity_counts["neu"] += 1
						elif ts < 0.0:
							polarity_counts["neg"] += 1
						elif ts > 0.0:
							polarity_counts["pos"] += 1
					#Determine if majority is pos/neg/neu
					JSON_consolidation["majority_polarity"] = max(polarity_counts.iterkeys(), key=(lambda key: polarity_counts[key]))
					#Check elegibility for auto-consolidation
					if ((len(temp_sentiments) >= MINIMUM_ANNOTATIONS) and (JSON_consolidation["sentiment_standard_deviation"] < STANDARD_DEVIATION) and (JSON_consolidation["relevance_standard_deviation"] < SD_RELEVANCE) and ((polarity_counts["pos"] >= SAME_POLARITY) or (polarity_counts["neu"] >= SAME_POLARITY) or (polarity_counts["neg"] >= SAME_POLARITY))):
						#Eligible for auto-consolidation
						JSONannotation = {"userid": 99999, "username": "auto-consolidation"}
						if (NUMBER_FIELDS_TO_STORE_IN == 1):
							JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0] + "_consolidated"] = JSON_consolidation["sentiment_mean"]
						else:
							JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0] + "_consolidated"] = JSON_consolidation["sentiment_mean"]
							JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1] + "_consolidated"] = JSON_consolidation["relevance_mean"]
						JSONannotation["timestamp"] = datetime.datetime.utcnow().isoformat()

						col.update({"_id": cdoc["_id"]},{"$push": {"statistics": JSON_consolidation, "consolidations": JSONannotation}, "$addToSet": {"consolidated_by": 99999}})
					else:
						#Do not auto-consolidate!
						col.update({"_id": cdoc["_id"]},{"$push": {"statistics": JSON_consolidation}, "$addToSet": {"consolidated_by": 99998}})
				except:
					print ("ERROR in Consolidation - Not all documents are annotated")
					sys.exit()
		elif (ANNOTATION_MODE == "sentiment-news"):
			print ("Mode: "+ str(ANNOTATION_MODE))
			for cdoc in consol_cursor:
				JSON_consolidation_t = {}
				annotator_set = {}
				temp_sentiments = {}
				temp_relevances = {}
				JSON_consolidation_t["annotations_sentiment"] = {}
				JSON_consolidation_t["annotations_relevance"] = {}
				temp_spans_unfiltered = {}
				temp_title_spans_unfiltered = {}
				try:
					for an in cdoc["annotations"]:
						if an["entity"] not in annotator_set:
							annotator_set[an["entity"]] = []
							temp_sentiments[an["entity"]] = []
							temp_relevances[an["entity"]] = []
							temp_spans_unfiltered[an["entity"]] = []
							temp_title_spans_unfiltered[an["entity"]] = []
							JSON_consolidation_t["annotations_sentiment"][an["entity"]] = {}
							if (NUMBER_FIELDS_TO_STORE_IN > 1):
								JSON_consolidation_t["annotations_relevance"][an["entity"]] = {}
						if an["userid"] not in annotator_set[an["entity"]] and an["userid"] in ACCEPTED_ANNOTATORS_ID:
							annotator_set[an["entity"]].append(int(an["userid"]))
							if (NUMBER_FIELDS_TO_STORE_IN == 1):
								if an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]] != CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"]:
									JSON_consolidation_t["annotations_sentiment"][an["entity"]][str(an["userid"])] = (float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
									temp_sentiments[an["entity"]].append(float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
							else:
								if an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]] != CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"] and an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]] != CONFIGURATION["mode_settings"][ANNOTATION_MODE]["interface_settings"]["idontknow_value"]:
									JSON_consolidation_t["annotations_sentiment"][an["entity"]][str(an["userid"])] = (float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
									JSON_consolidation_t["annotations_relevance"][an["entity"]][str(an["userid"])] = (float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]]))
									temp_sentiments[an["entity"]].append(float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0]]))
									temp_relevances[an["entity"]].append(float(an[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1]]))
							if "spans" in an:
								for sp in an["spans"]:
									if "text_span" in sp:
										temp_spans_unfiltered[an["entity"]].append(sp["text_span"].strip())
									elif "title_span" in sp:
										temp_title_spans_unfiltered[an["entity"]].append(sp["title_span"].strip())
					for ent in annotator_set.keys():
						JSON_consolidation = {}
						JSON_consolidation["entity"] = ent
						if (NUMBER_FIELDS_TO_STORE_IN > 1):
							JSON_consolidation["annotations_relevance"] = JSON_consolidation_t["annotations_relevance"][ent]
						JSON_consolidation["annotations_sentiment"] = JSON_consolidation_t["annotations_sentiment"][ent]
						JSON_consolidation["sentiment_standard_deviation"] = np.std(temp_sentiments[ent])
						JSON_consolidation["relevance_standard_deviation"] = np.std(temp_relevances[ent])
						JSON_consolidation["sentiment_mean"] = np.mean(temp_sentiments[ent])
						JSON_consolidation["relevance_mean"] = np.mean(temp_relevances[ent])
						JSON_consolidation["text_spans_consolidated"], JSON_consolidation["text_spans_unique"] = consolidate_text_spans(temp_spans_unfiltered[ent])
						JSON_consolidation["title_spans_consolidated"], JSON_consolidation["title_spans_unique"] = consolidate_text_spans(temp_title_spans_unfiltered[ent])
						JSON_consolidation["all_spans_consolidated"], JSON_consolidation["all_spans_unique"] = consolidate_text_spans(temp_spans_unfiltered[ent] + temp_title_spans_unfiltered[ent])
						JSON_consolidation["annotations_sentiment"] = collections.OrderedDict(sorted(JSON_consolidation["annotations_sentiment"].items()))
						JSON_consolidation["annotations_relevance"] = collections.OrderedDict(sorted(JSON_consolidation["annotations_relevance"].items()))
						#Check polarity of the annotations
						polarity_counts = {"pos":0,"neu":0,"neg":0}
						for ts in temp_sentiments[ent]:
							if ((ts >= 0.0) and (ts < POLARITY_THRESHOLD)) or ((ts < 0.0) and (ts > (0.0 - POLARITY_THRESHOLD))):
								polarity_counts["neu"] += 1
							elif ts < 0.0:
								polarity_counts["neg"] += 1
							elif ts > 0.0:
								polarity_counts["pos"] += 1
						#Determine if majority if pos/neg/neu
						JSON_consolidation["majority_polarity"] = max(polarity_counts.iterkeys(), key=(lambda key: polarity_counts[key]))
						#Check elegibility for auto-consolidation
						if ((len(temp_sentiments[ent]) >= MINIMUM_ANNOTATIONS) and (JSON_consolidation["sentiment_standard_deviation"] < STANDARD_DEVIATION) and (JSON_consolidation["relevance_standard_deviation"] < SD_RELEVANCE) and ((polarity_counts["pos"] >= SAME_POLARITY) or (polarity_counts["neu"] >= SAME_POLARITY) or (polarity_counts["neg"] >= SAME_POLARITY))):
							#Eligible for auto-consolidation
							JSONannotation = {"userid": 99999, "username": "auto-consolidation", "entity": ent}
							if (NUMBER_FIELDS_TO_STORE_IN == 1):
								JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0] + "_consolidated"] = JSON_consolidation["sentiment_mean"]
							else:
								JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][0] + "_consolidated"] = JSON_consolidation["sentiment_mean"]
								JSONannotation[CONFIGURATION["mode_settings"][ANNOTATION_MODE]["data_specifications"]["fields_to_store_in"][1] + "_consolidated"] = JSON_consolidation["relevance_mean"]
							JSONannotation["timestamp"] = datetime.datetime.utcnow().isoformat()

							col.update({"_id": cdoc["_id"]},{"$push": {"statistics": JSON_consolidation, "consolidations": JSONannotation}, "$addToSet": {"consolidated_by": 99999}})
						else:
							#Do not auto-consolidate!
							col.update({"_id": cdoc["_id"]},{"$push": {"statistics": JSON_consolidation}, "$addToSet": {"consolidated_by": 99998}})
				except:
					print ("ERROR in Consolidation - Not all documents are annotated")
					sys.exit()
		else:
			print ("Consolidation completed")
	else:
		print ("No Documents queried in database; double-check the field names in your db and the configuration file.")

'''
This class will handle any incoming request from the browser
'''
class myHandler(BaseHTTPRequestHandler):
	def do_HEAD(self):
		print ("send header")
		self.send_response(200)
		self.send_header("Content-type", "text/html")
		self.end_headers()
		return

	def do_AUTHHEAD(self):
		print ("send header")
		self.send_response(401)
		self.send_header("WWW-Authenticate", "Basic realm=\"Test\"")
		self.send_header("Content-type", "text/html")
		self.end_headers()

	def do_GET(self):
		global KEY
		global USERID
		if self.headers.getheader("Authorization") == None:
			self.do_AUTHHEAD()
			self.wfile.write("no auth header received")
			return
		elif (self.headers.getheader("Authorization") in KEY):
			USERID = KEY.index(self.headers.getheader("Authorization"))
			if (((self.path=="/") or ((self.path=="/start.html"))) and (CONFIGURATION["guideline_at_start"] == True)):
				if (CONSOLIDATION_MODE):
					self.path="/cstart.html"
				else:
					self.path="/start.html"
			else:
				if (CONSOLIDATION_MODE):
					if (self.path=="/index.html"):
						if (ANNOTATION_MODE == "sentiment"):
							self.path="/csentiment.html"
						elif (ANNOTATION_MODE == "sentiment-news"):
							self.path="/csentiment_news.html"
						elif (ANNOTATION_MODE == "bi-classification"):
							if (ANNOTATION_BUTTON_SIDE == True):
								self.path="/cbiclassification_side.html"
							else:
								self.path="/cbiclassification.html"
						elif (ANNOTATION_MODE == "tri-classification"):
							if (ANNOTATION_BUTTON_SIDE == True):
								self.path="/ctriclassification_side.html"
							else:
								self.path="/ctriclassification.html"
						elif (ANNOTATION_MODE == "quadri-classification"):
							self.path="/cquadriclassification.html"
						elif (ANNOTATION_MODE == "quinque-classification"):
							self.path="/cquinqueclassification.html"
						elif (ANNOTATION_MODE == "textual-annotation"):
							self.path="/ctextualannotation.html"
				else:
					if (self.path=="/index.html"):
						if (ANNOTATION_MODE == "sentiment"):
							self.path="/sentiment.html"
						elif (ANNOTATION_MODE == "sentiment-news"):
							self.path="/sentiment_news.html"
						elif (ANNOTATION_MODE == "bi-classification"):
							if (ANNOTATION_BUTTON_SIDE == True):
								self.path="/biclassification_side.html"
							else:
								self.path="/biclassification.html"
						elif (ANNOTATION_MODE == "tri-classification"):
							if (ANNOTATION_BUTTON_SIDE == True):
								self.path="/triclassification_side.html"
							else:
								self.path="/triclassification.html"
						elif (ANNOTATION_MODE == "quadri-classification"):
							self.path="/quadriclassification.html"
						elif (ANNOTATION_MODE == "quinque-classification"):
							self.path="/quinqueclassification.html"
						elif (ANNOTATION_MODE == "textual-annotation"):
							self.path="/textualannotation.html"
			try:
				sendReply = False
				if self.path.endswith(".html"):
					mimetype="text/html"
					sendReply = True
				if self.path.endswith(".jpg"):
					mimetype="image/jpg"
					sendReply = True
				if self.path.endswith(".png"):
					mimetype="image/png"
					sendReply = True
				if self.path.endswith(".gif"):
					mimetype="image/gif"
					sendReply = True
				if self.path.endswith(".js"):
					mimetype="application/javascript"
					sendReply = True
				if self.path.endswith(".css"):
					mimetype="text/css"
					sendReply = True

				if sendReply == True:
					f = open(curdir + sep + "resources/" + self.path) 
					self.send_response(200)
					self.send_header("Content-type",mimetype)
					self.end_headers()
					self.wfile.write(f.read())
					f.close()
				return
			except IOError:
				self.send_error(404,"File Not Found: %s" % self.path)
			return
		else:
			self.do_AUTHHEAD()
			self.wfile.write("You are not authenticated")
			return

	def do_POST(self):
		global KEY
		global USERID
		if self.headers.getheader("Authorization") == None:
			self.do_AUTHHEAD()
			self.wfile.write("no auth header received")
			return
		elif (self.headers.getheader("Authorization") in KEY):
			USERID = KEY.index(self.headers.getheader("Authorization"))
			sendData = False
			if self.path=="/":
				if CONFIGURATION["guideline_at_start"] == True:
					if (CONSOLIDATION_MODE):
						self.path="/cstart.html"
					else:
						self.path="/start.html"
			elif (self.path=="/data"):
				sendData = True
				maximum_annotations = get_maxannotations()
				user_progress = get_userprogress(USERID)
				if (CONSOLIDATION_MODE):
					#Consolidator requests data
					if maximum_annotations == user_progress:
						JSONtobesend = "finished"
					else:
						JSONreceived = json.loads(self.rfile.read(int(self.headers.getheader("Content-Length"))))
						annotationdata = querydata(USERID)
						if (JSONreceived == True):
							if ((ANNOTATION_MODE == "sentiment") or (ANNOTATION_MODE == "sentiment-news") or (ANNOTATION_MODE == "textual-annotation")):
								JSONtobesend = JSONEncoder().encode({"maximum_annotations": maximum_annotations, "progress": user_progress, "idontknow_value": ANNOTATION_IDK_VALUE, "content": annotationdata})
							else:
								JSONtobesend = JSONEncoder().encode({"maximum_annotations": maximum_annotations, "progress": user_progress,  "idontknow_value": ANNOTATION_IDK_VALUE, "content": annotationdata, "annotation_classes": ANNOTATION_CLASSES})
						else:
							JSONtobesend = JSONEncoder().encode({"content": annotationdata})
				else:
					#Annotator requests data
					if maximum_annotations == user_progress:
						JSONtobesend = "finished"
					else:
						JSONreceived = json.loads(self.rfile.read(int(self.headers.getheader("Content-Length"))))
						annotationdata = querydata(USERID)
						if (JSONreceived == True):
							if ((ANNOTATION_MODE == "sentiment") or (ANNOTATION_MODE == "sentiment-news") or (ANNOTATION_MODE == "textual-annotation")):
								JSONtobesend = JSONEncoder().encode({"maximum_annotations": maximum_annotations, "progress": user_progress, "idontknow_value": ANNOTATION_IDK_VALUE, "content": annotationdata})
							else:
								JSONtobesend = JSONEncoder().encode({"maximum_annotations": maximum_annotations, "progress": user_progress,  "idontknow_value": ANNOTATION_IDK_VALUE, "content": annotationdata, "annotation_classes": ANNOTATION_CLASSES})
						else:
							JSONtobesend = JSONEncoder().encode({"content": annotationdata})
			elif (self.path=="/annotation"):
				sendData = True
				JSONtobesend = "ok"
				JSONreceived = json.loads(self.rfile.read(int(self.headers.getheader("Content-Length"))))
				if ("entity" in JSONreceived):
					t_entity = JSONreceived["entity"]
				else:
					t_entity = ""
				if ("spans" in JSONreceived):
					if (len(JSONreceived["spans"]) > 0):
						t_spans = JSONreceived["spans"]
					else:
						t_spans = ""
				else:
					t_spans = ""
				current_timestamp = datetime.datetime.utcnow().isoformat()
				update_database_annotation(JSONreceived["_id"],JSONreceived["value1"],JSONreceived["value2"],t_entity,t_spans,USERID,current_timestamp)
			elif (self.path=="/consolidation"):
				sendData = True
				JSONtobesend = "ok"
				JSONreceived = json.loads(self.rfile.read(int(self.headers.getheader("Content-Length"))))
				if ("entity" in JSONreceived):
					t_entity = JSONreceived["entity"]
				else:
					t_entity = ""
				if ("spans" in JSONreceived):
					if (len(JSONreceived["spans"]) > 0):
						t_spans = JSONreceived["spans"]
					else:
						t_spans = ""
				else:
					t_spans = ""
				if ("spans_consolidated" in JSONreceived):
					if (len(JSONreceived["spans_consolidated"]) > 0):
						t_spans_consolidated = JSONreceived["spans_consolidated"]
					else:
						t_spans_consolidated = ""
				else:
					t_spans_consolidated = ""
				current_timestamp = datetime.datetime.utcnow().isoformat()
				update_database_consolidation(JSONreceived["_id"],JSONreceived["value1"],JSONreceived["value2"],t_entity,t_spans,t_spans_consolidated,USERID,current_timestamp)
			else:
				self.path="/index.html"
			try:
				sendReply = False
				if self.path.endswith(".html"):
					mimetype="text/html"
					sendReply = True
				if self.path.endswith(".jpg"):
					mimetype="image/jpg"
					sendReply = True
				if self.path.endswith(".gif"):
					mimetype="image/gif"
					sendReply = True
				if self.path.endswith(".js"):
					mimetype="application/javascript"
					sendReply = True
				if self.path.endswith(".css"):
					mimetype="text/css"
					sendReply = True

				if sendReply == True:
					#Open the static file requested and send it
					f = open(curdir + sep + "resources/" + self.path) 
					self.send_response(200)
					self.send_header("Content-type",mimetype)
					self.end_headers()
					self.wfile.write(f.read())
					f.close()
				elif sendData == True: 
					self.send_response(200)
					if (JSONtobesend == "finished"):
						self.send_header("Content-type","text/html")
						self.end_headers()
						self.wfile.write(JSONtobesend)
					elif (JSONtobesend == "ok"):
						self.end_headers()
					else:
						self.send_header("Content-type","application/json")
						self.end_headers()
						self.wfile.write(JSONtobesend)
				return
			except IOError:
				self.send_error(404,"File Not Found: %s" % self.path)
			return
		else:
			self.do_AUTHHEAD()
			self.wfile.write("You are not authenticated")
			return

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
	'''Handle requests in a separate thread.'''

'''
Run consolidation of consolidation mode is true
'''
if CONSOLIDATION_MODE == True:
	print ("Consolidating data...")
	consolidate_data()

try:
	server = ThreadedHTTPServer(("", PORT_NUMBER), myHandler)
	print ("Starting server, use <Ctrl-C> to stop")
	print ("Started httpserver on port " , PORT_NUMBER)
	server.serve_forever()

except KeyboardInterrupt:
	print ("^C received, shutting down the web server")
	server.socket.close()