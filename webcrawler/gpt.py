import os
import re
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
import logging

# Load environment variables
load_dotenv(".env.local")
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_client():
    """Creates an Azure OpenAI client using API key and endpoint from environment variables."""
    try:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        return client
    except Exception as e:
        logger.error(f"Error creating Azure OpenAI client: {e}")
        return None

def gpt_request(gpt_instruction: str, user_prompt: str, client=None):
    """Executes GPT request with a given instruction and user prompt."""
    if client is None:
        client = create_client()
        if client is None:
            return ""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            seed=42,
            temperature=0.3,
            messages=[
                {"role": "system", "content": gpt_instruction},
                {"role": "user", "content": user_prompt}
            ]
        )
        payload = response.choices[0].message.content
        return payload
    except Exception as e:
        logger.error(f"Error during GPT request: {e}")
        return ""

def aggregate_gpt_request(user_prompt: str, conversation=None, client=None):
    """Adds multiple conversation messages to a single conversation to avoid max token error."""
    if conversation is None:
        conversation = []

    if client is None:
        client = create_client()
        if client is None:
            return "", conversation

    conversation.append({"role": "user", "content": user_prompt})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            seed=42,
            temperature=0.3,
            messages=conversation
        )

        payload = response.choices[0].message.content
        conversation.append({"role": "assistant", "content": payload})

        return payload, conversation
    except Exception as e:
        logger.error(f"Error during GPT request with conversation: {e}")
        return "", conversation

def remove_json_markdown(the_string): # either gpt is not doing a good job or this is not doing a good job 
    """Removes code block markers (like ```json) from the string."""
    return re.sub(r"json|```", "", the_string).strip()

def extract_json_code_block(input_string: str) -> dict:
    """
    Extracts the JSON code inside a code block from the given string.
    Handles single quotes and Python-specific 'None' by converting them to JSON-compatible format.
    
    :param input_string: The string containing the JSON code block.
    :return: The extracted JSON data as a dictionary or an empty dictionary if parsing fails.
    """
    try:
        # Log the full input string for debugging
        logger.debug(f"Raw input string: {input_string}")
        
        # First, try to find a well-formatted JSON block within triple backticks
        match = re.search(r"```json\s*(\{.*?\})\s*```", input_string, re.DOTALL)
        
        if not match:
            # If no code block is found, search for any JSON-like structure in the input
            match = re.search(r"(\{.*?\})", input_string, re.DOTALL)
        
        if match:
            json_content = match.group(1).strip()
            
            # Replace single quotes with double quotes to make it valid JSON
            json_content = json_content.replace("'", '"')
            
            # Replace Python 'None' with JSON 'null'
            json_content = json_content.replace("None", "null")
            
            # Try to load the JSON
            return json.loads(json_content)  # Safely load the JSON content

        logger.warning("No JSON code block or JSON-like content found in the input string.")
        return {}
    
    except json.JSONDecodeError as e:
        # Log the error and the problematic string
        logger.error(f"Error decoding JSON: {e}")
        logger.error(f"Problematic JSON content: {input_string}")
        return {}

def process_response_as_json(response: str) -> dict:
    """
    Tries to parse the response as JSON, handling cases where the response is not valid JSON.
    :param response: The raw response from GPT or web scraping.
    :return: A dictionary with the parsed JSON data, or an empty dictionary if parsing fails.
    """
    try:
        # First attempt to extract any JSON code block
        json_data = extract_json_code_block(response)
        if json_data:
            return json_data

        # If no code block, assume the entire response is a JSON string
        return json.loads(response)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from response: {e}")
        return {}

if __name__ == "__main__":
    # Example usage of gpt_request with improvements
    gpt_instruction = 'You are a helpful assistant.'
    user_prompt = 'Tell me a life-changing story about eating pudding.'
    
    # Send GPT request
    response = gpt_request(gpt_instruction, user_prompt)

    # Process the response as JSON if necessary
    json_data = process_response_as_json(response)
    
    # Output the response or the parsed JSON data
    print("Response:", response)
    print("Parsed JSON:", json_data)
