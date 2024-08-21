import os
import threading
from datetime import datetime
import json
from dotenv import load_dotenv

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

from webcrawler.CrawlerTools import (scrape_concerts_per_year, make_google_search, scrape_page_text, traverse_all_pages)
from webcrawler.gpt import create_client, gpt_request, aggregate_gpt_request
from webcrawler.BrowserConfig import create_browser, kill_chrome

import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(".env.local")
load_dotenv()

# Given venue name, class creation researches properties of interest
class ResearchVenue:
    def __init__(self, venue_name: str, mongo_collection, source=None):
        # MongoDB Schema
        self.venue: str = venue_name
        self.city: str = None
        self.capacity: int = None
        self.owned: str = None
        self.management: str = None
        self.number_of_stories: int = None # not found -> pretty hard to find -> ask taylor
        self.square_footage: int = None
        self.number_of_bars: int = None
        self.number_of_shows_in_2023: int = None # not found # possible source: https://www.concertarchives.org/venues/the-coach-house
        self.vip_packages_access: int = None # not found -> pretty hard to find 
        self.food_offered: bool = None
        # Sources
        self.article_source = source  # source for entry point of venue find
        self.sources = []  # contains all sources for each attribute

        # Homepage data as GPT conversation 
        self.homelink = None
        self.homepage_webpage_conversation = []
        
        # GPT client
        self.gpt_cient = create_client()

        # MongoDB connections
        self.mongo_collection = mongo_collection  # stores connection to mongodb collection
        self.mongo_venue = None  # stores mongo DB object reference

        self.run_in_parallel()
    
    def get_homepage_webpages(self, browser):
        """Populate GPT conversation log with text from webpages from the venue's original website"""
        google_links = make_google_search(f'{self.venue}', browser, 1)
        if not google_links:
            return

        google_link = google_links[0]
        self.homelink = google_link
        
        self.homepage_webpage_conversation = traverse_all_pages(google_link, browser, max_page_visits=30) 
        
    def get_city(self, browser):
        """Returns city that venue presides in"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the city that the music or theatre venue `{self.venue}` is located in.'
        format_request = 'Return the response as json: {"city": str}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} city location', browser)
        if not google_links:
            print('what the flip')
            return '{"city": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def get_capacity(self, browser) -> dict:
        """Returns the capacity of the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the capacity of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"capacity": int}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue capacity', browser, 1)
        if not google_links:
            return '{"capacity": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def get_owned(self, browser) -> dict:
        """Returns the ownership details of the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the ownership details of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"owned": str}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue ownership', browser, 1)
        if not google_links:
            return '{"owned": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def get_management(self, browser) -> dict:
        """Returns the management details of the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the management details of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"management": str}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue management', browser, 1)
        if not google_links:
            return '{"management": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def get_number_of_stories(self, browser) -> dict:
        """Returns the number of stories of the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the number of stories of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"number_of_stories": int}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue number of stories', browser, 1)
        if not google_links:
            return '{"number_of_stories": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def get_square_footage(self, browser) -> dict:
        """Returns the square footage of the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the square footage of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"square_footage": int}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue square footage', browser, 1)
        if not google_links:
            return '{"square_footage": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def get_number_of_bars(self, browser) -> dict:
        """Returns the number of bars in the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the number of bars in the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"number_of_bars": int}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue number of bars', browser, 1)
        if not google_links:
            return '{"number_of_bars": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link
    
    def get_yearly_number_of_shows(self, browser) -> dict:
        """Returns the number of shows in 20xx at the venue"""
        
        concerts_per_year, venue_link = scrape_concerts_per_year(self.venue)
        
        return concerts_per_year, venue_link

    def get_vip_packages_access(self, browser) -> dict:
        """Fetches VIP package details for the venue."""
        prompt = f'List all VIP benefits at the venue `{self.venue}`.'
        format_request = 'Return as JSON: {"vip_packages_access": str}.'

        response, conversation = aggregate_gpt_request(prompt + format_request, self.homepage_webpage_conversation)

        google_link = self.homelink
        
        return response, google_link

    def get_food_offered(self, browser) -> dict:
        """Returns whether food is offered at the venue"""
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find out if food is offered at the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"food_offered": bool}. If unable to find accurate data, set the json value to None'

        google_links = make_google_search(f'{self.venue} venue food offered', browser, 1)
        if not google_links:
            return '{"food_offered": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_cient)
        return res, google_link

    def updateDB(self, data: dict, source: dict):
        """Updates the database with the data"""
        logger.info(f"Updating database with {data.keys()}")

        # check if venue object connection is established
        if self.mongo_venue is None:
            venue = self.mongo_collection.find_one({"name": self.venue})
            if venue is not None:
                # set existing venue object
                self.mongo_venue = venue
            else:
                # create new venue in the database
                new_venue = self.mongo_collection.insert_one({'name': self.venue, 'article_source': self.article_source, 'createdAt': datetime.now(), })
                self.mongo_venue = new_venue
                pass

        # make updates to the mongodb food hall
        update_result = self.mongo_collection.update_one(
            {"name": self.venue},
            {"$set": data,
             '$currentDate': {'updatedAt': True}  # Automatically set the update timestamp
             },
        )
        logger.info(f"Updated {update_result.modified_count} document(s).")
        pass

    def browser_research(self, browser, tasks):
        """Executes a list of research tasks using the given browser instance."""
        for task in tasks:
            try:
                task_response, google_link = task(browser)
                string = None
                if isinstance(task_response, str):
                    string = task_response.replace("```json", "").replace("```", "")

                    # Debug print to check the content of the string
                    logger.info(f"Raw JSON string: {string}")
                else:
                    logger.info(f'response not a string: {task_response}')

                if string and '{"data": null}' not in string:
                    try:
                        data = json.loads(string)
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e.msg} at line {e.lineno} column {e.colno}")
                        continue

                    if "data" in data and data["data"] is None:
                        continue

                    # handles regular dict data
                    source = None
                    if google_link:
                        label_formatted = task.__name__.replace("get_", "").replace("_", " ").title()
                        self.sources.append({"source": google_link, "label": label_formatted})
                        source = {"source": google_link, "label": label_formatted}

                    logger.info(f"Parsed data: {data}, Source: {source}")
                    self.updateDB(data, source)
                elif isinstance(task_response, list):
                        for yearly_concerts in task_response: 
                            concert_data = yearly_concerts
                            source = None
                            if google_link:
                                dict_key = str(concert_data.keys())
                                self.sources.append({"source": google_link, "label": f'{dict_key}'})
                                source = {"source": google_link, "label": f'{dict_key} yearly'}

                            logger.info(f"Parsed data: {concert_data}, Source: {source}")
                            self.updateDB(concert_data, source)
                else:
                    logger.info(f"Data not found for {task.__name__}")

                self.updateDB({"sources": self.sources}, {})

            except Exception as e:
                logger.error(f"Unexpected error in task {task.__name__}: {str(e)}")


    def run_in_parallel(self):
        # Initialize browser instances
        browser1 = create_browser()
        browser2 = create_browser()
        browser3 = create_browser()
        browser4 = create_browser()

        # Define the tasks for each browser
        all_tasks = [
            self.get_city,
            self.get_homepage_webpages,
            self.get_capacity,
            self.get_owned,
            self.get_management,
            self.get_number_of_stories,
            self.get_square_footage,
            self.get_number_of_bars,
            self.get_vip_packages_access,
            self.get_food_offered,
        ]
        
        tasks1 = all_tasks[:3]
        tasks2 = all_tasks[3:6]
        tasks3 = all_tasks[6:8]
        tasks4 = all_tasks[8:]

        # Create and start threads for each set of tasks
        thread1 = threading.Thread(target=self.browser_research, args=(browser1, tasks1))
        thread2 = threading.Thread(target=self.browser_research, args=(browser2, tasks2))
        thread3 = threading.Thread(target=self.browser_research, args=(browser3, tasks3))
        thread4 = threading.Thread(target=self.browser_research, args=(browser4, tasks4))

        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()

        # Wait for all threads to complete
        thread1.join()
        thread2.join()
        thread3.join()
        thread4.join()

        # Close browsers after completing tasks
       
        browser2.quit()
        browser3.quit()
        browser4.quit()
        
        # doing this last to format at end of mongodb object and to kill off all chrome browsers
        self.browser_research(browser1, self.get_yearly_number_of_shows)
        browser1.quit()
        kill_chrome()

    def __str__(self):
        """
        Returns a string representation of all attributes and their values
        for the ResearchVenue object.
        """
        attributes = vars(self)
        attributes_str = ', '.join(f"{key}={value!r}" for key, value in attributes.items())
        return f"{self.__class__.__name__}({attributes_str})"


def get_city(browser):
    """Returns city that venue presides in"""
    instruction = "You are a robust venue researcher that gives accurate data."
    prompt = f'Find the city that the music or theatre venue `alton food hall ` is located in.'
    format_request = 'Return the response as json: {"city": str}. If unable to find accurate data, set the json value to None'

    google_links = make_google_search(f'alton food hall city location', browser, 1)
    if not google_links:
        return '{"city": None}', None

    google_link = google_links[0]
    webcontent = scrape_page_text(google_link, browser)

    res = gpt_request(instruction, prompt + webcontent + format_request, create_client())
    return res, google_link


if __name__ == '__main__':
    mongo_uri = os.getenv("MONGO_CONNECTION")
    mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    mongodb = mongo_client.brokerai
    venues_collection = mongodb["venues_csv"]

    venue = ResearchVenue("Orpheum Theatre", venues_collection)
    print(venue)