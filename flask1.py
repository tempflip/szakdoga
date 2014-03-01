from flask import Flask
from flask import render_template
from flask import request

import requests
import json
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)

def initialize_collection(collection):
	client = MongoClient('localhost', 27017)
	db = client.textMinerDB
	return db[collection]

@app.route("/")
def hello():
    return render_template('start.html')

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

	return render_template('doc_get.html', docData = docData, pageMsg = pageMsg)

@app.route("/document_list")
def document_list():
	collection = initialize_collection('documents')
	documents = [d for d in collection.find()]
	count = collection.count()
	return render_template('document_list.html', documents = documents, count = count)

@app.route("/document_remove")
def document_remove():
	collection = initialize_collection('documents')

	d = collection.remove({'_id' : ObjectId(request.args.get('d'))})
	if (d == None) :
		return render_template('error.html', error = 'There is no such a document')

	return document_list()

if __name__ == "__main__":
    app.run(debug = True)


