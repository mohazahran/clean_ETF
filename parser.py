import re
import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

SPUS_URL = "https://stockanalysis.com/etf/spus/holdings/"

# ---------- helper: quote bare keys so it becomes legal JSON ---------------
_KEY_QUOTER = re.compile(r'(?<=\{|,)\s*([A-Za-z_]\w*)\s*:')

def quote_js_keys(js_literal: str) -> str:
    """Turn   {no:1,n:"Foo"}   →   {"no":1,"n":"Foo"}   (JSON-safe)."""
    return _KEY_QUOTER.sub(r'"\1":', js_literal)

# ---------------------------------------------------------------------------

def get_holdings(url: str = SPUS_URL) -> pd.DataFrame:
    html = requests.get(url, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    # 1) find the <script> that contains the big `const data = …` blob
    script = soup.find("script", string=lambda s: s and "const data" in s)
    if not script:
        raise RuntimeError("Holdings <script> not found")

    script_text = script.string or script.get_text()

    # 2) grab ONLY the holdings array   (note: *no quotes* around holdings)
    m = re.search(r'\bholdings\s*:\s*(\[\{[\s\S]*?\}\])',   # ← quotes removed
                  script_text, flags=re.DOTALL)
    if not m:
        raise RuntimeError("'holdings' array not found")

    holdings_js = m.group(1)          # still JS‐style (bare keys)

    # 3) quote bare keys → valid JSON, then parse
    holdings = json.loads(quote_js_keys(holdings_js))

    # 4) tidy DataFrame
    df = (pd.DataFrame(holdings)
            .rename(columns={"s": "Symbol", "n": "Name",
                             "as": "Weight", "sh": "Shares"}))
    df["Symbol"] = df["Symbol"].str.lstrip("$")
    df["Weight"] = df["Weight"].str.rstrip("%").astype(float)
    df["Shares"] = df["Shares"].str.replace(",", "").astype(int)

    return df[["Symbol", "Name", "Weight", "Shares"]]


if __name__ == "__main__":
    print(get_holdings().head())
