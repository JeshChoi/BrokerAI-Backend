from flask import Flask, request, Response
from flask_cors import CORS, cross_origin
from webcrawler import ResearchHall
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webcrawler import CrawlerTools
import threading

from flask import current_app


import os

from dotenv import load_dotenv
from openai import OpenAI

import time
import json

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from flask import Flask, render_template, request, Response, send_file, jsonify
from flask_cors import CORS, cross_origin
from bson import json_util

from download_foodhalls_as_csv import get_csv

load_dotenv(".env.local")
load_dotenv()

open_ai_key = os.getenv('GPT_API_KEY')
gpt_client = OpenAI(api_key=open_ai_key)

mongo_uri = os.getenv("MONGO_CONNECTION")
mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
mongodb = mongo_client.brokerai
foodhall_collection = mongodb["foodhalls_csv"]

try:
    mongo_client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

app = Flask(__name__)

@app.get("/download_csv")
@cross_origin()
def download_csv():
    # with open("outputs/Adjacency.csv") as fp:
    #     csv = fp.read()
    csv = get_csv()[0]

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=foodhalls.csv"})

@app.get("/api/foodhalls/count")
@cross_origin()
def get_foodhalls_count():
    """Returns number of foodhalls in mongodb
    """
    foodhall_count = foodhall_collection.count_documents({})

    res = jsonify({
        "foodhalls_count": foodhall_count
    })
    res.status_code = 200
    print(res)

    return res

@app.get("/api/foodhalls/")
@cross_origin()
def get_foodhalls():
    """Returns foods hall in the database. Limit of limit, offset by offset
    REQUEST body: 
        {
            limit: int, 
            offset: int,
        }
    """
    limit = request.args.get('limit', default=10, type=int)  # Default to 10 if not provided
    offset = request.args.get('offset', default=0, type=int) # Default to 0 if not provided
    foodhalls_cursor  = foodhall_collection.find().sort('updatedAt', -1).skip(offset).limit(limit)
    foodhalls = list(foodhalls_cursor)
    
    # Convert the list of MongoDB objects to a JSON string and then back to a dictionary
    # This is because MongoDB objects might not be directly serializable to JSON
    foodhalls_json = json.loads(json_util.dumps(foodhalls))
    res = jsonify({
        "foodhalls": foodhalls_json
    })
    res.status_code = 200
    print(res)

    return res

@app.get("/crawler/new/<search_key>")
@cross_origin()
def start_new_crawl(search_key, source = None):
    def task(search_key: str): 
        hall = ResearchHall.ResearchHall(foodhall_collection, search_key.title(), source = source)
        hall.run_in_parallel()
        print(hall)
        print("Done!")

    threading.Thread(target=task, args=(search_key,)).start()
    
    return "{ 'status': 'success' }"


def get_relevant_halls(): # fix this 
    """returns list of relevant halls"""
    options = Options()
    options.add_argument("--headless=new")
    options.page_load_strategy = 'eager'

    # Initialize browser instances
    browser = webdriver.Chrome(options=options)
    new_food_hall_article_links = CrawlerTools.scrape_google_alert(browser=browser)
    browser.quit()

    res = CrawlerTools.determine_food_halls_in_parallel(new_food_hall_article_links)
    
    return {
        "relevant_halls": res
    }

@app.get("/crawler/new_halls_today")
@cross_origin()
def get_new_halls_today():
    """Reads from Google alerts and adds food halls to database"""

    # collect list of food hall names to research
    new_hall_list = get_relevant_halls()['relevant_halls']  
    
    # number of food halls researched in an iteration 
    batch_size = 3

    # reserach iteration 
    wait_time = 60 * 6

    with app.app_context():
        count = 0
        for hall in new_hall_list:
            start_new_crawl(hall['food_hall_name'], source=hall['source'])
            count += 1
            if(count == batch_size):
                time.sleep(wait_time)
                count = 0

    # Check database for valid research 
    return jsonify({"status": "success"})

@app.route("/done")
def finish_page():
    # html
    return """
    <body style="width: 100vw; height: 100vh; display: flex; justify-content: center; align-items: center; font-size: 50px; font-family: monospace">Done</body>
    
    """


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3333)
