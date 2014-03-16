#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import json
from BeautifulSoup import BeautifulSoup
import requests
from pymongo import MongoClient
from bson.objectid import ObjectId

def get_url(url):
	r = {}
	try:
		response = requests.get(url)
		r['text'] = response.text
		r['url'] = url;
		r['status'] = 'success'
		r['status_code'] = response.status_code
	except:
		r['status'] = 'error'
	return r

def get_link_list(content):
	soup = BeautifulSoup(content)
	return [link.get('href') for link in soup.findAll('a')]	

def filtered_links(content):
	links = []
	for l in get_link_list(content):
		if("mailto:" in l) : continue
		if(l.startswith('http://')) : continue
		if(l.endswith('.pdf')) : continue
		if(l == '#') : continue

		#### napi specific
		if (l.startswith('/info/')) : continue
		if (l.startswith('/user/')) : continue
		if (l.startswith('/data/')) : continue
		if ( l.endswith('.html') == False): continue

		links.append(l)
	return links

def initialize_collection(collection):
	client = MongoClient('localhost', 27017)
	db = client.crawler
	return db[collection]

def clean_html(url):
	try :
		boilerPlateUrl = 'http://boilerpipe-web.appspot.com/extract?url={0}&extractor=ArticleExtractor&output=json&extractImages='.format(url)
		response = requests.get(boilerPlateUrl)
		if response.json()['status'] == 'error' :
			return None
		else :
			return response.json()['response']
	except:
		return None

def main():
	MAXCOUNT = 3000
	domain = 'http://www.napi.hu'
	startingPage = '/'
	startUrl = domain + startingPage

	r = get_url(startUrl)
	q = filtered_links(r['text'])

	collection = initialize_collection('crawler')

	i = 0
	for link in q :
		url = domain + link
		# if in DB
		d = collection.find_one({'source' : url});
		if (d != None) :
			print "+++ already in DB: " + url
			continue

		# getting the doc
		print "+++ GET " + url
		r = get_url(url)
		if r['status'] == 'error' or r['status_code'] != 200 :
			print '+++ ERROR'
			continue

		# cleaning text with boilerplate
		# inserting into DB
		docData = clean_html(url)
		if (docData != None) :
			collection.insert(docData)
			print docData['title'] + ' added'
		else :
			print '+++ BOILERPLATE ERROR'

		# extracting links
		try :
			links = filtered_links(r['text'])
		except:
			continue
		for newLink in links:
			if newLink in q:
				continue
			else:
				q.append(newLink)
		print '+++ Q LEN : ',
		print len(q),
		print ' # : ',
		print i
		i += 1
		if i >= MAXCOUNT : break

if __name__ == "__main__":
	main()