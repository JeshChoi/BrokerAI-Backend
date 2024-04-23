import pandas 

from pymongo import MongoClient 

from dotenv import load_dotenv
from pymongo.server_api import ServerApi
import os 

load_dotenv(".env.local")
load_dotenv()
def get_csv():
    # look out for special characters 
    mongo_uri = os.getenv("MONGO_CONNECTION")
    mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    mongodb = mongo_client.brokerai
    col = mongodb["foodhalls_csv"]

    try:
        mongo_client.admin.command('ping')
        print("Pinged your deployment. You successfully connected to MongoDB!")
    except Exception as e:
        print(e)

    cursor = col.find()
    print ("total docs in collection:", col.count_documents( {} ))


    mongo_docs = list(cursor)

    # create an empty DataFrame obj for storing Series objects
    docs = pandas.DataFrame(columns=[])

    # iterate over the list of MongoDB dict documents
    for num, doc in enumerate( mongo_docs ):   
        # convert ObjectId() to str
        doc["_id"] = str(doc["_id"])

        # get document _id from dict
        doc_id = doc["_id"]

        # create a Series obj from the MongoDB dict
        series_obj = pandas.Series( doc, name=doc_id )

        # append the MongoDB Series obj to the DataFrame obj
        docs = docs._append( series_obj )

    # export MongoDB documents to CSV
    csv_export = docs.to_csv(sep=",") # CSV delimited by commas
    print ("\nCSV data:", csv_export)

    return [csv_export, docs]

if __name__ == '__main__':
    # export MongoDB documents to a CSV file
    get_csv()[1].to_csv("foodhalls.csv", ",") # CSV delimited by commas