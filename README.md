# clean_ETF
This is a simple script that makes you in control of the investment of SP500. As you know SP500 has haram stocks and also blood stained stocks that should be boycotted (e.g. Macdonald's). This script is tracking SPUS which is a halal version of SP500. You can specify list of blacklisted stock to be excluded (Boycotted). You input your capital (the amount of money you'd like to invest). It will give you the stocks you should buy and the number of shares per stock. You need to register in alphavantage to get a free API key which will be used to get up-to-date stock prices. The free API will give you 25 price per day, so using the free version you will be getting recommendations for the top 25 holding in SPUS (excluding the blacklist).

The recommendations assumes the ability to buy fractional stocks (e.g. to buy 0.25 of apple stock). Fractional buying is supported in most of the trading apps I saw, however, selling them is a bit tricky (read about that if you think it's a risk for you). If you prefer whole stocks, there is an input "non_fractional_stocks" use it.

Example usage:
For fractional stocks
--capital 100000 --api_key_path api_key.txt

For whole stockes
--capital 100000 --api_key_path api_key.txt --non_fractional_stocks
