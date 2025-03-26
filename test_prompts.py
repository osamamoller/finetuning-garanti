import pandas as pd
import json
import re
import requests
import os
from time import sleep
from openpyxl import load_workbook
from dotenv import load_dotenv

load_dotenv()

# API Configuration for Azure OpenAI
API_KEY = os.environ.get("OPENAI_API_KEY")  # Get API key from environment variable
AZURE_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")  # e.g., "https://<your-resource-name>.openai.azure.com"
DEPLOYMENT_NAME = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")  # Your deployment name
API_VERSION = "2023-03-15-preview"
API_URL = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT_NAME}/chat/completions?api-version={API_VERSION}"

print("API_URL: ", API_URL)

MODEL_NAME = "gpt-4-vision-preview"  # Using vision model for image support

def read_excel_prompts(excel_file_path):
    """
    Read prompts from Excel file
    """
    # Read input data
    input_df = pd.read_excel(excel_file_path, sheet_name="Prompts - Input Data")
    
    # Read result data sheet to understand structure
    result_df = pd.read_excel(excel_file_path, sheet_name="Prompts - Result Data")
    
    return input_df, result_df

def read_jsonl_data(jsonl_file_path):
    """
    Read images and expected answers from JSONL file
    """
    test_cases = []
    
    with open(jsonl_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            # Extract relevant information from JSONL structure
            # Assuming each JSON contains messages array with user prompt and assistant response
            for entry in data.get('messages', []):
                if entry.get('role') == 'user':
                    # Extract image URL from user message
                    image_url = None
                    for content_item in entry.get('content', []):
                        if content_item.get('type') == 'image_url':
                            image_url = content_item.get('image_url', {}).get('url')
                
                if entry.get('role') == 'assistant':
                    # Assistant message contains the expected response
                    expected_response = entry.get('content', '')
                    
                    # Extract final answer using regex
                    expected_answer = extract_final_answer(expected_response)
            
            if image_url and expected_answer:
                test_cases.append({
                    'image_url': image_url,
                    'expected_answer': expected_answer
                })
    
    return test_cases

def extract_final_answer(response_text):
    """
    Use regex to extract the final answer from the response
    Looking for patterns like "Final Answer: X" or "**Final Answer: X**"
    """
    # Pattern to match final answer with or without markdown formatting
    patterns = [
        r'[*]*Final Answer:\s*(.*?)\s*(\(.*?\))[*]*',  # Matches "Final Answer: Month YYYY (YYYY-MM)"
        r'[*]*Final Answer:\s*(.*?)[*]*$',              # Matches "Final Answer: X"
        r'[*]*Final Output:\s*(.*?)[*]*$',              # Matches "Final Output: X"
        r'Formatted result:\s*(.*?)$'                   # Matches "Formatted result: X"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
        if match:
            # For the first pattern that has capture groups for both parts
            if len(match.groups()) > 1 and '(' in match.group(0):
                return match.group(0).strip()
            return match.group(1).strip()
    
    # If no match found, try to find any answer format like Month YYYY (YYYY-MM)
    date_pattern = r'([A-Z][a-z]+\s+\d{4}\s+\(\d{4}-\d{2}\))'
    match = re.search(date_pattern, response_text)
    if match:
        return match.group(1).strip()
    
    # If all else fails, return the last 100 characters as a fallback
    return response_text[-100:].strip()

def send_api_request(prompt_text, image_url):
    """
    Send a request to the Azure OpenAI API with the given prompt and image
    """
    headers = {
        "Content-Type": "application/json",
        "api-key": f"{API_KEY}"
    }
    
    # Construct the messages array
    messages = []
    
    # Create user message content
    user_content = []
    
    # Add text content
    user_content.append({
        "type": "text",
        "text": prompt_text
    })
    
    # Add image
    user_content.append({
        "type": "image_url",
        "image_url": {"url": image_url}
    })
    
    # Add the user message
    messages.append({
        "role": "user",
        "content": user_content
    })
    
    # Prepare the request payload
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        
        # Parse the response JSON
        response_data = response.json()
        
        # Extract the assistant's response text
        assistant_response = response_data["choices"][0]["message"]["content"]
        return assistant_response
    
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return f"Error: {e}"

def calculate_precision(extracted_result, expected_result):
    """
    Calculate a precision score (0.0 to 1.0) based on date comparison:
    - 1.0 if both month and year match
    - 0.5 if either month or year matches
    - 0.0 otherwise
    """
    if not extracted_result or not expected_result:
        return 0.0
    
    # Normalize both strings for comparison
    extracted_norm = extracted_result.lower().strip()
    expected_norm = expected_result.lower().strip()
    
    # If exact match
    if extracted_norm == expected_norm:
        return 1.0
    
    # Extract month and year from the expected and extracted results
    # Look for patterns like "YYYY-MM" or "Month YYYY"
    extracted_date_code = re.search(r'(\d{4})-(\d{2})', extracted_norm)
    expected_date_code = re.search(r'(\d{4})-(\d{2})', expected_norm)
    
    # Look for month names and years
    months = ["january", "february", "march", "april", "may", "june", "july", 
              "august", "september", "october", "november", "december"]
    
    extracted_month_name = None
    extracted_year_text = None
    
    for month in months:
        if month in extracted_norm:
            extracted_month_name = month
            # Try to find a year near the month
            year_match = re.search(r'\b(20\d{2})\b', extracted_norm)
            if year_match:
                extracted_year_text = year_match.group(1)
            break
    
    expected_month_name = None
    expected_year_text = None
    
    for month in months:
        if month in expected_norm:
            expected_month_name = month
            # Try to find a year near the month
            year_match = re.search(r'\b(20\d{2})\b', expected_norm)
            if year_match:
                expected_year_text = year_match.group(1)
            break
    
    # Check if we have date codes to compare
    if extracted_date_code and expected_date_code:
        extracted_year = extracted_date_code.group(1)
        extracted_month = extracted_date_code.group(2)
        expected_year = expected_date_code.group(1)
        expected_month = expected_date_code.group(2)
        
        # Check if both month and year match
        if extracted_year == expected_year and extracted_month == expected_month:
            return 1.0
        # Check if either month or year matches
        elif extracted_year == expected_year or extracted_month == expected_month:
            return 0.5
    
    # Compare text-based dates if available
    if extracted_month_name and expected_month_name and extracted_year_text and expected_year_text:
        month_match = extracted_month_name == expected_month_name
        year_match = extracted_year_text == expected_year_text
        
        if month_match and year_match:
            return 1.0
        elif month_match or year_match:
            return 0.5
    
    # If we have mixed formats, try to compare what we can
    if extracted_date_code and expected_month_name and expected_year_text:
        extracted_year = extracted_date_code.group(1)
        extracted_month = int(extracted_date_code.group(2))
        expected_year = expected_year_text
        expected_month = months.index(expected_month_name) + 1
        
        if extracted_year == expected_year and extracted_month == expected_month:
            return 1.0
        elif extracted_year == expected_year or extracted_month == expected_month:
            return 0.5
    
    # Similarly, check the reverse mixed format
    if expected_date_code and extracted_month_name and extracted_year_text:
        expected_year = expected_date_code.group(1)
        expected_month = int(expected_date_code.group(2))
        extracted_year = extracted_year_text
        extracted_month = months.index(extracted_month_name) + 1
        
        if extracted_year == expected_year and extracted_month == expected_month:
            return 1.0
        elif extracted_year == expected_year or extracted_month == expected_month:
            return 0.5
    
    # Default to 0.0 if no date comparison was possible
    return 0.0

def update_excel_results(excel_file_path, result_df):
    """
    Write the test results back to the Excel file
    """
    # Load the existing workbook to preserve formatting
    workbook = load_workbook(excel_file_path)
    writer = pd.ExcelWriter(excel_file_path, engine='openpyxl')
    writer._book = workbook
    
    # Write the updated results dataframe to the sheet
    result_df.to_excel(writer, sheet_name="Prompts - Result Data", index=False)
    
    # Save the changes
    writer.close()
    print(f"Results written to {excel_file_path}")

def run_tests(excel_file_path, jsonl_file_path):
    """
    Main function to run the tests.
    Reads prompts from the Excel file and test cases (images/expected answers) from the JSONL file,
    sends API requests for each prompt-test case pair, extracts and calculates precision,
    then writes all the results back to the Excel file.
    """
    print("Starting test execution...")
    
    # Read prompts from Excel
    prompt_df, _ = read_excel_prompts(excel_file_path)
    # Always reinitialize result_df with all IDs from prompt_df
    result_df = prompt_df[['ID']].copy()
    
    # Read test cases (images and expected answers) from JSONL
    test_cases = read_jsonl_data(jsonl_file_path)
    
    print(f"Found {len(prompt_df)} prompts and {len(test_cases)} test cases")
    
    # For each prompt
    for prompt_idx, prompt_row in prompt_df.iterrows():
        prompt_id = prompt_row['ID']
        prompt_text = prompt_row['Prompt']
        
        print(f"Processing prompt ID: {prompt_id}")
        
        # For each test case (image + expected answer)
        for i, test_case in enumerate(test_cases):
            image_url = test_case['image_url']
            expected_answer = test_case['expected_answer']
            
            print(f"  Testing with image {i+1}/{len(test_cases)}: {image_url}")
            
            # Send API request with prompt and image
            print("  Sending API request...")
            response = send_api_request(prompt_text, image_url)
            
            # Extract the final answer using regex
            print("  Extracting final answer...")
            extracted_result = extract_final_answer(response)
            
            # Calculate precision score
            precision = calculate_precision(extracted_result, expected_answer)
            
            print(f"  Extracted: {extracted_result}")
            print(f"  Expected: {expected_answer}")
            print(f"  Precision: {precision}")
            
            # Define column names for the test case result
            result_column = f"Result_{i+1}"
            precision_column = f"Precision_{i+1}"
            
            # Ensure that the columns exist in the result dataframe
            if result_column not in result_df.columns:
                result_df[result_column] = None
            if precision_column not in result_df.columns:
                result_df[precision_column] = None
            
            # Update the result dataframe for the current prompt
            result_df.loc[result_df['ID'] == prompt_id, result_column] = extracted_result
            result_df.loc[result_df['ID'] == prompt_id, precision_column] = precision
            
            # Rate limit to avoid API throttling
            sleep(1)
    
    # Write the updated results back to the Excel file
    update_excel_results(excel_file_path, result_df)
    
    print("\nTest Execution Summary")
    print("======================")
    print(f"Total tests: {len(prompt_df) * len(test_cases)}")
    print(f"All results have been updated in {excel_file_path}")


if __name__ == "__main__":
    excel_file_path = r"C:\Users\osabidi\sandbox\prompts_and_results.xlsx"  # Update with your Excel file path
    jsonl_file_path = r"C:\Users\osabidi\finetuning-garanti\zoomed\inflated_dataset.jsonl"     # Update with your JSONL file path
    run_tests(excel_file_path, jsonl_file_path)