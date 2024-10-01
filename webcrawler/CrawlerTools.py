from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List

import os
from selenium.webdriver.chrome.options import Options
from pyvirtualdisplay import Display

from dotenv import load_dotenv
from openai import AzureOpenAI
load_dotenv()

import time
import json

import urllib.parse
from urllib.parse import urlparse

from webcrawler.BrowserConfig import get_chrome_options, create_browser, create_undetected_non_headless_browser
from webcrawler.gpt import gpt_request, aggregate_gpt_request, extract_json_code_block
import re

import logging

logger = logging.getLogger(__name__)

def valid_url(url: str) -> bool:
    """returns whether this url is valid for search"""
    unnecessary_links = (
        'https://www.instagram.com',
        'https://www.google.com/search',
        'https://www.facebook.com/',
        'https://www.youtube.com/'
    )
    return url and not url.startswith(unnecessary_links)

def get_google_alert_links(search_key: str, browser) -> list[str]:
    """Given search key, returns a list of todays google alerts of the search_key"""
    google_alerts_url = 'https://www.google.com/alerts#1:0'

    browser.get(google_alerts_url)

    elem = browser.find_element(
        By.XPATH, "//input[@aria-label='Create an alert about...']")
    elem.send_keys(search_key)

    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'result'))
    )

    links = []
    search_results = browser.find_elements(By.XPATH, "//li[@class='result']")

    for result in search_results:
        anchor_tags = result.find_elements(By.CSS_SELECTOR, 'a')
        for a in anchor_tags:
            url = a.get_attribute('href')
            if valid_url(url):
                links.append(url)

    return links

def make_google_search(search_query: str, browser, num_links=3):
    """makes a google search and returns the top 'num_links' links"""
    browser.get(f'https://www.google.com/search?q={search_query}')

    # Collect URLs from search results
    links = []
    search_results = browser.find_elements(By.CSS_SELECTOR,
                                           '#search .g')  # Each result is within a div with class 'g'

    for result in search_results:
        anchor_tags = result.find_elements(By.CSS_SELECTOR, 'a')
        for a in anchor_tags:
            url = a.get_attribute('href')
            if valid_url(url):
                links.append(url)
    links = links[:num_links]

    return links

def scrape_page_text(url: str, browser, max_length=5000) -> str:
    """Returns text from specified URL, limited to max_length characters."""
    text = ""
    try:
        browser.get(url)
        wait = WebDriverWait(browser, 5)
        time.sleep(5)
        page_source = browser.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        if len(text) > max_length:
            text = text[:max_length] + '... [truncated]'
    finally:
        pass
    return text

def summarize_text(text: str, gpt_client, max_tokens=1000) -> str:
    """Summarizes the provided text to reduce token usage."""
    instruction = "Please provide a concise summary of the following text."
    prompt = f"{instruction}\n\n{text}"
    format_request = "Return the summary as a single paragraph."
    summary = gpt_request(instruction, prompt + format_request, gpt_client)
    return summary



def scrape_page_text_headless(url: str, browser) -> str:
    """Returns text from specified URL, pass browser in"""
    text = ""
    try:
        browser.get(url)
        page_source = browser.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip()
                  for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

    finally:
        pass

    return text

def get_all_tags_links_on_page(url: str, browser) -> list[str]:
    """returns all links on page of website -> great for smart navigation"""
    res = []
    try:
        browser.get(url)
        wait = WebDriverWait(browser, 5)
        time.sleep(12)
        links = browser.find_elements(By.CSS_SELECTOR, 'a')
        for link in links:
            res.append(
                {'label': link.text, 'link': link.get_attribute('href')})
    finally:
        pass

    return res

def get_all_links_on_page(url, browser) -> list[str]:
    """returns all links on page of website -> great for smart navigation"""
    res = []
    try:
        browser.get(url)
        wait = WebDriverWait(browser, 5)
        time.sleep(12)
        links = browser.find_elements(By.CSS_SELECTOR, 'a')
        res.extend([link.get_attribute('href') for link in links])
    finally:
        pass

    return res

