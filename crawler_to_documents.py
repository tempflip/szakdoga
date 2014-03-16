from pymongo import MongoClient
from bson.objectid import ObjectId

client = MongoClient('localhost', 27017)
db = client.crawler
crawlerDB = db['crawler']
db2 = client.textMinerDB
minerDB = db2['documents'] 

crawledList = crawlerDB.find()


for d in crawledList:
	found = minerDB.find_one({'source' : d['source']})
	if (found == None):
		minerDB.insert(d)
		print '#### added: ' + d['title']
	else :
		print '!!!! already there ' + d['title']


