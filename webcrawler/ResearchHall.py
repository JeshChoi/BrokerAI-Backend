import json
import os
import threading
from datetime import datetime

from dotenv import load_dotenv
from openai import AzureOpenAI

from webcrawler.CrawlerTools import (make_google_search,
                                     scrape_page_text)

from webcrawler.BrowserConfig import get_chrome_options, create_browser
load_dotenv(".env.local")
load_dotenv()

client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )

class ResearchHall:
    def __init__(self, mongo_collection, food_hall: str, source = None):
        food_hall = food_hall.strip().lower()
        if 'food hall' not in food_hall:
            food_hall = f'{food_hall} food hall'

        self.mongo_collection = mongo_collection
        self.food_hall = food_hall
        self.article_source = source
        self.sources = []
        self.mongo_foodhall = None

    def gpt_request(self, gpt_instruction: str, user_prompt: str):
        """return a list of names of relevant halls"""
        GPT_INSTRUCTIONS = gpt_instruction
        user_prompt = user_prompt

        response = client.chat.completions.create(
            model="gpt-35-turbo",
            seed=42,
            temperature=0.3,
            messages=[
                {"role": "system", "content": GPT_INSTRUCTIONS},
                {"role": "user", "content": user_prompt}
            ]
        )
        payload = response.choices[0].message.content
        return payload

    def get_location(self, browser):  # google maps API
        """returns location of food hall"""
        res = None
        location_instruction = "You are a market researcher and you are helping me find information about certain food halls."
        prompt = f'Given this text content, determine the location of the food hall "{self.food_hall}"' + \
            '. return the response as raw json: {"city": "CityName", "state": "StateCode"}'
        google_link = make_google_search(
            f'{self.food_hall} location', browser, 1)[0]
        try:
            webcontent = scrape_page_text(google_link, browser)
            res = self.gpt_request(location_instruction, prompt + webcontent)
        except:
            print('get_locations went wrong')

        return res, google_link

    def get_square_footage(self, browser):
        """returns get_square_footage of food hall"""
        res = None
        location_instruction = "You are a market researcher and you are helping me find information about certain food halls."
        prompt = f'Given this text content, determine the square footage of "{self.food_hall}"' + \
            '. return the response as raw json: {"square_footage": 10000} or {"square_footage": null} if data is unavailable.'

        google_link = make_google_search(
            f'{self.food_hall} square footage', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(location_instruction, prompt + webcontent)
        return res, google_link

    def get_number_of_food_stalls(self, browser):
        """returns number of food, bar, and retail stalls of food hall"""
        location_instruction = "You are a market researcher and you are helping me find information about certain food halls."
        prompt = f'Given this text content, determine the number of food stalls, bar stalls, and retail stalls in "{self.food_hall}"' + \
            '. return the response as raw and VALID json, it is crucial i get this data in the right format: {"food": 3, "bars": 4, "retail": 3} or {"food": null, "bars": null, "retail": null} if information is not available, of course if you can find number of stalls for some, you dont put them all as null.'

        google_link = make_google_search(
            f'{self.food_hall} number of food stalls', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(location_instruction, prompt + webcontent)
        return res, google_link

    # GPT Generated all below... this is what we want to do with the universal scraper...

    def get_types_of_food_stalls(self, browser):
        """Returns types of food stalls in food hall"""
        instruction = "You are a market researcher and you are helping me find information about the types of food stalls in certain food halls."
        prompt = f'Given this text content, list the types of food stalls available in "{self.food_hall}"' + \
            '. return the response as raw json: {"types_of_food_stalls": ["Mexican", "Italian", "Japanese"]} or {"types_of_food_stalls": null} if no data is found.'

        google_link = make_google_search(
            f'{self.food_hall} types of food stalls', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_demographic(self, browser):
        """Returns demographic information of the area surrounding the food hall."""
        instruction = "You are a market researcher and you are tasked with gathering demographic information about the area surrounding a specific food hall."
        prompt = f'Analyze this text content to provide demographic information of the area surrounding "{self.food_hall}"' + \
            '. return the response as raw json: {"population_density": "100/sq.miles", "median_income": "10000", "age_distribution": {"0-10": "10%", "11-24": "30%"}} or {"data": null} if specifics are unavailable.'

        google_link = make_google_search(
            f'{self.food_hall} area demographics', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_local_area_composition(self, browser):
        """Returns information on the local area composition around the food hall."""
        instruction = "You are a market researcher and your objective is to understand the composition of the area surrounding a food hall."
        prompt = f'Evaluate the text content to describe the area composition around "{self.food_hall}"' + \
            '. return the response as raw json: {"composition": ["office", "retail", "residential"]} or {"composition": null} if data is not available.'

        google_link = make_google_search(
            f'{self.food_hall} surrounding area composition', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_public_transport(self, browser):
        """Returns public transport options available near the food hall."""
        instruction = "You are a market researcher, aiming to find out about public transport options available near a food hall."
        prompt = f'Summarize information about nearby public transport for "{self.food_hall}"' + \
            '. return the response as raw json: {"public_transport": ["bus", "train", "bike"]} or {"public_transport": null} if information is scarce.'

        google_link = make_google_search(
            f'{self.food_hall} public transport options', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_parking_availability(self, browser):
        """Returns parking availability information for the food hall."""
        instruction = "You are a market researcher focusing on parking availability for a particular food hall."
        prompt = f'Provide details on parking at "{self.food_hall}".' + \
            ' return the response as raw json: {"parking_spots": 1000, "parking_fees": "$5/hr", "peak_time_availability": "10:00am"} or {"data": null} if unavailable.'

        google_link = make_google_search(
            f'{self.food_hall} parking availability', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_foot_traffic_estimates(self, browser):
        """Returns foot traffic estimates near the food hall."""
        instruction = "As a market researcher, your task is to estimate the foot traffic around a specific food hall."
        prompt = f'Determine the average foot traffic near "{self.food_hall}".' + \
            ' return the response as raw json: {"foot_traffic": "100/hr"} or {"foot_traffic": "1000/day"} or {"data": null} if estimates are not directly available.'

        google_link = make_google_search(
            f'{self.food_hall} foot traffic estimates', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_annual_visitor_count(self, browser):
        """Returns the annual visitor count of the food hall."""
        instruction = "You are tasked with finding the annual visitor count for a food hall as part of a market research project."
        prompt = f'Extract information on annual visitor count for "{self.food_hall}"' + \
            '. return the response as raw json: {"annual_visitor_count": 1000000} or {"data": null} if no specific numbers are found.'

        google_link = make_google_search(
            f'{self.food_hall} annual visitor count', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_lease_rates(self, browser):
        """Returns lease rates for the food hall."""
        instruction = "Your objective as a market researcher is to determine the lease rates for spaces within a specific food hall."
        prompt = f'Provide the average lease rate for spaces within "{self.food_hall}".' + \
            ' return the response as raw json: {"lease_rates": "$800/sq.ft"} or {"data": null} if precise rates are not available.'

        google_link = make_google_search(
            f'{self.food_hall} lease rates', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_occupancy_rate(self, browser):
        """Returns the occupancy rate of the food hall."""
        instruction = "As a market researcher, it's your job to find out the occupancy rate of a given food hall."
        prompt = f'Analyze to provide the occupancy rate for "{self.food_hall}".' + \
            ' return the response as raw json: {"occupancy_rate": "82%"} or {"data": null} if direct data is unavailable.'

        google_link = make_google_search(
            f'{self.food_hall} occupancy rate', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_year_established(self, browser):
        """Returns the year the food hall was established."""
        instruction = "Your role as a market researcher involves finding out when a food hall was first established."
        prompt = f'Find out the year of establishment for "{self.food_hall}".' + \
            ' return the response as raw json: {"year_established": 1980} or {"data": null} if the exact year is not available.'

        google_link = make_google_search(
            f'{self.food_hall} year established', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_renovation_history(self, browser):
        """Returns the renovation history of the food hall."""
        instruction = "In your capacity as a market researcher, you are to uncover the renovation history of a food hall."
        prompt = f'Detail the renovation history of "{self.food_hall}".' + \
            ' return the response as raw json: {"renovation_history": "Details"} or {"data": null} if comprehensive details are not available.'

        google_link = make_google_search(
            f'{self.food_hall} renovation history', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_owner(self, browser):
        """Returns the owner of the food hall."""
        instruction = "Your task as a market researcher is to identify the owner or owning entity of a food hall."
        prompt = f'Identify the owner of "{self.food_hall}". ' + \
            'return the response as raw json: {"owner": "Name", "contact": "ContactInfo"} or {"data": null} if the owner’s details are not directly available.'

        google_link = make_google_search(
            f'{self.food_hall} owner', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_management_company(self, browser):
        """Returns the management company of the food hall."""
        instruction = "The aim of your market research is to find out which company manages a specific food hall."
        prompt = f'Find out the management company for "{self.food_hall}".' + \
            ' return the response as raw json: {"management_company": "CompanyName"} or {"data": null} if the details are not evident.'

        google_link = make_google_search(
            f'{self.food_hall} management company', browser, 1)[0]
        webcontent = scrape_page_text(google_link, browser)

        res = self.gpt_request(instruction, prompt + webcontent)
        return res, google_link

    def get_photos(self, browser):
        """Returns the urls to food hall photos."""
        res = get_images(self.food_hall, browser)
        return res, None

    def updateDB(self, data: dict, source: dict):
        """Updates the database with the data"""
        print(f"Updating database with {data.keys()}")
        # MONGO DB changes here 
        new_data = {key: {"value": value, "source": source} for key, value in data.items()}
        if self.mongo_foodhall is None: 
            food_hall = self.mongo_collection.find_one({"name": self.food_hall})
            
            if food_hall is not None: 
                self.mongo_foodhall = food_hall
            else:
                # create new food hall in the database 
                new_foodhall = self.mongo_collection.insert_one({'name': self.food_hall, 'article_source':self.article_source, 'createdAt': datetime.now(),})
                self.mongo_foodhall = new_foodhall
                pass 
        # make updates to the mongodb food hall 
        update_result = self.mongo_collection.update_one(
            {"name": self.food_hall},  # Use the document's _id for the filter
            {"$set": data,
             '$currentDate': {'updatedAt': True}  # Automatically set the update timestamp
            },  # Use the '$set' operator to update fields
            
        )
        print(f"Updated {update_result.modified_count} document(s).")
        pass

    def browser_research(self, browser, tasks):
        """Executes a list of research tasks using the given browser instance."""
        for task in tasks:
            # Assuming each task function takes a 'food_hall' string and a 'browser' object
            # You might need to adjust this call depending on how your task functions are structured
            try:
                task_response, google_link = task(browser)
                string = task_response.replace("```json", "").replace("```", "")
                
                # Debug print to check the content of the string
                print(f"Raw JSON string: {string}")

                if '{"data": null}' not in string:
                    try:
                        data = json.loads(string)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e.msg} at line {e.lineno} column {e.colno}")
                        continue

                    if "data" in data and data["data"] is None:
                        continue

                    source = None
                    if google_link:
                        label_formatted = task.__name__.replace("get_", "").replace("_", " ").title()
                        self.sources.append({"source": google_link, "label": label_formatted})
                        source = {"source": google_link, "label": label_formatted}

                    print(f"Parsed data: {data}, Source: {source}")
                    self.updateDB(data, source)
                else:
                    print(f"Data not found for {task.__name__}")

                self.updateDB({"sources": self.sources}, {})
            
            except Exception as e:
                print(f"Unexpected error in task {task.__name__}: {str(e)}")

    def run_in_parallel(self):
        options = get_chrome_options()

        # Initialize browser instances
        browser1 = create_browser()
        browser2 = create_browser()
        browser3 = create_browser()
        browser4 = create_browser()

        # Define the tasks for each browser (quartering the total tasks)
        all_tasks = [
            # self.get_photos,
            self.get_location,
            self.get_square_footage,
            self.get_number_of_food_stalls,
            self.get_types_of_food_stalls,
            self.get_demographic,
            self.get_local_area_composition,
            self.get_public_transport,
            self.get_parking_availability,
            self.get_foot_traffic_estimates,
            self.get_annual_visitor_count,
            self.get_lease_rates,
            self.get_occupancy_rate,
            self.get_year_established,
            self.get_renovation_history,
            self.get_owner,
            self.get_management_company,
        ]

        tasks1 = all_tasks[:4]
        tasks2 = all_tasks[4:8]
        tasks3 = all_tasks[8:12]
        tasks4 = all_tasks[12:]

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
        browser1.quit()
        browser2.quit()
        browser3.quit()
        browser4.quit()

    def __str__(self):
        """
        Returns a string representation of all attributes and their values
        for the ResearchHall object.
        """
        attributes = vars(self)
        attributes_str = ', '.join(f"{key}={value!r}" for key, value in attributes.items())
        return f"{self.__class__.__name__}({attributes_str})"


if __name__ == '__main__':
    hall = ResearchHall(client, "1", "alton food hall")
    hall.run_in_parallel()
