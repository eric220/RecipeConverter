import base64
import google.generativeai as genai
import json
import re
from py_files import config
import glob
import logging
import os, shutil

logging.basicConfig(
    filename="logging/app.log",
    encoding="utf-8",
    filemode="a",
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M"
)

DATA_PATH = '../data/'
HTML_FILE_PATH = f'{DATA_PATH}html_files/'

api_key = config.GEMINI_API_KEY
if not api_key:
    raise ValueError("API key not found. Please set GEMINI_API_KEY in your .env file.")
genai.configure(api_key=api_key)

def encode_image_to_base64(image_path: str) -> str:
    """ Read an image file and return its byte string. """
    with open(image_path, 'rb') as f:
        image_bytes = f.read()
    return image_bytes

def extract_json_from_response(response) -> dict:
    """
    Extract JSON content from the LLM response, removing any code fence markers.
    """
    if not hasattr(response, "candidates") or not response.candidates:
        raise ValueError("Response does not contain valid candidates.")
    raw_text = response.candidates[0].content.parts[0].text
    json_str = re.sub(r"^```json|```$", "", raw_text.strip(), flags=re.MULTILINE)
    try:
        parsed_data = json.loads(json_str)
        return parsed_data
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}\\nRaw LLM Response:\\n{raw_text}")

def get_recipe(image_path: str):
    """
    Step 1: Ask the model to identify any part numbers, '
    """
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-lite")
    encoded_image = encode_image_to_base64(image_path)
    prompt = """
    You are a data entry expert for a restaurant. Yor job is to accurately and completly copy a recipe you are given.
    You will be given an image. Convert the given image to valid html so we can display the recipe in a browser.
    Always return only a valid HTML. Some important things to consider are:
    The title of the dish,
    Ingregients and amounts,
    Steps taken,
    and Apperance (focus on indentation)
    """
    response = model.generate_content([
        {"mime_type": "image/png", "data": encoded_image},
        prompt
    ])
    json_response = response#extract_json_from_response(response)
    return json_response

file_paths = glob.glob('../data/raw/*PNG')

def get_title(results):
    try:
        html_str = re.sub(r"^```html|```$", "", results.strip(), flags=re.MULTILINE)
        title = html_str.split('<h1>')[1]
        title = title.split('</h1>')[0]
        return (html_str, title)
    except ValueError:
        logging.error("Title extraction error", exc_info=True)
        return None

def check_filepath(path):
    # Check if the file exists
    if os.path.exists(file_path):
        print(f"The file {file_path} exists.")
        return False
    else:
        return True

if __name__ == "__main__":
    for f_p in file_paths:
        try:
            recipe = get_recipe(f_p).candidates[0].content.parts[0].text
            html_str, title = get_title(recipe)
            file_path = f'{HTML_FILE_PATH}{title}.html'
            if check_filepath(file_path):
                with open(f'{file_path}', 'w') as file:
                    file.write(f"{html_str}")
            else:
                raise ValueError
        except ValueError:
            destination = f'{DATA_PATH}trouble'
            shutil.move(f_p, destination)
            print(f'Image {f_p} was not processed')    