import requests
import parser
import time
import pandas as pd
import argparse

SP500_HOLDINGS_URL = "https://stockanalysis.com/etf/spus/holdings/"
API_KEY = ""


def compute_allocation(df, cap, whole_stocks):
    if whole_stocks:
        allocated = 0
        for index, row in df.iterrows():
            weight = 0.01 * row["Weight"]
            price = float(row["price"])
            if price == 0:
                continue
            current_quota = cap * weight
            current_stocks = int(current_quota / price)
            allocated += (current_stocks * price)
            print(row["Symbol"], current_stocks)
        print("capital left over = ", cap - allocated)
    else:
        allocated = 0
        for index, row in df.iterrows():
            weight = 0.01 * row["Weight"]
            price = float(row["price"])
            if price == 0:
                continue
            current_quota = cap * weight
            print(row["Symbol"], current_quota)
            allocated += current_quota
        print("capital left over = ", cap - allocated)


def mark_boycott(symbol, boycott_list):
    if symbol in boycott_list:
        return True
    else:
        return False


def get_stock_prices(symbol):
    time.sleep(2)
    base_url = "https://www.alphavantage.co/query"
    function = "TIME_SERIES_INTRADAY"
    interval = "1min"  # You can change the interval as needed (1min, 5min, 15min, 30min, 60min)
    outputsize = "compact"

    params = {
        "function": function,
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    if "Time Series (1min)" in data:
        # Extract the latest stock price
        latest_timestamp = max(data["Time Series (1min)"].keys())
        latest_price = data["Time Series (1min)"][latest_timestamp]["4. close"]
        return float(latest_price)
    else:
        print(f"Error retrieving data for {symbol}")
        return None


def parse_arguments():
    parser = argparse.ArgumentParser(description='Process command line arguments.')

    parser.add_argument('--capital', type=float, help='Capital (float)', default=1000)
    parser.add_argument('--api_key_path', type=str, help='Path to api_key.txt file', default="api_key.txt")
    parser.add_argument('--non_fractional_stocks', action='store_true', default=False, help='Specify if the input is fake')

    args = parser.parse_args()
    return args


def main():
    args = parse_arguments()

    with open(args.api_key_path, 'r') as f:
        API_KEY = f.read().strip()

    holdings = parser.parse_webpage(parser.get_page_content(SP500_HOLDINGS_URL))
    boycott = pd.read_csv("blacklist.csv")
    holdings['to_boycott'] = holdings['Symbol'].apply(lambda x: mark_boycott(x, list(boycott['Symbol'])))
    holdings.drop(holdings[holdings['to_boycott'] == True].index, inplace=True)
    holdings['price'] = holdings['Symbol'].apply(get_stock_prices)
    # saving the prices as the free API has a quota of 25 request/day
    holdings.to_csv("holdings.csv")
    holdings = pd.read_csv("holdings.csv")
    holdings['price'] = holdings['price'].fillna(0)
    # removing stocks failed to get prices
    holdings = holdings[holdings["price"] != 0]
    # re weighting
    holdings['Weight'] = holdings['Weight'] / holdings['Weight'].sum() * 100
    # fractions = True, assumes you can buy a fraction of a stock (this is allowed in most cases)
    compute_allocation(holdings, args.capital, whole_stocks=args.non_fractional_stocks)


if __name__ == "__main__":
    main()
