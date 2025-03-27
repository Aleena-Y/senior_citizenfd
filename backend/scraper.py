# This is the Scrapper Code v0.5
import pandas as pd
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import sqlite3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_selenium_driver():
    """Setup Chrome WebDriver with appropriate options"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--dns-prefetch-disable')
    chrome_options.add_argument('--disable-web-security')
   
    # Add user agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
   
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(60)  # Reduced timeout from 180 to 60 seconds
    driver.implicitly_wait(10)  # Reduced implicit wait from 20 to 10 seconds
    return driver

def scrape_with_selenium(url, wait_for_element=None, wait_timeout=20, max_retries=2):
    """Generic function to scrape using Selenium with retry mechanism"""
    retry_count = 0
    last_exception = None
   
    while retry_count < max_retries:
        driver = None
        try:
            driver = setup_selenium_driver()
            driver.get(url)
           
            if wait_for_element:
                try:
                    WebDriverWait(driver, wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, wait_for_element))
                    )
                except TimeoutException:
                    # If specific element not found, check if page has any content
                    if len(driver.page_source) < 100:  # Arbitrary small size
                        raise TimeoutException("Page appears to be empty")
           
            # Add a small delay to ensure dynamic content loads
            time.sleep(1)  # Reduced from 2 seconds to 1 second
           
            return driver.page_source
           
        except Exception as e:
            last_exception = e
            retry_count += 1
            logger.warning(f"Attempt {retry_count} failed for URL {url}: {str(e)}")
            time.sleep(retry_count * 1)  # Reduced backoff time
           
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
   
    if last_exception:
        logger.error(f"All {max_retries} attempts failed for URL {url}: {str(last_exception)}")
    return None

def find_relevant_tables(soup, class_keywords):
    """Find tables that might contain FD rates"""
    tables = []
   
    # Direct table search
    tables.extend(soup.find_all('table'))
   
    # Search in specific div classes
    for keyword in class_keywords:
        for div in soup.find_all(['div', 'section'], class_=lambda x: x and keyword in x.lower()):
            tables.extend(div.find_all('table'))
   
    # Search near relevant headings
    for heading in soup.find_all(['h1', 'h2', 'h3', 'h4'],
                               string=re.compile(r'fixed deposit|fd|interest rate', re.I)):
        next_table = heading.find_next('table')
        if next_table:
            tables.append(next_table)
   
    return tables

def extract_tenure_days(tenure_text):
    """Extract minimum and maximum days from tenure description"""

    if not tenure_text or not isinstance(tenure_text, str):
        return {'min_days': None, 'max_days': None}

    result = {'min_days': None, 'max_days': None}

    # Clean up the text
    tenure_text = tenure_text.lower().strip()

    # Try to extract days directly
    days_pattern = r'(\d+)\s*days?\s*(?:to|up to|-|and up to|and|less than)\s*(\d+)\s*days?'
    days_match = re.search(days_pattern, tenure_text, re.IGNORECASE)

    if days_match:
        result['min_days'] = int(days_match.group(1))
        result['max_days'] = int(days_match.group(2))
        return result

    # Try to extract years and convert to days
    years_pattern = r'(\d+)\s*years?\s*(?:\d+\s*days?)?\s*(?:to|up to|-|and up to|and|less than)\s*(\d+)\s*years?'
    years_match = re.search(years_pattern, tenure_text, re.IGNORECASE)

    if years_match:
        result['min_days'] = int(years_match.group(1)) * 365
        result['max_days'] = int(years_match.group(2)) * 365
        return result

    # Try to extract months and convert to days
    months_pattern = r'(\d+)\s*months?\s*(?:to|up to|-|and up to|and|less than)?\s*(?:to|up to|-|and up to|and|less than)?\s*(\d+)\s*months?'
    months_match = re.search(months_pattern, tenure_text, re.IGNORECASE)

    if months_match:
        result['min_days'] = int(months_match.group(1)) * 30
        result['max_days'] = int(months_match.group(2)) * 30
        return result

    # Try to extract mixed units (e.g., "1 year to 2 years")
    mixed_pattern = r'(\d+)\s*(day|month|year)s?\s*(?:to|up to|-|and up to|and|less than)\s*(\d+)\s*(day|month|year)s?'
    mixed_match = re.search(mixed_pattern, tenure_text, re.IGNORECASE)

    if mixed_match:
        min_value = int(mixed_match.group(1))
        min_unit = mixed_match.group(2).lower()
        max_value = int(mixed_match.group(3))
        max_unit = mixed_match.group(4).lower()

        # Convert to days
        if min_unit == 'day':
            result['min_days'] = min_value
        elif min_unit == 'month':
            result['min_days'] = min_value * 30
        elif min_unit == 'year':
            result['min_days'] = min_value * 365

        if max_unit == 'day':
            result['max_days'] = max_value
        elif max_unit == 'month':
            result['max_days'] = max_value * 30
        elif max_unit == 'year':
            result['max_days'] = max_value * 365

        return result

    # Single value patterns
    single_days_pattern = r'(\d+)\s*days?'
    single_days_match = re.search(single_days_pattern, tenure_text, re.IGNORECASE)

    if single_days_match:
        days = int(single_days_match.group(1))
        result['min_days'] = days
        result['max_days'] = days
        return result

    single_months_pattern = r'(\d+)\s*months?'
    single_months_match = re.search(single_months_pattern, tenure_text, re.IGNORECASE)

    if single_months_match:
        months = int(single_months_match.group(1))
        result['min_days'] = months * 30
        result['max_days'] = months * 30
        return result

    single_years_pattern = r'(\d+)\s*years?'
    single_years_match = re.search(single_years_pattern, tenure_text, re.IGNORECASE)

    if single_years_match:
        years = int(single_years_match.group(1))
        result['min_days'] = years * 365
        result['max_days'] = years * 365
        return result

    # Pattern for "less than X days"
    less_than_days_pattern = r'less than (\d+)\s*days?'
    less_than_days_match = re.search(less_than_days_pattern, tenure_text, re.IGNORECASE)

    if less_than_days_match:
        days = int(less_than_days_match.group(1))
        result['min_days'] = 1
        result['max_days'] = days - 1
        return result

    # Pattern for "more than X days"
    more_than_days_pattern = r'more than (\d+)\s*days?'
    more_than_days_match = re.search(more_than_days_pattern, tenure_text, re.IGNORECASE)

    if more_than_days_match:
        days = int(more_than_days_match.group(1))
        result['min_days'] = days + 1
        result['max_days'] = days + 365  # Assume one year more
        return result

    # If everything else fails but contains numbers, make a guess
    numbers = re.findall(r'\d+', tenure_text)
    if len(numbers) >= 2:
        result['min_days'] = int(numbers[0])
        result['max_days'] = int(numbers[1])
        return result
    elif len(numbers) == 1:
        # Just one number found, use it for both min and max
        result['min_days'] = int(numbers[0])
        result['max_days'] = int(numbers[0])
        return result

    return result

def clean_rate_text(rate_text):
    """Clean and validate rate text"""
    if not rate_text or not isinstance(rate_text, str):
        return None

    # Remove percentage and whitespace
    rate_text = rate_text.strip().replace('%', '')

    # Try to convert to float
    try:
        rate = float(rate_text)
        return rate if rate > 0 and rate < 100 else None
    except ValueError:
        return None



def scrape_icici():
    """Scrape FD rates from ICICI Bank"""

    url = "https://www.icicibank.com/personal-banking/deposits/fixed-deposit/fd-interest-rates"

    try:
        # Send request with headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        print(f"Fetching ICICI Bank FD rates from {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for the FD rates table
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on ICICI Bank page")

        results = []

        for idx, table in enumerate(tables):
            # Check if this table contains FD rates
            headers = [th.text.strip().lower() for th in table.find_all('th')]

            if any('tenure' in h for h in headers) or any('period' in h for h in headers):
                # Extract rows
                rows = table.find_all('tr')[1:]  # Skip header row

                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        tenure = cells[0].text.strip()

                        # Skip header or empty rows
                        if len(tenure) < 3 or 'tenure' in tenure.lower():
                            continue

                        regular_rate = None
                        if len(cells) >= 2:
                            regular_rate = clean_rate_text(cells[1].text.strip())

                        # Check if senior citizen rate is available
                        senior_rate = None
                        if len(cells) >= 3:
                            senior_rate = clean_rate_text(cells[2].text.strip())

                        # Extract min and max days from tenure
                        tenure_days = extract_tenure_days(tenure)

                        if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                            fd_data = {
                                'tenure_description': tenure,
                                'min_days': tenure_days['min_days'],
                                'max_days': tenure_days['max_days'],
                                'regular_rate': regular_rate,
                                'senior_rate': senior_rate,
                                'category': 'General'
                            }

                            results.append(fd_data)

        if not results:
            print("Failed to scrape ICICI Bank: Could not find FD rate data.")
            return []

        return results

    except Exception as e:
        print(f"Failed to scrape ICICI Bank: {str(e)}")
        return []

def scrape_sbi():
    """Scrape FD rates from SBI"""

    # Try multiple possible URLs for SBI Bank
    urls = [
        "https://sbi.co.in/web/interest-rates/deposit-rates/retail-domestic-term-deposits",
        "https://www.sbi.co.in/web/interest-rates/deposit-rates"
    ]

    # Headers to mimic browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

    for url in urls:
        try:
            print(f"Trying SBI Bank URL: {url}")
            response = requests.get(url, headers=headers, timeout=20)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for tables that might contain FD rates
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables on SBI Bank page from {url}")

            results = []

            # First, look for tables with relevant classes or id attributes
            # SBI often uses specific class names for their rate tables
            fd_keywords = ['fd', 'fixed', 'deposit', 'interest', 'rate']
            sbi_table_classes = ['deposit-table', 'table-interest', 'table-rates', 'table-bordered']

            potential_tables = []
            for idx, table in enumerate(tables):
                # Check class and id attributes
                table_class = ' '.join(table.get('class', [])).lower() if table.get('class') else ''
                table_id = table.get('id', '').lower()

                # Score the table based on how likely it is to contain FD rates
                score = 0

                # Check for SBI specific table classes
                for cls in sbi_table_classes:
                    if cls in table_class:
                        score += 5  # Higher weight for known SBI classes

                # Check for general FD keywords
                for keyword in fd_keywords:
                    if keyword in table_class or keyword in table_id:
                        score += 3

                # Check if the table has a caption or heading before it that mentions FD rates
                caption = table.find('caption')
                caption_text = caption.text.lower() if caption else ''

                if caption_text:
                    for keyword in fd_keywords:
                        if keyword in caption_text:
                            score += 2

                # Check nearby headings for relevance
                prev_headings = table.find_all_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'], limit=3)
                for heading in prev_headings:
                    heading_text = heading.text.lower()
                    for keyword in fd_keywords:
                        if keyword in heading_text:
                            score += 2  # More weight for headings right before the table

                # Try to find header row and check content
                header_rows = table.find_all('tr', limit=2)
                header_text = ''

                for row in header_rows:
                    cells = row.find_all(['th', 'td'])
                    row_text = ' '.join([cell.text.strip().lower() for cell in cells])
                    header_text += ' ' + row_text

                if any(term in header_text for term in ['tenure', 'period', 'term', 'duration']):
                    score += 3
                if any(term in header_text for term in ['interest', 'rate', '%', 'percentage']):
                    score += 3

                potential_tables.append((idx, table, score))

            # Sort tables by score, highest first
            potential_tables.sort(key=lambda x: x[2], reverse=True)

            # Process tables in order of likely relevance
            for idx, table, score in potential_tables:
                if score < 2:  # Skip tables that don't seem relevant at all
                    continue

                print(f"Analyzing table {idx+1} (relevance score: {score})")

                # Try to find the header row first
                header_row = None
                rows = table.find_all('tr')

                for i, row in enumerate(rows[:3]):  # Check first 3 rows for headers
                    cells = row.find_all(['th', 'td'])
                    cell_texts = [cell.text.strip().lower() for cell in cells]

                    if any(term in ' '.join(cell_texts) for term in ['tenure', 'period', 'term', 'days', 'months']):
                        header_row = i
                        print(f"Found header row at index {i}: {cell_texts}")
                        break

                if header_row is None and len(rows) > 0:
                    # If we couldn't identify a clear header row, assume it's the first row
                    header_row = 0
                    cells = rows[0].find_all(['th', 'td'])
                    print(f"Using first row as header: {[cell.text.strip() for cell in cells]}")

                # Now process the data rows
                data_found = False
                for row in rows[header_row+1:]:  # Skip the header row
                    cells = row.find_all(['td', 'th'])

                    if len(cells) < 2:  # Need at least tenure and one rate
                        continue

                    # First column usually has the tenure description
                    tenure = cells[0].text.strip()

                    # Skip rows that don't look like data rows
                    if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                        continue

                    # Try to determine which columns have rates
                    regular_rate = None
                    senior_rate = None

                    # Check the header row to determine which columns might have rates
                    rate_columns = []
                    if header_row is not None and header_row < len(rows):
                        header_cells = rows[header_row].find_all(['th', 'td'])
                        for i, cell in enumerate(header_cells[1:], 1):  # Skip first column (tenure)
                            cell_text = cell.text.strip().lower()
                            if any(term in cell_text for term in ['rate', '%', 'interest', 'public']):
                                rate_columns.append(i)
                            elif 'senior' in cell_text:
                                senior_column = i

                    # If we couldn't determine rate columns, assume they're columns 1 and possibly 2
                    if not rate_columns and len(cells) >= 2:
                        rate_columns = [1]
                        if len(cells) >= 3:
                            # Check if column 2 might be for senior citizens (usually higher rates)
                            rate_2 = clean_rate_text(cells[2].text.strip())
                            rate_1 = clean_rate_text(cells[1].text.strip())
                            if rate_2 is not None and rate_1 is not None and rate_2 > rate_1:
                                senior_rate = rate_2

                    # Extract regular rate from the first identified rate column
                    if rate_columns and rate_columns[0] < len(cells):
                        regular_rate = clean_rate_text(cells[rate_columns[0]].text.strip())

                    # Try to find senior rate if not already found
                    if senior_rate is None and len(cells) >= 3:
                        # Look for higher rates in other columns
                        for i in range(1, min(4, len(cells))):  # Check first few columns only
                            if i == rate_columns[0]:  # Skip already identified regular rate
                                continue

                            rate_val = clean_rate_text(cells[i].text.strip())
                            if rate_val is not None and regular_rate is not None and rate_val > regular_rate:
                                senior_rate = rate_val
                                break

                    # If we couldn't find any valid rates, skip this row
                    if regular_rate is None:
                        continue

                    # We found some rate data
                    data_found = True

                    # Extract min and max days from tenure
                    tenure_days = extract_tenure_days(tenure)

                    if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                        fd_data = {
                            'tenure_description': tenure,
                            'min_days': tenure_days['min_days'],
                            'max_days': tenure_days['max_days'],
                            'regular_rate': regular_rate,
                            'senior_rate': senior_rate,
                            'category': 'General'
                        }
                        results.append(fd_data)

                # If we found valid data in this table, we might be done
                if data_found and len(results) >= 3:
                    print(f"Successfully extracted {len(results)} FD rates from table {idx+1}")
                    return results

            # If we got here with some results but not enough from any single table,
            # return what we have if it seems like enough
            if results and len(results) >= 3:
                print(f"Collected {len(results)} SBI Bank FD rates across tables")
                return results

        except requests.RequestException as e:
            print(f"Error with SBI Bank URL {url}: {str(e)}")

    # If all URLs failed or no data found, return empty list
    print("Failed to scrape SBI Bank: All URLs failed or no data found.")
    return []

def scrape_kotak():
    """Scrape FD rates from Kotak Mahindra Bank"""

    url = "https://www.kotak.com/en/personal-banking/deposits/fixed-deposit/fixed-deposit-interest-rate.html"

    try:
        # Send request with headers to mimic browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        print(f"Fetching Kotak Mahindra Bank FD rates from {url}")
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for the FD rates table
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables on Kotak Mahindra Bank page")

        results = []

        for idx, table in enumerate(tables):
            print(f"Analyzing table {idx+1}")
            headers = []
            header_row = table.find('tr')
            if header_row:
                headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
                print(f"Table {idx+1} headers: {headers}")

            # Check if this table contains FD rates
            if any('tenure' in h for h in headers) or any('period' in h for h in headers) or any('tenor' in h for h in headers):
                print(f"Found potential FD rates table at index {idx}")

                # Try to identify which column has the regular rate and which has senior rate
                regular_col = None
                senior_col = None

                for i, h in enumerate(headers):
                    if 'regular' in h or 'general' in h or 'public' in h or 'non senior' in h:
                        regular_col = i
                    elif 'senior' in h:
                        senior_col = i

                if regular_col is None and len(headers) >= 2:
                    regular_col = 1

                if senior_col is None and len(headers) >= 3:
                    senior_col = 2

                # Extract rows
                rows = table.find_all('tr')[1:]  # Skip header row

                for row in rows:
                    cells = row.find_all(['td', 'th'])

                    if len(cells) >= 2:
                        tenure = cells[0].text.strip()
                        print(f"Processing tenure: {tenure}")

                        # Skip header or empty rows
                        if len(tenure) < 3 or 'tenure' in tenure.lower() or 'tenors' in tenure.lower():
                            continue

                        regular_rate = None
                        if regular_col is not None and regular_col < len(cells):
                            regular_rate = clean_rate_text(cells[regular_col].text.strip())
                            print(f"Regular rate: {regular_rate}")

                        senior_rate = None
                        if senior_col is not None and senior_col < len(cells):
                            senior_rate = clean_rate_text(cells[senior_col].text.strip())
                            print(f"Senior rate: {senior_rate}")

                        # Extract min and max days from tenure
                        tenure_days = extract_tenure_days(tenure)

                        if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                            fd_data = {
                                'tenure_description': tenure,
                                'min_days': tenure_days['min_days'],
                                'max_days': tenure_days['max_days'],
                                'regular_rate': regular_rate,
                                'senior_rate': senior_rate,
                                'category': 'General'
                            }

                            results.append(fd_data)

        if not results:
            print("Failed to scrape Kotak Mahindra Bank: Could not find FD rate data.")
            return []

        return results

    except Exception as e:
        print(f"Failed to scrape Kotak Mahindra Bank: {str(e)}")
        return []

def scrape_axis():
    """Scrape FD rates from Axis Bank"""

    # Try multiple possible URLs for Axis Bank
    urls = [
        "https://www.axisbank.com/interest-rate-on-deposits",
        "https://www.axisbank.com/retail/deposits/fixed-deposits/fixed-deposit-interest-rate",
        "https://www.axisbank.com/fixed-deposits/fixed-deposit-interest-rate"
    ]

    # Headers to mimic browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    for url in urls:
        try:
            print(f"Trying Axis Bank URL: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Raise HTTPError for bad responses

            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for tables with FD rates
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables on Axis Bank page from {url}")

            results = []

            # Look for tables with relevant classes or ids
            fd_keywords = ['fd', 'fixed', 'deposit', 'interest', 'rate']

            # First pass: look for tables that have clear indicators of being FD rate tables
            potential_tables = []
            for idx, table in enumerate(tables):
                # Check class and id attributes
                table_class = ' '.join(table.get('class', [])).lower()
                table_id = table.get('id', '').lower()

                # Check if the table has a caption that mentions FD rates
                caption = table.find('caption')
                caption_text = caption.text.lower() if caption else ''

                # Check the text content around the table for keywords
                prev_elem = table.find_previous()
                prev_text = prev_elem.text.lower() if prev_elem else ''

                # Score the table based on how likely it is to contain FD rates
                score = 0
                for keyword in fd_keywords:
                    if keyword in table_class or keyword in table_id:
                        score += 3
                    if keyword in caption_text:
                        score += 2
                    if keyword in prev_text:
                        score += 1

                # Additional check for Axis Bank - look for tables with specific headers
                headers_text = ''
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
                    headers_text = ' '.join(headers)
                    if any(term in headers_text for term in ['tenure', 'period', 'duration', 'term']):
                        score += 3
                    if any(term in headers_text for term in ['rate', 'interest', '%']):
                        score += 3

                potential_tables.append((idx, table, score))

            # Sort tables by score, highest first
            potential_tables.sort(key=lambda x: x[2], reverse=True)

            # Process tables in order of likely relevance
            for idx, table, score in potential_tables:
                if score < 1:  # Skip tables that don't seem relevant
                    continue

                print(f"Analyzing table {idx+1} (relevance score: {score})")

                # Extract headers
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
                    print(f"Table {idx+1} headers: {headers}")

                # Look for rows that might contain FD rate data
                rows = table.find_all('tr')[1:]  # Skip header row

                valid_data_found = False
                for row in rows:
                    cells = row.find_all(['td', 'th'])

                    if len(cells) < 2:  # Need at least tenure and rate
                        continue

                    # Extract potential tenure from first column
                    tenure = cells[0].text.strip()

                    # Skip rows that don't look like data rows
                    if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                        continue

                    print(f"Processing row with tenure: {tenure}")

                    # Try to extract rates from other columns
                    # For Axis, sometimes regular rate is 2nd col, sometimes it's in other columns
                    regular_rate = None
                    senior_rate = None

                    # Check all columns for potential rates
                    for i, cell in enumerate(cells[1:], 1):  # Start from index 1
                        rate_text = cell.text.strip()
                        rate_value = clean_rate_text(rate_text)

                        if rate_value is not None:
                            # If we haven't found a regular rate yet, this is it
                            if regular_rate is None:
                                regular_rate = rate_value
                                print(f"Regular rate found in column {i+1}: {regular_rate}")
                            # If we already have a regular rate and this is higher, it might be senior rate
                            elif rate_value > regular_rate and senior_rate is None:
                                senior_rate = rate_value
                                print(f"Senior rate found in column {i+1}: {senior_rate}")

                    # If we couldn't find rates, skip this row
                    if regular_rate is None:
                        continue

                    # If we get here, we found some rate data
                    valid_data_found = True

                    # Extract min and max days from tenure
                    tenure_days = extract_tenure_days(tenure)

                    if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                        fd_data = {
                            'tenure_description': tenure,
                            'min_days': tenure_days['min_days'],
                            'max_days': tenure_days['max_days'],
                            'regular_rate': regular_rate,
                            'senior_rate': senior_rate,
                            'category': 'General'
                        }
                        results.append(fd_data)

                # If we found valid data in this table, we might be done
                if valid_data_found:
                    print(f"Found {len(results)} valid FD rates in table {idx+1}")
                    if len(results) >= 3:  # If we found at least 3 rates, consider this a success
                        return results

            # If we found some results but not enough, return what we have
            if results and len(results) >= 2:
                print(f"Collected {len(results)} Axis Bank FD rates from tables")
                return results

        except requests.RequestException as e:
            print(f"Error with Axis Bank URL {url}: {str(e)}")
        except Exception as e:
            print(f"Error processing Axis Bank URL {url}: {str(e)}")

    # If all URLs failed or no data found, return empty list
    print("Failed to scrape Axis Bank: All URLs failed or no data found.")
    return []

def scrape_bob():
    """Scrape FD rates from Bank of Baroda"""
    urls = [
        "https://www.bankofbaroda.in/interest-rates/deposits-interest-rates",
        "https://www.bankofbaroda.in/personal-banking/deposits/fixed-deposits",
        # New URLs
        "https://www.bankofbaroda.in/interest-rates",
        "https://www.bankofbaroda.in/personal-banking/deposits/term-deposits",
        "https://www.bankofbaroda.in/interest-rates/deposit-rates",
        "https://www.bankofbaroda.in/personal-banking/deposits/domestic-term-deposits"
    ]
   
    print("Starting Bank of Baroda scraping...")
   
    for url in urls:
        try:
            print(f"Trying Bank of Baroda URL: {url}")
           
            # Try with Selenium first
            html_content = scrape_with_selenium(url, wait_for_element='table', wait_timeout=30)
            if not html_content:
                # If Selenium fails, try with direct request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Cache-Control': 'no-cache'
                }
                response = requests.get(url, headers=headers, timeout=30)
                html_content = response.text
           
            soup = BeautifulSoup(html_content, 'html.parser')
           
            # Look for tables with specific Bank of Baroda patterns
            tables = []
           
            # Direct table search
            tables.extend(soup.find_all('table'))
           
            # Look for tables in specific div classes
            for div in soup.find_all(['div', 'section'],
                                   class_=['rates-table', 'interest-rates', 'fd-rates', 'depositRates',
                                         'rateTable', 'rate-table', 'fixed-deposit-rates', 'table-responsive']):
                tables.extend(div.find_all('table'))
           
            # Look near relevant headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                                       string=re.compile(r'fixed deposit|fd|interest rate|deposit rate', re.I)):
                next_table = heading.find_next('table')
                if next_table:
                    tables.append(next_table)

            print(f"Found {len(tables)} potential tables")
           
            results = []
           
            for table in tables:
                # Check if table contains rate information
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
               
                if any(term in ' '.join(headers) for term in
                      ['tenure', 'period', 'term', 'duration', 'days', 'months', 'years']):
                   
                    rows = table.find_all('tr')[1:]  # Skip header
                   
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                       
                        if len(cells) >= 2:
                            tenure = cells[0].text.strip()
                           
                            # Skip non-data rows
                            if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                                continue
                           
                            # Try to find rate columns
                            regular_rate = None
                            senior_rate = None
                           
                            # Look for rate columns based on headers
                            rate_col = None
                            senior_col = None
                           
                            for i, header in enumerate(headers):
                                if any(term in header for term in ['regular', 'general', 'public', 'standard']):
                                    rate_col = i
                                elif 'senior' in header:
                                    senior_col = i
                           
                            # If couldn't find specific columns, use default positions
                            if rate_col is None and len(cells) >= 2:
                                rate_col = 1
                            if senior_col is None and len(cells) >= 3:
                                senior_col = 2
                           
                            # Extract rates
                            if rate_col is not None and rate_col < len(cells):
                                regular_rate = clean_rate_text(cells[rate_col].text.strip())
                           
                            if senior_col is not None and senior_col < len(cells):
                                senior_rate = clean_rate_text(cells[senior_col].text.strip())
                           
                            # Extract tenure days
                            tenure_days = extract_tenure_days(tenure)
                           
                            if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                                fd_data = {
                                    'tenure_description': tenure,
                                    'min_days': tenure_days['min_days'],
                                    'max_days': tenure_days['max_days'],
                                    'regular_rate': regular_rate,
                                    'senior_rate': senior_rate,
                                    'category': 'General'
                                }
                                results.append(fd_data)
           
            if results:
                print(f"Successfully extracted {len(results)} FD rates from Bank of Baroda")
                return results
               
        except Exception as e:
            print(f"Error with Bank of Baroda URL {url}: {str(e)}")
            continue
   
    print("Failed to scrape Bank of Baroda from all URLs")
    return []

def scrape_federal():
    """Scrape FD rates from Federal Bank"""
    urls = [
        "https://www.federalbank.co.in/deposit-rates",
        "https://www.federalbank.co.in/fixed-deposits",
        # Additional URLs
        "https://www.federalbank.co.in/interest-rates",
        "https://www.federalbank.co.in/term-deposit-rates",
        "https://www.federalbank.co.in/personal-banking/deposits/fixed-deposit-rates",
        "https://www.federalbank.co.in/personal-banking/deposits/term-deposit-rates"
    ]
   
    print("Starting Federal Bank scraping...")
   
    for url in urls:
        try:
            print(f"Trying Federal Bank URL: {url}")
           
            # Use Selenium for dynamic content
            html_content = scrape_with_selenium(url, wait_for_element='table', wait_timeout=20)
            if not html_content:
                continue
               
            soup = BeautifulSoup(html_content, 'html.parser')
           
            # Look for tables with specific Federal Bank patterns
            tables = []
           
            # Direct table search
            tables.extend(soup.find_all('table'))
           
            # Look for tables in specific Federal Bank div classes
            for div in soup.find_all(['div', 'section'],
                                   class_=['rates-table', 'interest-rates', 'fd-rates', 'depositRates',
                                         'rateTable', 'rate-table', 'fixed-deposit-rates']):
                tables.extend(div.find_all('table'))
           
            # Look near relevant headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                                       string=re.compile(r'fixed deposit|fd|interest rate|deposit rate', re.I)):
                next_table = heading.find_next('table')
                if next_table:
                    tables.append(next_table)

            print(f"Found {len(tables)} potential tables")
           
            results = []
           
            for table in tables:
                # Check if table contains rate information
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
               
                if any(term in ' '.join(headers) for term in
                      ['tenure', 'period', 'term', 'duration', 'days', 'months', 'years']):
                   
                    rows = table.find_all('tr')[1:]  # Skip header
                   
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                       
                        if len(cells) >= 2:
                            tenure = cells[0].text.strip()
                           
                            # Skip non-data rows
                            if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                                continue
                           
                            # Try to find rate columns
                            regular_rate = None
                            senior_rate = None
                           
                            # Look for rate columns based on headers
                            rate_col = None
                            senior_col = None
                           
                            for i, header in enumerate(headers):
                                if any(term in header for term in ['regular', 'general', 'public']):
                                    rate_col = i
                                elif 'senior' in header:
                                    senior_col = i
                           
                            # If couldn't find specific columns, use default positions
                            if rate_col is None and len(cells) >= 2:
                                rate_col = 1
                            if senior_col is None and len(cells) >= 3:
                                senior_col = 2
                           
                            # Extract rates
                            if rate_col is not None and rate_col < len(cells):
                                regular_rate = clean_rate_text(cells[rate_col].text.strip())
                           
                            if senior_col is not None and senior_col < len(cells):
                                senior_rate = clean_rate_text(cells[senior_col].text.strip())
                           
                            # Extract tenure days
                            tenure_days = extract_tenure_days(tenure)
                           
                            if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                                fd_data = {
                                    'tenure_description': tenure,
                                    'min_days': tenure_days['min_days'],
                                    'max_days': tenure_days['max_days'],
                                    'regular_rate': regular_rate,
                                    'senior_rate': senior_rate,
                                    'category': 'General'
                                }
                                results.append(fd_data)
           
            if results:
                print(f"Successfully extracted {len(results)} FD rates from Federal Bank")
                return results
               
        except Exception as e:
            print(f"Error with Federal Bank URL {url}: {str(e)}")
            continue
   
    print("Failed to scrape Federal Bank from all URLs")
    return []

def scrape_bank_of_india():
    """Scrape FD rates from Bank of India"""
    urls = [
        "https://www.bankofindia.co.in/interest-rates",
        "https://www.bankofindia.co.in/fixed-deposits",
        # New URLs
        "https://www.bankofindia.co.in/interest-rate/deposit-rates",
        "https://www.bankofindia.co.in/term-deposit-rates",
        "https://www.bankofindia.co.in/domestic-term-deposits",
        "https://www.bankofindia.co.in/retail-term-deposits"
    ]
   
    print("Starting Bank of India scraping...")
   
    for url in urls:
        try:
            print(f"Trying Bank of India URL: {url}")
           
            # Try with Selenium first
            html_content = scrape_with_selenium(url, wait_for_element='table', wait_timeout=30)
            if not html_content:
                # If Selenium fails, try with direct request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Cache-Control': 'no-cache'
                }
                response = requests.get(url, headers=headers, timeout=30)
                html_content = response.text
           
            soup = BeautifulSoup(html_content, 'html.parser')
           
            # Look for tables with specific Bank of India patterns
            tables = []
           
            # Direct table search
            tables.extend(soup.find_all('table'))
           
            # Look for tables in specific div classes
            for div in soup.find_all(['div', 'section'],
                                   class_=['rates-table', 'interest-rates', 'fd-rates', 'depositRates',
                                         'rateTable', 'rate-table', 'fixed-deposit-rates', 'table-responsive']):
                tables.extend(div.find_all('table'))
           
            # Look near relevant headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                                       string=re.compile(r'fixed deposit|fd|interest rate|deposit rate', re.I)):
                next_table = heading.find_next('table')
                if next_table:
                    tables.append(next_table)

            print(f"Found {len(tables)} potential tables")
           
            results = []
           
            for table in tables:
                # Check if table contains rate information
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
               
                if any(term in ' '.join(headers) for term in
                      ['tenure', 'period', 'term', 'duration', 'days', 'months', 'years']):
                   
                    rows = table.find_all('tr')[1:]  # Skip header
                   
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                       
                        if len(cells) >= 2:
                            tenure = cells[0].text.strip()
                           
                            # Skip non-data rows
                            if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                                continue
                           
                            # Try to find rate columns
                            regular_rate = None
                            senior_rate = None
                           
                            # Look for rate columns based on headers
                            rate_col = None
                            senior_col = None
                           
                            for i, header in enumerate(headers):
                                if any(term in header for term in ['regular', 'general', 'public', 'standard']):
                                    rate_col = i
                                elif 'senior' in header:
                                    senior_col = i
                           
                            # If couldn't find specific columns, use default positions
                            if rate_col is None and len(cells) >= 2:
                                rate_col = 1
                            if senior_col is None and len(cells) >= 3:
                                senior_col = 2
                           
                            # Extract rates
                            if rate_col is not None and rate_col < len(cells):
                                regular_rate = clean_rate_text(cells[rate_col].text.strip())
                           
                            if senior_col is not None and senior_col < len(cells):
                                senior_rate = clean_rate_text(cells[senior_col].text.strip())
                           
                            # Extract tenure days
                            tenure_days = extract_tenure_days(tenure)
                           
                            if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                                fd_data = {
                                    'tenure_description': tenure,
                                    'min_days': tenure_days['min_days'],
                                    'max_days': tenure_days['max_days'],
                                    'regular_rate': regular_rate,
                                    'senior_rate': senior_rate,
                                    'category': 'General'
                                }
                                results.append(fd_data)
           
            if results:
                print(f"Successfully extracted {len(results)} FD rates from Bank of India")
                return results
               
        except Exception as e:
            print(f"Error with Bank of India URL {url}: {str(e)}")
            continue
   
    print("Failed to scrape Bank of India from all URLs")
    return []

def scrape_bank_of_maharashtra():
    """Scrape FD rates from Bank of Maharashtra"""
    urls = [
        "https://www.bankofmaharashtra.in/interest-rates",
        "https://www.bankofmaharashtra.in/fixed-deposits"
    ]
   
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
   
    results = []
   
    for url in urls:
        try:
            logger.info(f"Attempting to scrape Bank of Maharashtra URL: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
           
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
           
            for table in tables:
                if process_bom_table(table, results):
                    return results
                   
        except Exception as e:
            logger.error(f"Error scraping Bank of Maharashtra: {str(e)}")
           
    return results

def scrape_canara_bank():
    """Scrape FD rates from Canara Bank"""
    urls = [
        "https://www.canarabank.com/interest-rates/deposits.aspx",
        "https://www.canarabank.com/fixed-deposit-interest-rates.aspx",
        # New URLs
        "https://www.canarabank.com/User_page.aspx?othlink=9",
        "https://www.canarabank.com/interest-rate/deposit-rates",
        "https://www.canarabank.com/english/interest-rates",
        "https://www.canarabank.com/term-deposits"
    ]
   
    print("Starting Canara Bank scraping...")
   
    for url in urls:
        try:
            print(f"Trying Canara Bank URL: {url}")
           
            # Try with Selenium first
            html_content = scrape_with_selenium(url, wait_for_element='table', wait_timeout=30)
            if not html_content:
                # If Selenium fails, try with direct request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
                response = requests.get(url, headers=headers, timeout=30)
                html_content = response.text
           
            soup = BeautifulSoup(html_content, 'html.parser')
           
            # Look for tables with specific Canara Bank patterns
            tables = []
           
            # Direct table search
            tables.extend(soup.find_all('table'))
           
            # Look for tables in specific div classes
            for div in soup.find_all(['div', 'section'],
                                   class_=['rates-table', 'interest-rates', 'fd-rates', 'depositRates',
                                         'rateTable', 'rate-table', 'fixed-deposit-rates', 'table-responsive']):
                tables.extend(div.find_all('table'))
           
            # Look near relevant headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                                       string=re.compile(r'fixed deposit|fd|interest rate|deposit rate', re.I)):
                next_table = heading.find_next('table')
                if next_table:
                    tables.append(next_table)

            print(f"Found {len(tables)} potential tables")
           
            results = []
           
            for table in tables:
                # Check if table contains rate information
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
               
                if any(term in ' '.join(headers) for term in
                      ['tenure', 'period', 'term', 'duration', 'days', 'months', 'years']):
                   
                    rows = table.find_all('tr')[1:]  # Skip header
                   
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                       
                        if len(cells) >= 2:
                            tenure = cells[0].text.strip()
                           
                            # Skip non-data rows
                            if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                                continue
                           
                            # Try to find rate columns
                            regular_rate = None
                            senior_rate = None
                           
                            # Look for rate columns based on headers
                            rate_col = None
                            senior_col = None
                           
                            for i, header in enumerate(headers):
                                if any(term in header for term in ['regular', 'general', 'public', 'standard']):
                                    rate_col = i
                                elif 'senior' in header:
                                    senior_col = i
                           
                            # If couldn't find specific columns, use default positions
                            if rate_col is None and len(cells) >= 2:
                                rate_col = 1
                            if senior_col is None and len(cells) >= 3:
                                senior_col = 2
                           
                            # Extract rates
                            if rate_col is not None and rate_col < len(cells):
                                regular_rate = clean_rate_text(cells[rate_col].text.strip())
                           
                            if senior_col is not None and senior_col < len(cells):
                                senior_rate = clean_rate_text(cells[senior_col].text.strip())
                           
                            # Extract tenure days
                            tenure_days = extract_tenure_days(tenure)
                           
                            if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                                fd_data = {
                                    'tenure_description': tenure,
                                    'min_days': tenure_days['min_days'],
                                    'max_days': tenure_days['max_days'],
                                    'regular_rate': regular_rate,
                                    'senior_rate': senior_rate,
                                    'category': 'General'
                                }
                                results.append(fd_data)
           
            if results:
                print(f"Successfully extracted {len(results)} FD rates from Canara Bank")
                return results
               
        except Exception as e:
            print(f"Error with Canara Bank URL {url}: {str(e)}")
            continue
   
    print("Failed to scrape Canara Bank from all URLs")
    return []

def scrape_central_bank():
    """Scrape FD rates from Central Bank of India"""
    urls = [
        "https://www.centralbankofindia.co.in/en/interest-rates",
        "https://www.centralbankofindia.co.in/en/term-deposit-interest-rate",
        # Additional URLs
        "https://www.centralbankofindia.co.in/en/fixed-deposit-interest-rates",
        "https://www.centralbankofindia.co.in/en/deposit-rates",
        "https://www.centralbankofindia.co.in/sites/default/files/interest-rate",
        "https://www.centralbankofindia.co.in/en/domestic-term-deposits"
    ]
   
    print("Starting Central Bank of India scraping...")
   
    for url in urls:
        try:
            print(f"Trying Central Bank URL: {url}")
           
            # Use Selenium for dynamic content
            html_content = scrape_with_selenium(url, wait_for_element='table', wait_timeout=20)
            if not html_content:
                continue
               
            soup = BeautifulSoup(html_content, 'html.parser')
           
            # Look for tables with specific Central Bank patterns
            tables = []
           
            # Direct table search
            tables.extend(soup.find_all('table'))
           
            # Look for tables in specific Central Bank div classes
            for div in soup.find_all(['div', 'section'],
                                   class_=['rates-table', 'interest-rates', 'fd-rates', 'depositRates',
                                         'rateTable', 'rate-table', 'fixed-deposit-rates', 'deposit-table']):
                tables.extend(div.find_all('table'))
           
            # Look near relevant headings
            for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
                                       string=re.compile(r'fixed deposit|fd|interest rate|deposit rate', re.I)):
                next_table = heading.find_next('table')
                if next_table:
                    tables.append(next_table)

            print(f"Found {len(tables)} potential tables")
           
            results = []
           
            for table in tables:
                # Check if table contains rate information
                headers = []
                header_row = table.find('tr')
                if header_row:
                    headers = [th.text.strip().lower() for th in header_row.find_all(['th', 'td'])]
               
                if any(term in ' '.join(headers) for term in
                      ['tenure', 'period', 'term', 'duration', 'days', 'months', 'years']):
                   
                    rows = table.find_all('tr')[1:]  # Skip header
                   
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                       
                        if len(cells) >= 2:
                            tenure = cells[0].text.strip()
                           
                            # Skip non-data rows
                            if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                                continue
                           
                            # Try to find rate columns
                            regular_rate = None
                            senior_rate = None
                           
                            # Look for rate columns based on headers
                            rate_col = None
                            senior_col = None
                           
                            for i, header in enumerate(headers):
                                if any(term in header for term in ['regular', 'general', 'public']):
                                    rate_col = i
                                elif 'senior' in header:
                                    senior_col = i
                           
                            # If couldn't find specific columns, use default positions
                            if rate_col is None and len(cells) >= 2:
                                rate_col = 1
                            if senior_col is None and len(cells) >= 3:
                                senior_col = 2
                           
                            # Extract rates
                            if rate_col is not None and rate_col < len(cells):
                                regular_rate = clean_rate_text(cells[rate_col].text.strip())
                           
                            if senior_col is not None and senior_col < len(cells):
                                senior_rate = clean_rate_text(cells[senior_col].text.strip())
                           
                            # Extract tenure days
                            tenure_days = extract_tenure_days(tenure)
                           
                            if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                                fd_data = {
                                    'tenure_description': tenure,
                                    'min_days': tenure_days['min_days'],
                                    'max_days': tenure_days['max_days'],
                                    'regular_rate': regular_rate,
                                    'senior_rate': senior_rate,
                                    'category': 'General'
                                }
                                results.append(fd_data)
           
            if results:
                print(f"Successfully extracted {len(results)} FD rates from Central Bank")
                return results
               
        except Exception as e:
            print(f"Error with Central Bank URL {url}: {str(e)}")
            continue
   
    print("Failed to scrape Central Bank from all URLs")
    return []

def scrape_indian_bank():
    """Scrape FD rates from Indian Bank"""
    urls = [
        "https://www.indianbank.in/interest-rates/",
        "https://www.indianbank.in/departments/deposit-rates/"
    ]
   
    results = []
   
    for url in urls:
        try:
            logger.info(f"Attempting to scrape Indian Bank URL: {url}")
            html_content = scrape_with_selenium(url)
            soup = BeautifulSoup(html_content, 'html.parser')
           
            tables = find_relevant_tables(soup, ['deposit-rates', 'interest-table'])
           
            for table in tables:
                if process_indian_bank_table(table, results):
                    return results
                   
        except Exception as e:
            logger.error(f"Error scraping Indian Bank: {str(e)}")
           
    return results








# Table processing functions
def process_boi_table(table, results):
    """Process Bank of India table"""
    return process_generic_table(table, results)

def process_bom_table(table, results):
    """Process Bank of Maharashtra table"""
    return process_generic_table(table, results)

def process_canara_tables(soup):
    """Process Canara Bank tables"""
    results = []
    tables = soup.find_all('table')
   
    for table in tables:
        process_generic_table(table, results)
   
    return results

def process_indian_bank_table(table, results):
    """Process Indian Bank table"""
    return process_generic_table(table, results)

def process_iob_table(table, results):
    """Process Indian Overseas Bank table"""
    return process_generic_table(table, results)

def process_psb_table(table, results):
    """Process Punjab & Sind Bank table"""
    return process_generic_table(table, results)

def process_uco_table(table, results):
    """Process UCO Bank table"""
    return process_generic_table(table, results)

def process_union_table(table, results):
    """Process Union Bank table"""
    return process_generic_table(table, results)

def process_generic_table(table, results):
    """Generic table processing function"""
    headers = [th.text.strip().lower() for th in table.find_all(['th', 'td'])]
   
    if any(term in ' '.join(headers) for term in ['tenure', 'period', 'rate']):
        rows = table.find_all('tr')[1:]  # Skip header
       
        data_found = False
        for row in rows:
            cells = row.find_all(['td', 'th'])
           
            if len(cells) >= 2:
                tenure = cells[0].text.strip()
               
                if len(tenure) < 3 or not any(c.isdigit() for c in tenure):
                    continue
               
                regular_rate = clean_rate_text(cells[1].text.strip())
                senior_rate = clean_rate_text(cells[2].text.strip()) if len(cells) > 2 else None
               
                tenure_days = extract_tenure_days(tenure)
               
                if tenure_days['min_days'] is not None and tenure_days['max_days'] is not None:
                    results.append({
                        'tenure_description': tenure,
                        'min_days': tenure_days['min_days'],
                        'max_days': tenure_days['max_days'],
                        'regular_rate': regular_rate,
                        'senior_rate': senior_rate,
                        'category': 'General'
                    })
                    data_found = True
       
        return data_found
    return False

def run_all_scrapers():
    """Run all bank scrapers and combine the results"""
    print("Starting FD rates scraping process...")
   
    # Create a timestamp for the saved files
    today = datetime.today().strftime('%Y-%m-%d')
   
    # List of all scraper functions and their corresponding bank names
    scrapers = [
        (scrape_icici, 'ICICI Bank'),
        (scrape_sbi, 'SBI'),
        (scrape_kotak, 'Kotak Mahindra Bank'),
        (scrape_axis, 'Axis Bank'),
        (scrape_bank_of_maharashtra, 'Bank of Maharashtra'),
        (scrape_canara_bank, 'Canara Bank'),
        (scrape_central_bank, 'Central Bank of India'),
        (scrape_indian_bank, 'Indian Bank')
    ]
   
    results = []
    success_status = {}
   
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_bank = {executor.submit(scraper): bank for scraper, bank in scrapers}
       
        for future in as_completed(future_to_bank):
            bank = future_to_bank[future]
            try:
                bank_data = future.result()
                if bank_data and len(bank_data) > 0:
                    for record in bank_data:
                        record['bank'] = bank
                        record['scraped_date'] = today
                   
                    results.extend(bank_data)
                    print(f"✅ Successfully scraped {bank} - Found {len(bank_data)} FD rates")
                    success_status[bank] = "success"
                else:
                    print(f"❌ Failed to scrape {bank}: No data returned")
                    success_status[bank] = "failed"
            except Exception as e:
                print(f"❌ Failed to scrape {bank}: {str(e)}")
                success_status[bank] = "failed"
   
    # Save results to CSV
    if results:
        df = pd.DataFrame(results)
       
        # Save raw results
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        csv_path = os.path.join(data_dir, f"fd_rates_{today}.csv")
        df.to_csv(csv_path, index=False)
       
        # Save clean version
        clean_df = df.dropna(subset=['min_days', 'max_days', 'regular_rate'])
        clean_csv_path = os.path.join(data_dir, f"fd_rates_clean_{today}.csv")
        clean_df.to_csv(clean_csv_path, index=False)
        
        # Save directly to SQLite DB
        try:
            # Import sqlite3 here to avoid circular imports
            import sqlite3
            from pathlib import Path
            
            # Define the DB path
            db_path = Path(__file__).parent / "fd_rates.db"
            
            # Connect to the database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Make sure table exists
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS fd_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank TEXT NOT NULL,
                tenure_description TEXT NOT NULL,
                min_days INTEGER NOT NULL,
                max_days INTEGER NOT NULL,
                regular_rate REAL NOT NULL,
                senior_rate REAL,
                category TEXT DEFAULT 'General',
                scraped_date TEXT,
                UNIQUE(bank, tenure_description)
            )
            ''')
            
            # Insert data into the database with conflict resolution
            for _, row in clean_df.iterrows():
                try:
                    cursor.execute('''
                    INSERT OR REPLACE INTO fd_rates 
                    (bank, tenure_description, min_days, max_days, regular_rate, senior_rate, category, scraped_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['bank'], 
                        row['tenure_description'], 
                        row['min_days'], 
                        row['max_days'], 
                        row['regular_rate'],
                        row.get('senior_rate'),
                        row.get('category', 'General'),
                        row.get('scraped_date', today)
                    ))
                except Exception as e:
                    print(f"Error inserting row into database: {str(e)}")
            
            # Commit changes and close connection
            conn.commit()
            conn.close()
            print(f"Successfully saved {len(clean_df)} records to database")
        except Exception as e:
            print(f"Failed to save to database: {str(e)}")
       
        # Print summary
        print("\nScraping Summary:")
        successful_banks = [bank for bank, status in success_status.items() if status == "success"]
        failed_banks = [bank for bank, status in success_status.items() if status == "failed"]
       
        if successful_banks:
            print(f"✅ Successfully scraped: {', '.join(successful_banks)}")
        if failed_banks:
            print(f"❌ Failed to scrape: {', '.join(failed_banks)}")
       
        return df
    else:
        print("No data was scraped from any bank.")
        return pd.DataFrame()

def plot_best_rates(df, n=8, for_seniors=False):
    """Plot the top N best FD rates across banks"""

    # Create a copy to avoid modifying the original
    plot_df = df.copy()

    # Use senior rates if requested
    rate_column = 'senior_rate' if for_seniors else 'regular_rate'

    # Filter out rows with missing rates
    plot_df = plot_df[plot_df[rate_column].notna()]

    # Group by tenure ranges
    tenure_groups = [
        (0, 90, 'Up to 3 months'),
        (91, 180, '3-6 months'),
        (181, 365, '6-12 months'),
        (366, 730, '1-2 years'),
        (731, 1095, '2-3 years'),
        (1096, 9999, '3+ years')
    ]

    plt.figure(figsize=(12, 8))

    # For each tenure group, find the best rates
    for i, (min_days, max_days, label) in enumerate(tenure_groups):
        # Filter by tenure
        filtered = plot_df[(plot_df['min_days'] >= min_days) &
                          (plot_df['max_days'] <= max_days)]

        if filtered.empty:
            continue

        # Sort by rate and get top N
        top_n = filtered.sort_values(by=rate_column, ascending=False).head(n)

        # Plot as a horizontal bar chart
        plt.subplot(len(tenure_groups), 1, i+1)
        sns.barplot(x=rate_column, y='bank', data=top_n, hue='bank', legend=False)
        plt.title(f'Best FD Rates for {label}')
        plt.xlabel('Interest Rate (%)')
        plt.ylabel('Bank')

    plt.tight_layout()

    # Save the plot
    timestamp = datetime.now().strftime("%Y-%m-%d")
    plt.savefig(f'data/best_rates_{timestamp}.png')
    plt.close()

def plot_rate_comparison(df, tenure_days):
    """Plot rate comparison for a specific tenure across all banks"""

    # Filter data for the specified tenure
    tenure_data = df[
        (df['min_days'] <= tenure_days) &
        (df['max_days'] >= tenure_days)
    ]

    if tenure_data.empty:
        print(f"No data found for {tenure_days} days tenure")
        return

    # Create comparison plot
    plt.figure(figsize=(12, 6))

    # Plot regular rates
    plt.subplot(1, 2, 1)
    sns.barplot(x='regular_rate', y='bank', data=tenure_data, hue='bank', legend=False)
    plt.title('Regular FD Rates')
    plt.xlabel('Interest Rate (%)')
    plt.ylabel('Bank')

    # Plot senior citizen rates
    plt.subplot(1, 2, 2)
    sns.barplot(x='senior_rate', y='bank', data=tenure_data, hue='bank', legend=False)
    plt.title('Senior Citizen FD Rates')
    plt.xlabel('Interest Rate (%)')
    plt.ylabel('Bank')

    plt.tight_layout()

    # Save the plot
    timestamp = datetime.now().strftime("%Y-%m-%d")
    plt.savefig(f'data/rate_comparison_{tenure_days}days_{timestamp}.png')
    plt.close()

def generate_summary_report(df):
    """Generate a summary report of the best rates"""

    # Create a copy to avoid modifying the original
    report_df = df.copy()

    # Filter out rows with missing rates
    report_df = report_df[report_df['regular_rate'].notna()]

    # Group by tenure ranges
    tenure_groups = [
        (0, 90, 'Up to 3 months'),
        (91, 180, '3-6 months'),
        (181, 365, '6-12 months'),
        (366, 730, '1-2 years'),
        (731, 1095, '2-3 years'),
        (1096, 9999, '3+ years')
    ]

    # Create summary DataFrame
    summary_data = []

    for min_days, max_days, label in tenure_groups:
        # Filter by tenure
        filtered = report_df[
            (report_df['min_days'] >= min_days) &
            (report_df['max_days'] <= max_days)
        ]

        if not filtered.empty:
            # Get best regular rate
            best_regular_idx = filtered['regular_rate'].idxmax()
            best_regular = filtered.loc[best_regular_idx]

            # Get best senior rate if available
            best_senior_str = 'N/A'
            if 'senior_rate' in filtered.columns and filtered['senior_rate'].notna().any():
                best_senior_idx = filtered['senior_rate'].dropna().idxmax()
                if pd.notna(best_senior_idx):
                    best_senior = filtered.loc[best_senior_idx]
                    best_senior_str = f"{best_senior['senior_rate']}% ({best_senior['bank']})"

            summary_data.append({
                'Tenure': label,
                'Best Regular Rate': f"{best_regular['regular_rate']}% ({best_regular['bank']})",
                'Best Senior Rate': best_senior_str
            })

    # Create summary DataFrame
    summary_df = pd.DataFrame(summary_data)

    # Save to CSV
    timestamp = datetime.now().strftime("%Y-%m-%d")
    summary_df.to_csv(f'data/summary_report_{timestamp}.csv', index=False)

    return summary_df

if __name__ == "__main__":
    # Run the scraper
    df = run_all_scrapers()

    if df is not None:
        # Display detailed data by bank
        print("\nDetailed FD Rates by Bank:")
        for bank in df['bank'].unique():
            bank_data = df[df['bank'] == bank]
            print(f"\n{bank} FD Rates:")
            print(bank_data[['tenure_description', 'min_days', 'max_days', 'regular_rate', 'senior_rate']].to_string(index=False))

        # Generate visualizations
        plot_best_rates(df, n=8, for_seniors=True)  # For senior citizen rates
        plot_best_rates(df, n=8, for_seniors=False)  # For regular rates

        # Generate comparison for specific tenure (e.g., 1 year = 365 days)
        plot_rate_comparison(df, 365)

        # Generate summary report
        summary_df = generate_summary_report(df)
        print("\nSummary Report:")
        print(summary_df)

        print("\nFull Data Head:")
        print(df.head())
