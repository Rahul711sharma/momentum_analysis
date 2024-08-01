# Install necessary libraries
# !pip install streamlit yfinance pandas numpy plotly

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from constants.config import nse_500

# today = str(pd.Timestamp.utcnow().date())
today = '2024-07-27'

def main():
    st.title('Stock Analysis with Weekly Momentum and Returns')
    errored_tickers = []
    tickers_raw_data = []

    # Fetch data from Yfinance
    @st.cache_data
    def get_stock_data(ticker, period='2y'):
        try:
            data = pd.read_csv(f'/Users/rahulsharma/Documents/experiments/Momentum/tickers_data/{ticker}_{today}.csv',
                               index_col=0)
            data.index = pd.to_datetime(data.index).tz_convert(None)
            return data
        except Exception as e:
            errored_tickers.append(f'{ticker}')
            return pd.DataFrame()
        print(f'errored tickers: {errored_tickers}')

    # Calculate Weekly Returns and Risk to Return Ratio
    def calculate_weekly_returns(data, ticker):
        try:
            # Resample to weekly frequency
            weekly_data = data['Close'].resample('W').last()

            # Calculate weekly returns
            weekly_returns = weekly_data.pct_change().dropna() * 100

            # Calculate the average weekly return
            avg_weekly_return = weekly_returns.mean()

            # Calculate the weekly standard deviation
            weekly_std_dev = weekly_returns.std()

            # Calculate the return-to-risk ratio
            return_to_risk_ratio = avg_weekly_return / weekly_std_dev if weekly_std_dev != 0 else np.nan

            return {
                'Ticker': ticker,
                'Average Weekly Return (%)': avg_weekly_return,
                'Weekly Std Dev (%)': weekly_std_dev,
                'Return to Risk Ratio': return_to_risk_ratio
            }
        except Exception as e:
            st.error(f"Error calculating weekly returns for {ticker}: {e}")
            return None

    # Simulate weekly momentum investment strategy
    def simulate_investment_strategy_weekly(tickers_list, amount=100000):
        start_date = pd.Timestamp.today().normalize() - pd.DateOffset(years=1)
        end_date = pd.Timestamp.today().normalize()
        weekly_investment = amount / 52

        weekly_returns = {}
        individual_weekly_returns = {ticker: {} for ticker in tickers_list}
        top_10_weekly = {}
        total_amount = 0
        portfolio = {}
        buying_prices = []
        selling_prices = []

        for week in pd.date_range(start_date, end_date, freq='W-MON'):
            week_end = (week + pd.DateOffset(days=6))
            if week_end > end_date:
                week_end = end_date

            tickers_stats = []
            close_prices = {}

            for ticker in tickers_list:
                data = get_stock_data(ticker)
                if not data.empty:
                    returns = calculate_weekly_returns(data.loc[:week_end], ticker)
                    if returns:
                        tickers_stats.append(returns)
                        close_prices[ticker] = data['Close']

            tickers_data = pd.DataFrame(tickers_stats)
            if tickers_data.empty:
                continue

            tickers_data['Close'] = tickers_data['Ticker'].map(close_prices)

            tickers_data['Week Return'] = tickers_data.apply(
                lambda row: (row['Close'].asof(week_end) - row['Close'].asof(week)) / row['Close'].asof(week) * 100
                if pd.notnull(row['Close'].asof(week)) and pd.notnull(row['Close'].asof(week_end)) else np.nan,
                axis=1)

            for ticker in tickers_data['Ticker']:
                individual_weekly_returns[ticker][week.strftime('%Y-%W')] = \
                    tickers_data[tickers_data['Ticker'] == ticker]['Week Return'].values[0]

            top_10_tickers = tickers_data.nlargest(10, 'Return to Risk Ratio')[['Ticker', 'Week Return']]
            avg_week_return = tickers_data.loc[
                tickers_data['Ticker'].isin(top_10_tickers['Ticker']), 'Week Return'].mean()

            weekly_returns[week.strftime('%Y-%W')] = avg_week_return
            top_10_weekly[week.strftime('%Y-%W')] = top_10_tickers.set_index('Ticker').to_dict()[
                'Week Return']

            # Sell stocks that are no longer in the top 10
            current_top_10 = set(top_10_tickers['Ticker'])
            for ticker in list(portfolio.keys()):
                if ticker not in current_top_10:
                    selling_price = close_prices[ticker].asof(week_end)
                    selling_prices.append({
                        'Ticker': ticker,
                        'Week': week.strftime('%Y-%W'),
                        'Selling Price': selling_price
                    })
                    total_amount += portfolio[ticker] * selling_price
                    del portfolio[ticker]

            # Buy new top 10 stocks
            for ticker in current_top_10:
                if ticker not in portfolio:
                    buying_price = close_prices[ticker].asof(week)
                    buying_prices.append({
                        'Ticker': ticker,
                        'Week': week.strftime('%Y-%W'),
                        'Buying Price': buying_price
                    })
                    portfolio[ticker] = weekly_investment / len(current_top_10) / buying_price

            # Update portfolio value
            for ticker in portfolio:
                current_price = close_prices[ticker].asof(week_end)
                total_amount += portfolio[ticker] * current_price

        individual_weekly_returns_df = pd.DataFrame(individual_weekly_returns).transpose()
        top_10_weekly_df = pd.DataFrame(top_10_weekly).transpose()
        buying_prices_df = pd.DataFrame(buying_prices)
        selling_prices_df = pd.DataFrame(selling_prices)

        return total_amount, weekly_returns, individual_weekly_returns_df, top_10_weekly_df, buying_prices_df, selling_prices_df

    # Main Application Logic
    tickers = st.text_area('Enter stock tickers (comma separated):', ', '.join(nse_500))
    tickers_list = [ticker.strip() for ticker in tickers.split(', ')]
    st.write(f'Total number of companies analysed: {len(tickers_list)}')
    tickers_stats = []

    for ticker in tickers_list:
        data = get_stock_data(ticker)
        if not data.empty:
            returns = calculate_weekly_returns(data, ticker)
            if returns:
                tickers_stats.append(returns)

    tickers_data = pd.DataFrame(tickers_stats)

    if not tickers_data.empty:
        st.write('### Overall Stock Returns and Metrics')
        st.write(tickers_data)

        # Simulate weekly momentum investment strategy
        total_amount, weekly_returns, individual_weekly_returns_df, top_10_weekly_df, buying, selling = simulate_investment_strategy_weekly(
            tickers_list)

        st.write('### Investment Simulation Results - Weekly Momentum Strategy')
        st.write(
            'Total amount at the end of the year if invested $100,000 equally in top 10 companies based on Weekly Return to Risk Ratio:')
        st.write(f"${total_amount:,.2f}")

        st.write('### Weekly Returns for Top 10 Companies')
        st.write(weekly_returns)

        st.write('### Weekly Returns by Stock')
        st.write(individual_weekly_returns_df)

        st.write('### Top 10 Companies Each Week')
        st.write(top_10_weekly_df)

        st.write("### Top 10 Companies Portfolio Buying and Selling Prices")
        data_container = st.container()

        with data_container:
            buy, sell = st.columns(2)
            with buy:
                st.table(buying)
            with sell:
                st.table(selling)

if __name__=="__main__":
    main()