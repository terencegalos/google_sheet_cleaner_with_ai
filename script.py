
import logging
import os
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import openai
from itertools import zip_longest
import time





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



def get_prompts_from_sheet(sheet):
    """Retrieve prompts from the third tab of the Google Sheet."""
    logging.info("Retrieving prompts from Google Sheet...")
    worksheet = sheet.get_worksheet(2)
    company_prompt = worksheet.range('B3:F35')
    first_name_prompt = worksheet.range('B39:F71')
    
    # Convert cell values to strings
    company_prompt_text = ''.join([cell.value for cell in company_prompt])
    first_name_prompt_text = ''.join([cell.value for cell in first_name_prompt])
    
    logging.info(f"Company prompt: {company_prompt_text}")
    time.sleep(3)
    
    logging.info(f"First name prompt: {first_name_prompt_text}")
    time.sleep(3)
    
    return company_prompt_text, first_name_prompt_text



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
    



def clean_google_sheet(sheet,prompt_company_name,prompt_first_name):
    """Clean the company names using AI"""
    worksheet = sheet.get_worksheet(1) # Index starts 0 (get the second tab)
    
    # Assuming the name of the sheet is "Unique names"
    if worksheet.title == "Unique names":
        
        campaign_list = [
            {"name_column":1,"cleaned_name_column":4,"cleaned_name_column_alpha":"D","prompt":prompt_company_name,},
            {"name_column":2,"cleaned_name_column":5,"cleaned_name_column_alpha":"E","prompt":prompt_first_name,}
        ]
                
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
        company_prompt, first_name_prompt = get_prompts_from_sheet(sheet)
        clean_google_sheet(sheet, company_prompt, first_name_prompt)
        logging.info('Script completed successfully.')
    except Exception as e:
        logging.error(f"Script stopped unexpectedly: {e}")




if __name__ == "__main__":
    main()