def get_domain(url):
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    return domain

def filter_links(base_url, links):
    base_domain = get_domain(base_url)
    filtered_links = [link for link in links if get_domain(link) == base_domain]
    return filtered_links

def webpage_to_json_markdown(website_url, browser): 
    """Returns the current page as markdown in json format"""
    gpt_instruction = "You are a robust web scraper, scraping the web to analyze accurate information."
    prompt = f'Take the contents of this page and put it into web format that is clean and useful for analyzing the page content.'
    webcontent = f'Here is the webcontent:' + scrape_page_text(website_url, browser)
    format_request = 'Return the response as json - ONLY return JSON!: {"content": str}.'
    
    prompt_details =  prompt + webcontent + format_request
    gpt_response = gpt_request(gpt_instruction, prompt_details)
    page_content_json = re.sub(r"json|```", "", gpt_response).strip()
    
    return page_content_json
    
def check_domain(url, correct_domain):
    parsed_url = urlparse(url)
    current_domain = parsed_url.hostname  
    return current_domain == correct_domain

def chunk_text(text: str, max_chunk_size=4000) -> list[str]:
    """Splits text into smaller chunks to stay within token limits."""
    return [text[i:i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]


def extract_relevant_info(page_content: str, search_items: list, gpt_client=None) -> dict:
    """
    Extracts relevant information from the page content for the provided search items.
    
    Args:
        page_content (str): The raw text content of the webpage.
        search_items (list): A list of items to search for (e.g., 'VIP packages', 'number of floors').
        gpt_client: The GPT client instance to process the page content.
    
    Returns:
        dict: A dictionary with search items as keys and the extracted information as values.
    """
    instruction = "You are a robust venue researcher tasked with extracting the following details from the webpage text."
    prompt = f"{instruction}\n\nPage Content:\n{page_content}\n\nSearch for the following information: {', '.join(search_items)}."
    format_request = 'Return the information as a JSON object with keys for each search item. If no data is found for an item, return None for that item.'

    # Making the GPT request to extract relevant information
    response = gpt_request(instruction, prompt + format_request, gpt_client)
    
    try:
        extracted_data = extract_json_code_block(response)
    except json.JSONDecodeError:
        extracted_data = {item: None for item in search_items}  # Default to None if parsing fails

    return extracted_data
# Assume this function returns the number of tokens used by a string or conversation list
def count_tokens(text: str) -> int:
    # Placeholder for actual token counting logic based on the GPT model in use
    return len(text.split())  # Simple word count approximation (replace with actual token count logic)

def traverse_pages_intelligently(url: str, browser, max_page_visits=5, venue: str=None, search_items: List[str]=None, gpt_client=None, max_tokens=20000):
    """
    Traverses website pages intelligently to find information about the search_items.
    Returns a GPT conversation list that can be used to ask a question to GPT about the pages.
    """
    if search_items is None:
        search_items = ['number of floors', 'VIP packages', 'food offered', 'number of bars']  # Default items to search for
    
    url_queue = get_all_links_on_page(url, browser)
    visited_urls = set()
    visited_urls_count = 0
    
    found_items = set()
    conversation = []
    total_tokens_used = 0  # Initialize token usage tracker
    
    # Start the conversation for intelligent web traversal
    traverse_prompt = f"You are tasked with navigating through multiple webpages to find accurate data about: {', '.join(search_items)}."
    response, conversation = aggregate_gpt_request(traverse_prompt, conversation=conversation)
    
    # Log the initial token usage
    tokens_used = count_tokens(traverse_prompt)
    total_tokens_used += tokens_used
    logger.info(f"Initial prompt used {tokens_used} tokens. Total tokens: {total_tokens_used}")
    
    while url_queue and visited_urls_count < max_page_visits:
        if total_tokens_used >= max_tokens:
            logger.warning(f"Token limit reached. Stopping traversal at {total_tokens_used} tokens.")
            break
        
        available_links = [{"link": url} for url in url_queue if valid_url(url) and url not in visited_urls]
        if not available_links:
            break
        
        link_selection_prompt = (
            f"You are gathering information about the venue {venue}. Help retrieve information about the venue's: {', '.join(search_items)}.\n"
            f"Here are some links to choose from- starting with the venue homepage is a good start. Select the most relevant one in the format: {{'link': 'selected_link'}}:\n"
            f"{json.dumps(available_links, indent=2)}\n"
            "Please respond with *only* the JSON content and nothing else. The format should strictly be: {'link': 'selected_link'}."
        )
        
        # Add the token usage for the current prompt
        tokens_used = count_tokens(link_selection_prompt)
        total_tokens_used += tokens_used
        logger.info(f"Link selection prompt used {tokens_used} tokens. Total tokens: {total_tokens_used}")
        
        if total_tokens_used >= max_tokens:
            logger.warning(f"Token limit reached. Stopping traversal at {total_tokens_used} tokens.")
            break
        
        response, conversation = aggregate_gpt_request(link_selection_prompt, conversation)
        
        try:
            selected_link_data = extract_json_code_block(response)
            selected_link = selected_link_data.get("link", None)
        except:
            selected_link = available_links[0]["link"]
        
        if selected_link in visited_urls or not selected_link:
            continue
        
        # Visit the selected URL and scrape the content
        browser.get(selected_link)
        data_content = scrape_page_text_headless(selected_link, browser)
        
        # Split the content into smaller chunks
        content_chunks = chunk_text(data_content)
        
        for chunk in content_chunks:
            if total_tokens_used >= max_tokens:
                logger.warning(f"Token limit reached. Stopping traversal at {total_tokens_used} tokens.")
                break
            
            summarized_chunk = summarize_text(chunk, gpt_client)
            conversation.append({"role": "user", "content": summarized_chunk})
            
            # Track tokens used by this chunk
            tokens_used = count_tokens(summarized_chunk)
            total_tokens_used += tokens_used
            logger.info(f"Summarized chunk used {tokens_used} tokens. Total tokens: {total_tokens_used}")
            
            # Extract relevant information using GPT
            extracted_info = extract_relevant_info(summarized_chunk, search_items, gpt_client)
            for item, value in extracted_info.items():
                if value is not None:
                    found_items.add(item)
        
        visited_urls.add(selected_link)
        visited_urls_count += 1
        
        # Stop if all search items are found
        if found_items == set(search_items):
            break
        
        # Get new links from the selected page
        new_links = get_all_links_on_page(selected_link, browser)
        url_queue.extend([link for link in new_links if link not in visited_urls])
        url_queue = [url for url in url_queue if url != selected_link]
    
    logger.info(f'Final token usage: {total_tokens_used}. Found Items: {found_items}')
    return conversation
def traverse_pages_intelligently_OG(url: str, browser, max_page_visits = 5, venue: str = None, search_items: List[str] = None, gpt_client=None):
    """
    Traverses webiste pages intelligently to find information about the search_items
    Returns a GPT conversation list that can be used to ask a question to GPT about the pages
    """
    if search_items is None: 
        search_items = ['number of floors', 'VIP packages', 'food offered', 'number of bars'] # default things we want to research for vnues 
    
    url_queue = get_all_links_on_page(url, browser)
    visited_urls = set() 
    visited_urls_count = 0 
    
    found_items = set()
    
    conversation = [] 
    
    # kickstart conversation for intelligent web traversal 
    traverse_prompt = f"You are tasked with navigating through multiple webpages to find accurate data about: {', '.join(search_items)}."
    response, conversation = aggregate_gpt_request(traverse_prompt, conversation=conversation)
    
    while url_queue and visited_urls_count < max_page_visits:
        available_links = [{"link": url} for url in url_queue if valid_url(url) and url not in visited_urls]
        if not available_links:
            break

        link_selection_prompt = (
            f"You are gathering information about the venue {venue}. Help retrieve information about the venue's: {', '.join(search_items)}.\n"
            f"Here are some links to choose from- starting with the venue homepage is a good start. Select the most relevant one in the format: {{'link': 'selected_link'}}:\n"
            f"{json.dumps(available_links, indent=2)}\n"
            "Please respond with *only* the JSON content and nothing else. The format should strictly be: {'link': 'selected_link'}."
        )
        # we should add page data to help aid link selection

        response, conversation = aggregate_gpt_request(link_selection_prompt, conversation)

        try:
            selected_link_data = extract_json_code_block(response)
            selected_link = selected_link_data.get("link", None)
        except:
            selected_link = available_links[0]["link"]

        if selected_link in visited_urls or not selected_link:
            continue

        # Visit the selected URL and scrape the content
        browser.get(selected_link)
        data_content = scrape_page_text_headless(selected_link, browser)

        # Split the content into smaller chunks
        content_chunks = chunk_text(data_content)
        
        # Process each chunk separately with GPT
        for chunk in content_chunks:
            summarized_chunk = summarize_text(chunk, gpt_client)
            conversation.append({"role": "user", "content": summarized_chunk})

            # Extract relevant information using GPT
            extracted_info = extract_relevant_info(summarized_chunk, search_items, gpt_client)
            for item, value in extracted_info.items():
                if value is not None:
                    found_items.add(item)

        visited_urls.add(selected_link)
        visited_urls_count += 1

        # Stop if all search items are found
        if found_items == set(search_items):
            break

        new_links = get_all_links_on_page(selected_link, browser)
        url_queue.extend([link for link in new_links if link not in visited_urls])
        url_queue = [url for url in url_queue if url != selected_link]

    print(f'Found Items: {found_items}')
    return conversation
    
    

def traverse_all_pages(website_url: str, browser, max_page_visits=5, search_items=None, gpt_client=None):
    if search_items is None:
        search_items = ['number of floors', 'VIP packages', 'food offered', 'number of bars']

    website_domain = get_domain(website_url)
    url_queue = get_all_links_on_page(website_url, browser)
    visited_urls = set()
    visited_count = 0

    page_data = {}
    conversation = []
    found_items = set()

    traverse_prompt = f"You are tasked with navigating through multiple webpages to find accurate data about: {', '.join(search_items)}."
    response, conversation = aggregate_gpt_request(traverse_prompt, conversation=conversation)

    while url_queue and visited_count < max_page_visits:
        available_links = [{"link": url} for url in url_queue if valid_url(url) and check_domain(url, website_domain) and url not in visited_urls]
        if not available_links:
            break

        link_selection_prompt = (
            f"You are gathering information about: {', '.join(search_items)}.\n"
            f"Here are some links to choose from. Select the most relevant one:\n"
            f"{json.dumps(available_links)}"
        )

        MAX_CONVERSATION_LENGTH = 8
        if len(conversation) > MAX_CONVERSATION_LENGTH:
            conversation = conversation[-MAX_CONVERSATION_LENGTH:]

        response, conversation = aggregate_gpt_request(link_selection_prompt, conversation)

        try:
            selected_link_data = extract_json_code_block(response)
            selected_link = selected_link_data.get("link", None)
        except:
            selected_link = available_links[0]["link"]

        if selected_link in visited_urls or not selected_link:
            continue

        # Visit the selected URL and scrape the content
        browser.get(selected_link)
        data_content = scrape_page_text_headless(selected_link, browser)

        # Split the content into smaller chunks
        content_chunks = chunk_text(data_content)
        
        # Process each chunk separately with GPT
        for chunk in content_chunks:
            summarized_chunk = summarize_text(chunk, gpt_client)
            conversation.append({"role": "user", "content": summarized_chunk})

            # Extract relevant information using GPT
            extracted_info = extract_relevant_info(summarized_chunk, search_items, gpt_client)
            for item, value in extracted_info.items():
                if value is not None:
                    found_items.add(item)

        # Store the page data
        page_data[selected_link] = data_content

        visited_urls.add(selected_link)
        visited_count += 1

        # Stop if all search items are found
        if found_items == set(search_items):
            break

        new_links = get_all_links_on_page(selected_link, browser)
        url_queue.extend([link for link in new_links if link not in visited_urls])
        url_queue = [url for url in url_queue if url != selected_link]

    return conversation, page_data


def search_venue_concert_archives(venue:str):
    """Takes venue name and returns valid search key on concert archives"""
    driver = create_undetected_non_headless_browser()
    link = 'https://www.concertarchives.org/venues?utf8=%E2%9C%93&search=' + venue
    driver.get(link)

    res = None
    try:
        table = WebDriverWait(driver, 60).until(
            EC.presence_of_element_located((By.ID, "venues-index-table"))
        )
        res = table.find_element(By.CSS_SELECTOR, 'tbody tr:first-child a').get_attribute('href')
    except Exception as e:
        print(f"Element not found: {e}")
    finally:
        driver.close()
        driver.quit()
    return res
    
def scrape_concerts_per_year(venue: str):
    """Scrapes number of concerts per year from: https://www.concertarchives.org/venues/<concert-hall>"""
    driver = create_undetected_non_headless_browser()
    
    venue_link = search_venue_concert_archives(venue)
    driver.get(venue_link)
    
    concerts_per_year = []

    try:
        WebDriverWait(driver, 120).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".table.table-condensed.table-hover.tops_table"))
        )
        
        rows = driver.find_elements(By.CSS_SELECTOR, '.table.table-condensed.table-hover.tops_table tbody tr')
        count = 0
        for row in rows:
            if count == 5:
                break
            try:
                row_text = row.text
                if row_text[0] != '2' and row_text[0] != '1':
                    continue    
                year_link = row.find_element(By.CSS_SELECTOR, 'td a.subtle-link')
                concerts_link = row.find_element(By.CSS_SELECTOR, 'td.table-cell-no-stretch a')
                
                year = year_link.text.strip() + " concerts"
                concerts = int(concerts_link.text.split()[0])
                
                concerts_per_year.append({year: concerts})
                count += 1
            except Exception as e:
                print(f"Error processing row: {e}")

    except Exception as e:
        print(f"Element not found: {e}")

    finally:
        driver.close()
        driver.quit()
    
    return concerts_per_year, venue_link



