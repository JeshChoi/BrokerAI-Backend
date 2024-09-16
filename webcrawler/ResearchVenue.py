import os
import threading
from datetime import datetime
import json
from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from webcrawler.CrawlerTools import (traverse_pages_intelligently, scrape_concerts_per_year, make_google_search, scrape_page_text, traverse_all_pages)
from webcrawler.gpt import create_client, gpt_request, aggregate_gpt_request, extract_json_code_block
from webcrawler.BrowserConfig import create_browser, kill_chrome
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv(".env.local")
load_dotenv()

class ResearchVenue:
    def __init__(self, venue_name: str, mongo_collection, source=None):
        # MongoDB Schema
        self.venue: str = venue_name
        self.city: str = None
        self.capacity: int = None
        self.owned: str = None
        self.management: str = None
        self.number_of_stories: int = None
        self.square_footage: int = None
        self.number_of_bars: int = None
        self.number_of_shows_in_2023: int = None
        self.vip_packages_access: str = None
        self.food_offered: bool = None
        
        # Sources
        self.article_source = source
        self.sources = []  # Contains all sources for each attribute
        
        # Homepage data as GPT conversation and page data
        self.homelink = None
        self.homepage_webpage_conversation = []
        self.page_data = {}  # Stores data from traversed pages
        
        # GPT client
        self.gpt_client = create_client()

        # MongoDB connections
        self.mongo_collection = mongo_collection
        self.mongo_venue = self.get_existing_venue()  # Initialize with existing venue object, if available

        # If the venue already exists in the database, skip redundant research
        if self.mongo_venue:
            logger.info(f"Venue {self.venue} already exists in the database.")
            self.run_in_parallel()
        else:
            self.run_in_parallel()

    def get_existing_venue(self):
        """Check if the venue already exists in the MongoDB collection."""
        existing_venue = self.mongo_collection.find_one({"name": self.venue})
        if existing_venue:
            return existing_venue
        else:
            return None

    def get_homepage_webpages(self, browser):
        """Populate GPT conversation log with text from webpages from the venue's original website."""
        google_links = make_google_search(f'{self.venue}', browser, 1)
        if not google_links:
            return

        google_link = google_links[0]
        self.homelink = google_link
        
        # Traverse and store webpage data for specific items
        search_items = ['number of floors', 'VIP packages', 'capacity', 'number of bars']
        self.homepage_webpage_conversation, self.page_data = traverse_all_pages(google_link, browser, max_page_visits=30, search_items=search_items)

    def get_city(self, browser):
        """Returns city that venue presides in using Google search."""
        google_links = make_google_search(f'{self.venue} city location', browser, 1)
        if not google_links:
            return '{"city": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the city that the music or theatre venue `{self.venue}` is located in.'
        format_request = 'Return the response as json: {"city": str}. If unable to find accurate data, set the json value to None'

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_client)
        return res, google_link

    def get_capacity(self, browser) -> dict:
        """Returns the capacity of the venue using Google search."""
        google_links = make_google_search(f'{self.venue} venue capacity', browser, 1)
        if not google_links:
            return '{"capacity": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the capacity of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"capacity": int}. If unable to find accurate data, set the json value to None'

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_client)
        return res, google_link

    def get_owned(self, browser) -> dict:
        """Returns the ownership details of the venue using Google search."""
        google_links = make_google_search(f'{self.venue} venue ownership', browser, 1)
        if not google_links:
            return '{"owned": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the ownership details of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"owned": str}. If unable to find accurate data, set the json value to None'

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_client)
        return res, google_link

    def get_management(self, browser) -> dict:
        """Returns the management details of the venue using Google search."""
        google_links = make_google_search(f'{self.venue} venue management', browser, 1)
        if not google_links:
            return '{"management": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the management details of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"management": str}. If unable to find accurate data, set the json value to None'

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_client)
        return res, google_link

    def get_square_footage(self, browser) -> dict:
        """Returns the square footage of the venue using Google search."""
        google_links = make_google_search(f'{self.venue} venue square footage', browser, 1)
        if not google_links:
            return '{"square_footage": None}', None

        google_link = google_links[0]
        webcontent = scrape_page_text(google_link, browser)
        instruction = "You are a robust venue researcher that gives accurate data."
        prompt = f'Find the square footage of the music or theatre venue `{self.venue}`.'
        format_request = 'Return the response as json: {"square_footage": int}. If unable to find accurate data, set the json value to None'

        res = gpt_request(instruction, prompt + webcontent + format_request, self.gpt_client)
        return res, google_link

    # Updated code snippet within the ResearchVenue class

    def get_number_of_stories(self, browser) -> dict:
        """Fetches the number of floors/stories for the venue using webpage data first, then Google search if needed."""
        search_item = 'number of floors'
        google_links = make_google_search(f'{self.venue}', browser, 1)
        
        if not google_links:
            return {"number_of_stories": None}, None

        google_link = google_links[0]
        self.homelink = google_link

        # First, try to get the data by traversing pages
        conversation = traverse_pages_intelligently(google_link, browser, max_page_visits=3, search_items=[search_item], gpt_client=self.gpt_client)
        
        if conversation:
            # Process and retrieve data from the traversed pages
            prompt = f'Find the {search_item} of the music or theatre venue `{self.venue}`.'
            format_request = 'Return the response as json: {"number_of_stories": int}. If unable to find accurate data, set the json value to None'
            response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
            
            # Check if the response is a valid JSON string and load it
            if isinstance(response, str):
                try:
                    response = extract_json_code_block(response)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from GPT response: {response}")
                    return {"number_of_stories": None}, self.homelink

            # Ensure the response is a dictionary and contains the desired key
            if isinstance(response, dict) and "number_of_stories" in response:
                return response, self.homelink

        # If traversed pages did not provide data, use regular Google search
        return {"number_of_stories": None}, google_link


    def get_number_of_bars(self, browser) -> dict:
        """Fetches the number of bars in the venue using webpage data first, then Google search if needed."""
        search_item = 'number of bars'
        google_links = make_google_search(f'{self.venue}', browser, 1)

        if not google_links:
            return {"number_of_bars": None}, None

        google_link = google_links[0]
        self.homelink = google_link

        # First, try to get the data by traversing pages
        conversation = traverse_pages_intelligently(google_link, browser, max_page_visits=3, search_items=[search_item], gpt_client=self.gpt_client)

        if conversation:
            # Process and retrieve data from the traversed pages
            prompt = f'Find the {search_item} of the music or theatre venue `{self.venue}`.'
            format_request = 'Return the response as json: {"number_of_bars": int}. If unable to find accurate data, set the json value to None'
            response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
            
            # Check if response is a JSON string and load it
            if isinstance(response, str):
                try:
                    response = extract_json_code_block(response)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from GPT response: {response}")
                    return {"number_of_bars": None}, self.homelink

            if isinstance(response, dict) and "number_of_bars" in response:
                return response, self.homelink

        # If traversed pages did not provide data, use regular Google search
        return {"number_of_bars": None}, google_link

    def get_food_offered(self, browser) -> dict:
        """Fetches food offering details for the venue using webpage data first, then Google search if needed."""
        search_item = 'food offered'
        google_links = make_google_search(f'{self.venue}', browser, 1)

        if not google_links:
            return {"food_offered": None}, None

        google_link = google_links[0]
        self.homelink = google_link

        # First, try to get the data by traversing pages
        conversation = traverse_pages_intelligently(google_link, browser, max_page_visits=3, search_items=[search_item], gpt_client=self.gpt_client)

        if conversation:
            # Process and retrieve data from the traversed pages
            prompt = f'Find out if food is offered at the music or theatre venue `{self.venue}`.'
            format_request = 'Return the response as json: {"food_offered": bool}. If unable to find accurate data, set the json value to None'
            response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
            
            # Check if the response is a string and load it as JSON
            if isinstance(response, str):
                try:
                    response = extract_json_code_block(response)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from GPT response: {response}")
                    return {"food_offered": None}, self.homelink

            # Ensure the response is a dictionary and contains the desired key
            if isinstance(response, dict) and "food_offered" in response:
                return response, self.homelink

        # If traversed pages did not provide data, use regular Google search
        return {"food_offered": None}, google_link

    def get_vip_packages_access(self, browser) -> dict:
        """Fetches VIP package details for the venue using webpage data first, then Google search if needed."""
        search_item = 'VIP packages'
        google_links = make_google_search(f'{self.venue}', browser, 1)

        if not google_links:
            return {"vip_packages_access": None}, None

        google_link = google_links[0]
        self.homelink = google_link

        # First, try to get the data by traversing pages
        conversation = traverse_pages_intelligently(google_link, browser, max_page_visits=3, search_items=[search_item], gpt_client=self.gpt_client)

        if conversation:
            # Process and retrieve data from the traversed pages
            prompt = f'Find the details of the VIP packages offered at the music or theatre venue `{self.venue}`.'
            format_request = 'Return the response as json: {"vip_packages_access": str}. If unable to find accurate data, set the json value to None'
            response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
            
            # Check if the response is a string and load it as JSON
            if isinstance(response, str):
                try:
                    response = extract_json_code_block(response)
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from GPT response: {response}")
                    return {"vip_packages_access": None}, self.homelink

            # Ensure the response is a dictionary and contains the desired key
            if isinstance(response, dict) and "vip_packages_access" in response:
                return response, self.homelink

        # If traversed pages did not provide data, use regular Google search
        return {"vip_packages_access": None}, google_link

    def updateDB(self, data: dict, source: dict):
        """Updates the database with the data."""
        logger.info(f"Updating database with {data.keys()}")

        # Check if venue object connection is established
        if self.mongo_venue is None:
            new_venue = self.mongo_collection.insert_one({'name': self.venue, 'article_source': self.article_source, 'createdAt': datetime.now()})
            self.mongo_venue = new_venue

        # Make updates to the MongoDB venue
        update_result = self.mongo_collection.update_one(
            {"name": self.venue},
            {"$set": data,
             '$currentDate': {'updatedAt': True}},  # Automatically set the update timestamp
        )
        logger.info(f"Updated {update_result.modified_count} document(s).")

    def browser_research(self, browser, tasks):
        """
        Executes a list of research tasks using the given browser instance.
        This function handles various response formats such as JSON strings, lists, or dictionaries.
        """
        for task in tasks:
            try:
                # Execute the task (assuming it returns a tuple of (response, google_link))
                task_response, google_link = task(browser)

                # Initialize variables
                string = None
                source = None

                # Handle if the task response is a string (possibly a JSON string)
                if isinstance(task_response, str):
                    string = task_response.replace("```json", "").replace("```", "").strip()
                    logger.info(f"Raw JSON string: {string}")

                # If the task_response is a dictionary or list, process it directly
                elif isinstance(task_response, (dict, list)):
                    logger.info(f"Response is a JSON object or list: {task_response}")

                    # Create source metadata
                    if google_link:
                        label_formatted = task.__name__.replace("get_", "").replace("_", " ").title()
                        self.sources = list(self.sources)  # Ensure sources is a list
                        self.sources.append({"source": google_link, "label": label_formatted})
                        source = {"source": google_link, "label": label_formatted}

                    # If it's a list of dictionaries, handle each dictionary individually
                    if isinstance(task_response, list) and all(isinstance(item, dict) for item in task_response):
                        for item in task_response:
                            self.process_dict_item(item, google_link, task)

                    # If it's a dictionary, process it directly
                    elif isinstance(task_response, dict):
                        self.updateDB(task_response, source)
                    continue

                # If it's a string, try to parse the JSON
                if string:
                    if '{"data": null}' not in string:  # Skip if data is explicitly null
                        try:
                            data = json.loads(string)  # Try to load JSON
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e.msg} at line {e.lineno} column {e.colno}")
                            continue

                        # Skip if "data" key exists and is None
                        if "data" in data and data["data"] is None:
                            logger.info(f"No useful data found in task {task.__name__}")
                            continue

                        # Create source metadata if not already created
                        if google_link and not source:
                            label_formatted = task.__name__.replace("get_", "").replace("_", " ").title()
                            self.sources = list(self.sources)  # Ensure sources is a list
                            self.sources.append({"source": google_link, "label": label_formatted})
                            source = {"source": google_link, "label": label_formatted}

                        logger.info(f"Parsed data: {data}, Source: {source}")
                        self.updateDB(data, source)

                # Log if no valid data was found
                else:
                    logger.info(f"No data found for task {task.__name__}")

                # Ensure sources are always updated and stored
                self.updateDB({"sources": self.sources}, {})

            except Exception as e:
                logger.error(f"Unexpected error in task {task.__name__}: {str(e)}")


    def process_dict_item(self, item, google_link, task):
        """
        Process individual dictionary items from a list of dictionaries (e.g., yearly concert data).
        """
        try:
            source = None
            if google_link:
                dict_key = list(item.keys())[0]  # Get the first key, which represents the year or relevant identifier
                self.sources = list(self.sources)  # Ensure sources is a list
                self.sources.append({"source": google_link, "label": f'{dict_key} data'})
                source = {"source": google_link, "label": f'{dict_key} data'}

            # Log and update the database for each dictionary item
            logger.info(f"Parsed item: {item}, Source: {source}")
            self.updateDB(item, source)

        except Exception as e:
            logger.error(f"Error processing dictionary item in task {task.__name__}: {str(e)}")


    def get_yearly_number_of_shows(self, browser) -> dict:
        """Returns the number of hows in 20xx at the venue"""
        concerts_per_year, venue_link = scrape_concerts_per_year(self.venue) 
        return concerts_per_year, venue_link
    
    def run_in_parallel(self):
        """Manages the parallel execution of research tasks."""
        browsers = [create_browser() for _ in range(4)]

        tasks1 = [self.get_vip_packages_access, self.get_city, self.get_capacity, self.get_owned]
        tasks2 = [self.get_number_of_bars, self.get_square_footage]
        tasks3 = [self.get_number_of_stories, self.get_management]
        tasks4 = [self.get_food_offered, self.get_yearly_number_of_shows]

        threads = [
            threading.Thread(target=self.browser_research, args=(browsers[0], tasks1)),
            threading.Thread(target=self.browser_research, args=(browsers[1], tasks2)),
            threading.Thread(target=self.browser_research, args=(browsers[2], tasks3)),
            threading.Thread(target=self.browser_research, args=(browsers[3], tasks4))
        ]

        # Start threads
        for thread in threads:
            thread.start()

        # Ensure all threads complete before continuing
        for thread in threads:
            thread.join()

        # Close all browser instances after work is done
        for browser in browsers:
            browser.quit()

        # Ensure all Chrome instances are terminated.
        kill_chrome()

    def __str__(self):
        """
        Returns a string representation of all attributes and their values
        for the ResearchVenue object.
        """
        attributes = vars(self)
        attributes_str = ', '.join(f"{key}={value!r}" for key, value in attributes.items())
        return f"{self.__class__.__name__}({attributes_str})"

from webcrawler.venues import venues # dataset with all the data

if __name__ == '__main__' and False:
    mongo_uri = os.getenv("MONGO_CONNECTION")
    mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    mongodb = mongo_client.brokerai
    venues_collection = mongodb["venues"]
    start_time = time.time()  # Start the timer

    venue = ResearchVenue('Alberta Rose Theatre', venues_collection)
    print(venue)
    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    print(f"Time taken for the main function: {elapsed_time:.2f} seconds")

# if __name__ == '__main__':
#     print(len(venues_2))
if __name__ == '__main__' and True:
    mongo_uri = os.getenv("MONGO_CONNECTION")
    mongo_client = MongoClient(mongo_uri, server_api=ServerApi('1'))
    mongodb = mongo_client.brokerai
    venues_collection = mongodb["venues"]
    start_time = time.time()  # Start the timer
    for venue in venues:
        ResearchVenue(venue, venues_collection)
        print(venue)
    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    print(f"Time taken for the main function: {elapsed_time:.2f} seconds")
    # 300-500 
    # 500 -1000 