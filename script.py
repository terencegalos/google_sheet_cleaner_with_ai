
import logging
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import openai
from itertools import zip_longest





# Define the log folder and file
log_folder = 'logs'
log_file = os.path.join(log_folder,'script.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)


# Google Sheets settings
SHEET_NAME = "4K Email Campaign Cleaner"
# SHEET_NAME = "CRM Mastersheet"

# Google Sheet Credentials
credentials_file = './creds301.json'

# Load environment variables from .env file
load_dotenv()

# Retrieve the api key from environment variable
api_key = os.getenv('API_KEY')

# Set the OpenAI API Key for authentication
openai.api_key = api_key


# Define the cleaning rules in the prompt for company names
prompt_company_name = """
Prompt: Clean Prospect List for Email Campaign

Instructions:

1. Process each company name according to the specific rules listed below.
2. Apply transformations to achieve the desired “final result.”
3. Ensure consistency and readability of the output.

Rules:

1. Remove company type suffixes like Inc, LLC, Ltd, Architects, etc., unless otherwise stated.
   - Example: Gulf Breeze Consulting, Inc. → GBC
2. Replace symbols like “+” with words (“and”).
   - Example: Hornberger + Worstell Architects → Hornberger and Worstell
3. Abbreviate all names containing three or more words, even if they appear consistent or readable.
   - Example: Waterstone Development Group → WDG
4. Remove full stops in abbreviations.
   - Example: H.J. Martin and Son → HJ Martin and Son
5. If the company name is already fine and contains fewer than three words, leave it as is.
   - Example: Euthenics → Euthenics
6. When abbreviating, use the first letter of each key word, preserving capitalization.
   - Example: Raino Ogden Architects → ROA

Examples for Reference:

- Murphy Stillings LLC → Murphy Stillings
- Hornberger + Worstell Architects → Hornberger and Worstell
- Raino Ogden Architects → ROA
- Ranon & Partners, Inc. Architects → Ranon & Partners
- Design Edge Architecture → DEA
- Waterstone Development Group → WDG
- Aria Group Architects, Inc. → AGA

Output Format:
For each entry, provide the cleaned company name in a single line.
"""




# Define the cleaning rules in the prompt for first names
prompt_first_name = """
Prompt: Clean and Format First Names for Professional Use

Instructions:

1. Process each first name according to the specific rules listed below.
2. Apply transformations to achieve the desired "final result."
3. Ensure consistency and readability of the output.

Rules:

1. Correct improper capitalization:
   - Capitalize only the first letter of the name, leaving the rest lowercase unless the name includes initials or other valid uppercase letters.
   - Examples:
     - frank → Frank
     - ALEX → Alex

2. Handle accents and corrupted characters:
   - Replace corrupted or special characters with their plain equivalents (e.g., Ã¡ → a).
   - Do not preserve accents; convert all names to their plain-text version.
   - Examples:
     - AdriÃ¡n → Adrian
     - Olga MarÃ­a → Olga Maria

3. Remove professional titles, suffixes, or prefixes:
   - Remove titles like Arq., Dr., Eng., etc.
   - Examples:
     - Arq. Olga Mariela → Olga Mariela
     - Dr. Adam → Adam

4. Handle initials and abbreviations:
   - If the name contains initials (e.g., A.J.), remove the periods to standardize.
   - Examples:
     - A.J. → AJ
     - Adam E. → Adam
     - Abdel F. → Abdel

5. Remove trailing or irrelevant details:
   - Ensure the name contains only the first name (and middle name if applicable).
   - Examples:
     - Arturo A. → Arturo
     - Olga Mariela → Olga Mariela

6. Catch-all cleanup:
   - Remove any leading/trailing whitespace.
   - Ensure the result is a clean, readable name suitable for use in professional communication.

Examples for Reference:

- Arq. Olga Mariela → Olga Mariela
- Abdel F. → Abdel
- Adam E. → Adam
- frank → Frank
- AdriÃ¡n → Adrian
- A.J. → AJ
- Arturo A. → Arturo
- ALEX → Alex

Output Format:
Provide each cleaned name on a new line, formatted for professional use.
"""
campaign_list = [
    {"name_column":1,"cleaned_name_column":4,"cleaned_name_column_alpha":"D","prompt":prompt_company_name,},
    {"name_column":2,"cleaned_name_column":5,"cleaned_name_column_alpha":"E","prompt":prompt_first_name,}
    ]





def authenticate_google_sheet(credentials_file):
    """Authenticate and open the Google Sheet."""
    logging.info('Authorizing Google Spreadsheet using credentials...')
    creds = Credentials.from_service_account_file(
        credentials_file,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME)


def process_name(name,prompt):
    logging.info(f"Processing : {name}")
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role":"system","content":prompt},
                {"role":"user","content":f"Please clean the following company name according to the rules: {name}"}
            ],
            temperature=0.7,
            max_tokens=50 # Adjust based on expected output length
        )
        processed_name = response.choices[0].message.content.strip()
        logging.info(f'Processing completed - Original: {name} - Processed name: {processed_name}')
        return processed_name
    except Exception as e:
        return f"Error processing: {str(e)}"
    



def clean_google_sheet(sheet):
    """Clean the company names using AI"""
    worksheet = sheet.get_worksheet(1) # Index starts 0 (get the second tab)
    
    # Assuming the name of the sheet is "Unique names"
    if worksheet.title == "Unique names":
                
        for campaign in campaign_list:
            # Get all names and processed name starting from 3rd row
            names = worksheet.col_values(campaign['name_column'])[3:]
            cleaned_names = worksheet.col_values(campaign['cleaned_name_column'])[3:]
            
            # logging.info(f"names: {names[:10]}")
            # logging.info(f"cleaned_names: {cleaned_names[:10]}")
            
            for i,(name,cleaned_name) in enumerate(
                zip_longest(names,cleaned_names,fillvalue=""), start=4
            ):
                
                # Process only if cleaned name is empty
                if name and not cleaned_name:
                    # Start cleaning
                    processed_name = process_name(name,campaign['prompt'])
                    
                    # Save it to the spreadsheet
                    logging.info('Saving...')
                    worksheet.update(
                        range_name=f"{campaign['cleaned_name_column_alpha']}{i}", values=[[processed_name]]
                    )
                    
                    logging.info(f'Saved to spreadsheet.')
                
            



def main():
    logging.info("Script started.")
    try:

        sheet = authenticate_google_sheet(credentials_file)
        clean_google_sheet(sheet)
        logging.info('Script completed successfully.')
    except Exception as e:
        logging.error(f"Script stopped unexpectedly: {e}")




if __name__ == "__main__":
    main()