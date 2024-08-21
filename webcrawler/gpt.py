import os
import re
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv(".env.local")
load_dotenv()

def create_client(): 
    client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
            api_version="2024-02-01",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
    
    return client

def gpt_request(gpt_instruction: str, user_prompt: str, client = None):
        """executes GPT request with given instruction and user prompt"""
        if client == None: 
            client = create_client()
            
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

def aggregate_gpt_request(user_prompt: str, conversation: [str] = [],  client = None):
    """adds multiple conversation messages to a single conversation to avoid max token error"""
    if client == None: 
            client = create_client()
            
    conversation.append({"role": "user", "content": user_prompt})
    response = client.chat.completions.create(
            model="gpt-4o",
            seed=42,
            temperature=0.3,
            messages=conversation
        )
    
    payload = response.choices[0].message.content
    conversation.append({"role": "assistant", "content": payload})
    return payload, conversation
    
def remove_json_markdown(the_string):
    return re.sub(r"json|```", "", the_string).strip()

def extract_json_code_block(input_string: str) -> str:
    """
    Extracts the code inside a JSON code block from the given string.
    
    :param input_string: The string containing the JSON code block.
    :return: The extracted JSON code or an empty string if no code block is found.
    """
    match = re.search(r"```json\s*(.*?)\s*```", input_string, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""
    
if __name__ == "__main__":
    print(gpt_request('you are a jolly guy','tell me a life changing story about eatinig pudding'))