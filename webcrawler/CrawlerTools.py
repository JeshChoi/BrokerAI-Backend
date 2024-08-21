from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

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

def scrape_page_text(url: str, browser) -> str:
    """Returns text from specified URL, pass browser in"""
    text = ""
    try:
        browser.get(url)
        wait = WebDriverWait(browser, 5)
        time.sleep(5)
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

def traverse_all_pages(website_url: str, browser, max_page_visits = 10):
    """Traverses all of the pages of a given webpage and returns list of webcontent from all the pages"""
    website_domain = get_domain(website_url)
    url_queue = get_all_links_on_page(website_url, browser)
    visited_urls = set([])
    visited_count = 0
    
    conversation = []
    traverse_prompt = "You will be given multiple webpages, where you will have to look through to give accurate data to my questions about data."
    response, conversation = aggregate_gpt_request(traverse_prompt, conversation=conversation)
    while url_queue:
        if visited_count == max_page_visits:
            break
        current_url = url_queue.pop()
        if not check_domain(current_url, website_domain):
            continue
        if current_url in visited_urls:
            continue
        data_content = scrape_page_text_headless(current_url, browser)
        conversation.append({"role": "user", "content": data_content})
        
        visited_urls.add(current_url)
        visited_count += 1
        
        new_links = get_all_links_on_page(current_url, browser)
        url_queue.extend(new_links)
        
    return conversation

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
        
        for row in rows:
            try:
                row_text = row.text
                if row_text[0] != '2' and row_text[0] != '1':
                    continue    
                year_link = row.find_element(By.CSS_SELECTOR, 'td a.subtle-link')
                concerts_link = row.find_element(By.CSS_SELECTOR, 'td.table-cell-no-stretch a')
                
                year = year_link.text.strip() + " concerts"
                concerts = int(concerts_link.text.split()[0])
                
                concerts_per_year.append({year: concerts})
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
    
    prompt = "List all the things an individual who bought VIP package at this venue can enjoy. I want to know what I can have as a VIP at this venue if such thing exists."
    format_request = 'Return the response as json: {"vip_package_access": str}.'
    conversation = traverse_all_pages("https://bourbonroomhollywood.com/", browser, max_page_visits=30)
    
    response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
    print(f'Payload: {extract_json_code_block(response)}')
    
    prompt = "Tell me how many bars this venue has."
    format_request = 'Return the response as json: {"number_of_bars": int}. If you are unable to find anything, set the json value to None'
    conversation = traverse_all_pages("https://bourbonroomhollywood.com/", browser, max_page_visits=30)
    
    response, conversation = aggregate_gpt_request(prompt + format_request, conversation)
    print(f'Payload: {extract_json_code_block(response)}')

    end_time = time.time()  # End the timer
    elapsed_time = end_time - start_time  # Calculate the elapsed time
    print(f"Time taken for the main function: {elapsed_time:.2f} seconds")

# if __name__ == '__main__':
#     main()
if __name__ == '__main__':
    print(scrape_concerts_per_year('the lodge room'))