def main():
    start_time = time.time()  # Start the timer

    browser = create_browser()
    
    # prompt = "List all the things an individual who bought VIP package at this venue can enjoy. I want to know what I can have as a VIP at this venue if such thing exists."
    # format_request = 'Return the response as json: {"vip_package_access": str}.'
    # conversation = traverse_all_pages("https://bourbonroomhollywood.com/", browser, max_page_visits=30)
    
    # response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
    # print(f'Payload: {extract_json_code_block(response)}')
    
    prompt = "Tell me how many bars this venue has."
    format_request = 'Return the response as json: {"number_of_bars": int}. If you are unable to find anything, set the json value to None'
    conversation = traverse_pages_intelligently("https://bourbonroomhollywood.com/", browser, max_page_visits=4, venue='bourbon room',search_items=["number of bars"])
    
    response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
    print(f'Raw GPT final Response: {response}')
    print(f'Payload: {extract_json_code_block(response)}')

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    print(f"Time taken for the main function: {elapsed_time:.2f} seconds")

# if __name__ == '__main__':
#     main()
if __name__ == '__main__':
    main()
    # browser = create_undetected_non_headless_browser()
    # prompt = f'List all VIP benefits at the venue `{'The Coach House Concert Hall'}`.'
    
    # format_request = 'Return as JSON: {"vip_packages_access": str}.'
    # prompt = f'Find the number of stories of the music or theatre venue `{'The Coach House Concert Hall'}`.'
    # format_request = 'Return the response as json: {"number_of_stories": int}. If unable to find accurate data, set the json value to None'

    # search_items = ['number of floors', 'VIP packages', 'capacity', 'number of bars']
    # conversation, page_data = traverse_all_pages('https://thecoachhouse.com/', browser, max_page_visits=10, search_items=search_items)
    # response, conversation = aggregate_gpt_request(prompt + format_request,conversation)
    # print(response)
    #print(scrape_concerts_per_year('the lodge room'))