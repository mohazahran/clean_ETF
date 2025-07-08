import argparse
import os
import time
import pandas as pd
import requests
from math import floor
import os
import time
from requests.exceptions import HTTPError

# Import the parser you just refactored
import parser as holdings_parser  # make sure this points at the file above


def parse_args():
    p = argparse.ArgumentParser(
        description="Allocate capital into SPUS (halal S&P 500) holdings."
    )
    p.add_argument(
        "--capital", type=float, default=100_000,
        help="Total dollars to invest."
    )
    p.add_argument(
        "--api_key_path", type=str, default="api_key_finnhub.txt",
        help="Path to your Alphavantage API key file."
    )
    p.add_argument(
        "--blacklist", type=str, default="blacklist.csv",
        help="CSV of Symbols to exclude (boycott list)."
    )
    p.add_argument(
        "--non_fractional_stocks", action="store_true",
        help="Allocate in whole shares only."
    )
    p.add_argument(
        "--use_yahoo", action="store_true",
        help="Use yfinance (no API key needed) instead of Alphavantage."
    )
    return p.parse_args()


def load_api_key(path: str) -> str:
    if not os.path.exists(path):
        raise FileNotFoundError(f"API key file not found: {path}")
    return open(path).read().strip()


def fetch_prices_alpha(tickers, api_key) -> dict:
    """
    Uses Alphavantage BATCH_STOCK_QUOTES to fetch up to 100 tickers per call.
    Respects 5 calls/minute by sleeping 12s between requests.
    """
    prices = {}
    base = "https://www.alphavantage.co/query"
    for i in range(0, len(tickers), 100):
        batch = tickers[i : i + 100]
        resp = requests.get(base, params={
            "function": "BATCH_STOCK_QUOTES",
            "symbols": ",".join(batch),
            "apikey": api_key
        })
        data = resp.json().get("Stock Quotes", [])
        for q in data:
            sym = q["1. symbol"]
            prices[sym] = float(q["2. price"])
        # stay under 5 calls/min
        time.sleep(12)
    return prices



# simple in-process cache
_price_cache = {}

def get_live_price_finnhub(symbol: str,
                           api_key: str = None,
                           max_retries: int = 3,
                           rate_limit_interval: float = 1.0) -> float:
    """
    Fetch current price for `symbol` from Finnhub, with rate-limiting and retry.
    Caches within the process so duplicate symbols don’t cost extra calls.

    Args:
      symbol: e.g. "AAPL"
      api_key: if None, read from FINNHUB_API_KEY env var
      max_retries: how many times to retry on 429 before giving up
      rate_limit_interval: min seconds between calls

    Returns:
      float price, or raises ValueError on permanent failure.
    """
    symbol = symbol.upper()
    # return cached if available
    if symbol in _price_cache:
        return _price_cache[symbol]

    if api_key is None:
        api_key = os.getenv('FINNHUB_API_KEY')
        if not api_key:
            raise ValueError("No API key: set FINNHUB_API_KEY")

    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": symbol, "token": api_key}

    for attempt in range(1, max_retries+1):
        try:
            resp = requests.get(url, params=params, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            price = data.get("c")
            if price is None:
                raise ValueError(f"Unexpected payload: {data}")
            price = float(price)
            _price_cache[symbol] = price
            time.sleep(rate_limit_interval)   # throttle
            return price

        except HTTPError as e:
            if resp.status_code == 429 and attempt < max_retries:
                backoff = 2 ** (attempt - 1)
                print(f"Rate limit hit, retrying in {backoff}s… (attempt {attempt})")
                time.sleep(backoff)
                continue
            else:
                raise

    raise ValueError(f"Couldn’t fetch price for {symbol} after {max_retries} retries")


def fetch_prices_yahoo(tickers) -> dict:
    """
    Uses yfinance to download daily close price for all tickers at once.
    """
    import yfinance as yf
    df = yf.download(
        tickers,
        period="1d",
        interval="1d",
        threads=True,
        progress=False
    )["Close"]
    prices = {}
    # if multiple tickers, df is a DataFrame; else it's a Series
    if isinstance(df, pd.DataFrame):
        for sym in tickers:
            try:
                prices[sym] = float(df[sym].iloc[-1])
            except Exception:
                prices[sym] = None
    else:
        prices[tickers[0]] = float(df.iloc[-1])
    return prices


def compute_allocation(df: pd.DataFrame, capital: float, whole_stocks: bool):
    """
    Prints allocation either in fractional shares or whole shares.
    """
    remaining = capital
    if whole_stocks:
        for _, row in df.iterrows():
            alloc = capital * (row["Weight"] / 100)
            shares = floor(alloc / row["Price"])
            cost = shares * row["Price"]
            remaining -= cost
            print(f"{row['Symbol']}  #shares: {shares}")
        print(f"Capital left over: ${remaining:,.2f}")
    else:
        for _, row in df.iterrows():
            alloc = capital * (row["Weight"] / 100)
            shares = alloc / row["Price"]
            print(f"{row['Symbol']}  invest ${alloc:,.2f} → {shares:.6f} shares")


def main():
    args = parse_args()

    # Read holdings
    holdings = holdings_parser.get_holdings()

    # Apply blacklist
    blacklist = pd.read_csv(args.blacklist)["Symbol"].tolist()
    holdings = holdings[~holdings["Symbol"].isin(blacklist)].reset_index(drop=True)

    # Fetch prices
    if args.use_yahoo:
        prices = fetch_prices_yahoo(holdings["Symbol"].tolist())
    else:
        key = load_api_key(args.api_key_path)
        #prices = fetch_prices_alpha(holdings["Symbol"].tolist(), key)
        #prices = get_live_price_finnhub(holdings["Symbol"].tolist(), key)
        holdings["Price"] = holdings["Symbol"].apply(
            lambda sym: get_live_price_finnhub(sym, api_key=key)  # key = your Finnhub token
        )

    # drop any that failed
    holdings = holdings[holdings["Price"] > 0].copy()

    # Re-normalize weights now that we’ve removed misses
    holdings["Weight"] = holdings["Weight"] / holdings["Weight"].sum() * 100

    compute_allocation(
        df=holdings,
        capital=args.capital,
        whole_stocks=args.non_fractional_stocks
    )


if __name__ == "__main__":
    main()
