from flask import Flask, request, render_template, url_for, redirect

import requests
import json
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

def initialize_collection(collection):
	client = MongoClient('localhost', 27017)
	db = client.textMinerDB
	return db[collection]

def document_list():
	collection = initialize_collection('documents')
	documents = [d for d in collection.find()]
	count = collection.count()
	return {'documents' : documents,
			'count' : count}

def tag_list():
	tagList = {}
	collection = initialize_collection('documents')
	for d in collection.find():
		if 'tags' in d:
			for tag in d['tags']:
				if tag in tagList:
					tagList[tag].append(d)
				else:
					tagList[tag] = [d]
	return tagList

@app.route("/fetch", methods=['POST'])
def fetch():
	collection = initialize_collection('documents')
	if request.method == 'POST':
		docUrl = request.form['url']

	# looking up, if we already have this document
	docData = collection.find_one({'source' : docUrl})
	if(docData != None):
		pageMsg = 'This is NOT a new document'
	else:
		pageMsg = 'This is a new document'
		boilerPlateUrl = 'http://boilerpipe-web.appspot.com/extract?url={0}&extractor=ArticleExtractor&output=json&extractImages='.format(docUrl)
		response = requests.get(boilerPlateUrl)
		if response.json()['status'] == 'error' :
			return render_template('error.html', error = response.json()['error'])
		docData = response.json()['response']
		print docData
		collection.insert(docData)

	#updating the tf-idf database
	tfIdf()
	return redirect(url_for('class1', d = docData['_id']))
	#return render_template('doc_get.html', docData = docData, pageMsg = pageMsg)

@app.route("/document_remove")
def document_remove():
	collection = initialize_collection('documents')
	docId = request.args.get('d')
	d = collection.remove({'_id' : ObjectId(docId)})
	if (d == None) :
		return render_template('error.html', error = 'There is no such a document')

	return redirect(url_for('class1', d = docId))

@app.route("/document_tag_add")
def document_tag_add():
	collection = initialize_collection('documents')
	docId = request.args.get('d')
	tagList = request.args.get('tag').split(',')
	d = collection.find_one({'_id' : ObjectId(docId)})
	if (d == None) :
		return render_template('error.html', error = 'There is no such a document')
	if ('tags' in d) :
		for tag in tagList:
			if (tag not in d['tags']):
				d['tags'].append(tag)
	else :
		d['tags'] = tagList
	collection.save(d)

	return redirect(url_for('class1', d = docId))

@app.route("/document_tag_remove")
def document_tag_remove():
	collection = initialize_collection('documents')
	docId = request.args.get('d')
	tag = request.args.get('tag')
	d = collection.find_one({'_id' : ObjectId(docId)})
	if (d == None) :
		return render_template('error.html', error = 'There is no such a document')
	if (tag not in d['tags']) :
		return render_template('error.html', error = 'There is no such a tag on document!')
	d['tags'].remove(tag)

	collection.save(d)

	return document_list()

def bag_of_words(words):
	return dict([word, True] for word in words)


@app.route("/class1")
def class1():
	import nltk
	from nltk.tokenize import WordPunctTokenizer
	docId = request.args.get('d')
	tokenizer = WordPunctTokenizer()		
	collection = initialize_collection('documents')

	featuresets = []
	tagSet = set()
	for d in collection.find():	
		bagOfWords = bag_of_words(tokenizer.tokenize(d['content']))
		if 'tags' not in d: continue
		for tag in d['tags']:
			featuresets.append((bagOfWords, tag))
			tagSet.add(tag)
	classifier = nltk.NaiveBayesClassifier.train(featuresets)

	d = collection.find_one({'_id' : ObjectId(docId)})

	#classifier.show_most_informative_features(100)
	cl = classifier.prob_classify(bag_of_words(tokenizer.tokenize(d['content'])))
	probs = []
	for tag in tagSet:
		probs.append((tag, round(cl.prob(tag)*100) ))
	classifier.show_most_informative_features(n=20)
	probs = sorted(probs, key = lambda x : x[1],  reverse = True)
	return render_template('class1.html', probs = probs, d=d)

@app.route("/class_tree")
def decisionTreeClassifier():
	import nltk
	from nltk.tokenize import WordPunctTokenizer
	docId = request.args.get('d')
	tokenizer = WordPunctTokenizer()		
	collection = initialize_collection('documents')

	featuresets = []
	tagSet = set()
	for d in collection.find():	
		bagOfWords = bag_of_words(tokenizer.tokenize(d['content']))
		if 'tags' not in d: continue
		for tag in d['tags']:
			featuresets.append((bagOfWords, tag))
			tagSet.add(tag)
	classifier = nltk.DecisionTreeClassifier.train(featuresets)
	print classifier.pseudocode(depth=4)
	d = collection.find_one({'_id' : ObjectId(docId)})
	print classifier.classify(bag_of_words(tokenizer.tokenize(d['content'])))
	
	return 'hello'
	"""
	#classifier.show_most_informative_features(100)
	cl = classifier.prob_classify(bag_of_words(tokenizer.tokenize(d['content'])))
	probs = []
	for tag in tagSet:
		probs.append((tag, round(cl.prob(tag)*100) ))
	classifier.show_most_informative_features(n=20)
	probs = sorted(probs, key = lambda x : x[1],  reverse = True)
	return render_template('error.html', error = 'aaa')"""

def create_idf_map():
	import nltk
	from nltk.tokenize import WordPunctTokenizer
	tokenizer = WordPunctTokenizer()		
	collection = initialize_collection('documents')

	idfMap = {}
	docs = collection.find()
	for d in docs:
		for word in tokenizer.tokenize(d['content'].lower()):
			if word not in idfMap:
				idfMap[word] = 1
			else:
				idfMap[word] += 1
	return idfMap

def generaral_frequency(idfMap):
	# general word frequency
	# input - from idfMap function
	genFreq = [(w, idfMap[w]) for w in idfMap]
	genFreq = sorted(genFreq, key = lambda x : x[1], reverse = True)	
	return genFreq

#updates the TF-IDF values in DB
@app.route("/tf_idf")
def tfIdf():
	TFIDF_MIN_SCORE = 100
	import nltk
	from nltk.tokenize import WordPunctTokenizer
	tokenizer = WordPunctTokenizer()		
	collection = initialize_collection('documents')

	docs = collection.find()
	tfidf = []
	idfMap = create_idf_map()
	docs = collection.find()
	for d in docs:
		tfMap = {}
		for word in set(tokenizer.tokenize(d['content'].lower())):
		 	if word not in tfMap:
		 		tfMap[word] = 1
		 	else:
		 		tfMap[word] += 1
		tfIdfValues = []
		for word in set(tokenizer.tokenize(d['content'].lower())):
			if (tfMap[word] * 1000 / idfMap[word]) > TFIDF_MIN_SCORE:
				tfIdfValues.append((word, tfMap[word] * 1000 / idfMap[word]))
		tfIdfValues = sorted(tfIdfValues, key = lambda x : x[1], reverse = True)
		d['tfidf'] = tfIdfValues
		tfidf.append({'d' : d,
					  'tfidf' : tfIdfValues})
		collection.save(d)


	genFreq = generaral_frequency(idfMap)
	return render_template("tfidf.html", documents = tfidf)

@app.route("/")
def hello():
	documents = document_list()
	genFreq = generaral_frequency(create_idf_map())
	tagList = tag_list()
	return render_template('start.html', 
		documents = documents['documents'], 
		count = documents['count'],
		genFreq = genFreq,
		tagList = tagList)

if __name__ == "__main__":
    app.run(debug = True)


