import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import undetected_chromedriver as uc
import os
import platform
import subprocess

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_chrome_options():
    options = Options()
    options.add_argument("--headless")  # Runs Chrome in headless mode.
    options.add_argument("--no-sandbox")  # Bypass OS security model
    options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems
    options.add_argument("--disable-gpu")  # Disable GPU
    options.page_load_strategy = 'normal'
    return options

def create_browser():
    options = get_chrome_options()
    try:
        logger.info("Starting Chrome browser...")
        # Use webdriver_manager to install the matching ChromeDriver version dynamically
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        logger.info("Chrome browser started successfully.")
        return driver
    except Exception as e:
        logger.error(f"Error starting Chrome browser: {e}")
        raise

def create_undetected_non_headless_browser():
    """Used for bypassing Cloudflare protections."""
    options = Options()
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")  # Spoof user-agent

    try:
        logger.info("Starting undetected Chrome browser...")
        driver = uc.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        logger.info("Undetected Chrome browser started successfully.")
        return driver
    except Exception as e:
        logger.error(f"Error starting Chrome browser: {e}")
        raise

def kill_chrome():
    current_os = platform.system()

    try:
        if current_os == "Windows":
            subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"], check=True)
            print("Chrome killed successfully on Windows.")
        elif current_os == "Darwin" or current_os == "Linux":
            subprocess.run(["pkill", "chrome"], check=True)
            print("Chrome killed successfully on macOS/Linux.")
        else:
            print(f"Unsupported operating system: {current_os}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to kill Chrome: {e}")

# Example usage
if __name__ == "__main__":
    kill_chrome()
    # browser = create_browser()
    # browser.get("https://www.google.com")
    # print(browser.title)
    # browser.quit()
