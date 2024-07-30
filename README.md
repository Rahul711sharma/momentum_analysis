# Stock Analysis with Moving Averages and Returns

This Streamlit application provides an analysis of stock data using moving averages and returns. The app supports two investment strategies:
1. Investing in the same top 10 stocks throughout the year.
2. Investing in the top 10 stocks based on the Return to Risk Ratio recalculated each month.

## Features

- Fetches historical stock data for the past 2 years using the yfinance API.
- Calculates various financial metrics including last year's return, last 6 months' return, last 3 months' return, average return, standard deviation, and return to risk ratio.
- Simulates two investment strategies and displays the results.
- Visualizes monthly returns, top 10 stocks each month, and monthly return amounts by stock.

## Installation

## Clone repo
```sh
git clone https://github.com/rahul711sharma/momentum_analysis.git
cd momentum_analysis
```
## Environment setup
```sh
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
streamlit run main.py
