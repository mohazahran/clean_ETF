from bs4 import BeautifulSoup
import re
import json
import requests
import pandas as pd


def get_page_content(url):
    try:
        # Send a GET request to the URL
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Return the content of the page
            return response.content
        else:
            print(f"Failed to retrieve content. Status code: {response.status_code}")
            return None

    except requests.RequestException as e:
        print(f"Error during request: {e}")
        return None


def extract_patterns(input_string):
    pattern = r'\{no:(\d+),s:"(\$[A-Z]+)",n:"([^"]+)",as:"([^"]+)",sh:"([\d,]+)"\}'
    matches = re.finditer(pattern, input_string)

    extracted_data = []
    for match in matches:
        no = match.group(1)
        symbol = match.group(2)
        name = match.group(3)
        percent_weight = match.group(4)
        shares = match.group(5).replace(',', '')

        entry = {
            'No.': no,
            'Symbol': symbol,
            'Name': name,
            '% Weight': percent_weight,
            'Shares': shares
        }

        extracted_data.append(entry)

    return extracted_data


def parse_webpage(html_content):
    # Use BeautifulSoup to parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the script tag containing 'const data'
    script_tags = soup.find_all('script', text=re.compile(r'const data = '))

    if script_tags:
        # Extract the content of the script tag
        script_content = script_tags[0].string

        # Use regular expression to extract the 'const data' part
        const_data_match = re.search(r'const data = (\[.*?\]);', script_content)

        if const_data_match:
            # Extract the JSON string containing 'const data'
            const_data_json = const_data_match.group(1)

            holdings = extract_patterns(const_data_json)
            df = pd.DataFrame(holdings)
            df['Symbol'] = df['Symbol'].str.replace('$', '')
            df.rename(columns={'% Weight': 'Weight'}, inplace=True)
            df['Weight'] = df['Weight'].str.replace('%', '')
            df['Weight'] = df['Weight'].astype(float)
            return df

    return None


if __name__ == '__main__':

    url = "https://stockanalysis.com/etf/spus/holdings/"

    your_html_content = get_page_content(url)

    holdings = parse_webpage(your_html_content)

    if parsed_data:
        # Print the parsed data
        print(json.dumps(parsed_data, indent=2))
    else:
        print("Failed to parse 'const data' from the webpage.")