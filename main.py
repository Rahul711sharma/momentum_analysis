# Install necessary libraries
# !pip install streamlit yfinance pandas numpy plotly

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

today = str(pd.Timestamp.utcnow().date())

def main():
    st.title('Stock Analysis with Moving Averages and Returns')
    errored_tickers = []
    tickers_raw_data = []
    # Fetch data from Yfinance
    @st.cache_data
    def get_stock_data(ticker, period='2y'):
        # data = pd.read_csv('constants/nse_2024-07-23.csv', index_col=[0], low_memory=False, header=[0, 1])
        # data = data[[i for i in data.columns if ticker in i[1] else None]]

        try:
            data = pd.read_csv(f'/Users/rahulsharma/Documents/experiments/Momentum/tickers_data/{ticker}_{today}.csv', index_col=0)
            data.index = pd.to_datetime(data.index).tz_convert(None)


            # stock = yf.Ticker(ticker)
            # data = stock.history(period=period)
            # if data.index.tz is not None:
            #
            #     data.to_csv(f'/Users/rahulsharma/Documents/experiments/Momentum/tickers_data/{ticker}_{today}.csv')
            #     data.index = data.index.tz_convert(None)  # Convert to timezone-naive if timezone-aware
            #     tickers_raw_data.append(data)
            return data
        except Exception as e:
            # st.error(f"Error fetching data for {ticker}: {e}")
            errored_tickers.append(f'{ticker}')
            return pd.DataFrame()
        print(f'errored tickers: {errored_tickers}')

    # Calculate Returns and Metrics
    def calculate_returns(data, ticker):
        try:
            end_date = data.index[-1]
            start_date_1y = end_date - pd.DateOffset(years=1)
            start_date_6m = end_date - pd.DateOffset(months=6)
            start_date_3m = end_date - pd.DateOffset(months=3)

            last_year_data = data.loc[start_date_1y:end_date]
            last_six_months_data = data.loc[start_date_6m:end_date]
            last_three_months_data = data.loc[start_date_3m:end_date]

            last_year_return = (last_year_data['Close'].iloc[-1] - last_year_data['Close'].iloc[0]) / \
                               last_year_data['Close'].iloc[0] * 100
            last_six_months_return = (last_six_months_data['Close'].iloc[-1] - last_six_months_data['Close'].iloc[0]) / \
                                     last_six_months_data['Close'].iloc[0] * 100
            last_three_months_return = (last_three_months_data['Close'].iloc[-1] - last_three_months_data['Close'].iloc[
                0]) / last_three_months_data['Close'].iloc[0] * 100
            avg_return = (last_year_return + last_six_months_return + last_three_months_return) / 3
            std_dev = last_year_data['Close'].pct_change().std() * np.sqrt(252) * 100
            ratio = avg_return / std_dev if std_dev != 0 else np.nan

            return {
                'Ticker': ticker,
                'Last Year Return (%)': last_year_return,
                'Last 6 Months Return (%)': last_six_months_return,
                'Last 3 Months Return (%)': last_three_months_return,
                'Average Return (%)': avg_return,
                '1 Year Std Dev (%)': std_dev,
                'Return to Risk Ratio': ratio
            }
        except Exception as e:
            st.error(f"Error calculating returns for {ticker}: {e}")
            return None

    # Simulate investment for strategy 1
    def simulate_investment_strategy_1(tickers_data, amount=100000):
        monthly_returns = {}
        individual_monthly_returns = {ticker: {} for ticker in tickers_data['Ticker']}
        top_10_monthly = {}
        start_date = pd.Timestamp.today().normalize() - pd.DateOffset(years=1)
        end_date = pd.Timestamp.today().normalize()

        for month in pd.date_range(start_date, end_date, freq='MS'):
            month_end = (month + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
            if month_end > end_date:
                month_end = end_date

            tickers_data['Month Return'] = tickers_data.apply(
                lambda row: (row['Close'].asof(month_end) - row['Close'].asof(month)) / row['Close'].asof(month) * 100
                if pd.notnull(row['Close'].asof(month)) and pd.notnull(row['Close'].asof(month_end)) else np.nan,
                axis=1)

            for ticker in tickers_data['Ticker']:
                individual_monthly_returns[ticker][month.strftime('%Y-%m')] = \
                tickers_data[tickers_data['Ticker'] == ticker]['Month Return'].values[0]

            top_10_tickers = tickers_data.nlargest(10, 'Return to Risk Ratio')[['Ticker', 'Month Return']]
            avg_month_return = tickers_data.loc[
                tickers_data['Ticker'].isin(top_10_tickers['Ticker']), 'Month Return'].mean()

            monthly_returns[month.strftime('%Y-%m')] = avg_month_return
            top_10_monthly[month.strftime('%Y-%m')] = top_10_tickers.set_index('Ticker').to_dict()[
                'Month Return']

        total_return = np.prod([1 + r / 100 for r in monthly_returns.values() if not np.isnan(r)]) - 1
        total_amount = amount * 12 * (1 + total_return)

        individual_monthly_returns_df = pd.DataFrame(individual_monthly_returns).transpose()
        top_10_monthly_df = pd.DataFrame(top_10_monthly).transpose()

        return total_amount, monthly_returns, individual_monthly_returns_df, top_10_monthly_df

    # Simulate investment for strategy 2
    # Simulate investment for strategy 2 with buying and selling prices tracking
    def simulate_investment_strategy_2(tickers_list, amount=100000):
        start_date = pd.Timestamp.today().normalize() - pd.DateOffset(years=1)
        end_date = pd.Timestamp.today().normalize()
        monthly_investment = amount

        monthly_returns = {}
        individual_monthly_returns = {ticker: {} for ticker in tickers_list}
        top_10_monthly = {}
        total_amount = 0
        portfolio = {}
        buying_prices = []
        selling_prices = []

        for month in pd.date_range(start_date, end_date, freq='MS'):
            month_end = (month + pd.DateOffset(months=1)) - pd.DateOffset(days=1)
            if month_end > end_date:
                month_end = end_date

            tickers_stats = []
            close_prices = {}

            for ticker in tickers_list:
                data = get_stock_data(ticker)
                if not data.empty:
                    returns = calculate_returns(data.loc[:month_end][-252:], ticker)
                    if returns:
                        tickers_stats.append(returns)
                        close_prices[ticker] = data['Close']

            tickers_data = pd.DataFrame(tickers_stats)
            if tickers_data.empty:
                continue

            tickers_data['Close'] = tickers_data['Ticker'].map(close_prices)

            tickers_data['Month Return'] = tickers_data.apply(
                lambda row: (row['Close'].asof(month_end) - row['Close'].asof(month)) / row['Close'].asof(month) * 100
                if pd.notnull(row['Close'].asof(month)) and pd.notnull(row['Close'].asof(month_end)) else np.nan,
                axis=1)

            for ticker in tickers_data['Ticker']:
                individual_monthly_returns[ticker][month.strftime('%Y-%m')] = \
                    tickers_data[tickers_data['Ticker'] == ticker]['Month Return'].values[0]

            top_10_tickers = tickers_data.nlargest(10, 'Return to Risk Ratio')[['Ticker', 'Month Return']]
            avg_month_return = tickers_data.loc[
                tickers_data['Ticker'].isin(top_10_tickers['Ticker']), 'Month Return'].mean()

            monthly_returns[month.strftime('%Y-%m')] = avg_month_return
            top_10_monthly[month.strftime('%Y-%m')] = top_10_tickers.set_index('Ticker').to_dict()[
                'Month Return']

            # Sell stocks that are no longer in the top 10
            current_top_10 = set(top_10_tickers['Ticker'])
            for ticker in list(portfolio.keys()):
                if ticker not in current_top_10:
                    selling_price = close_prices[ticker].asof(month_end)
                    selling_prices.append({
                        'Ticker': ticker,
                        'Month': month.strftime('%Y-%m'),
                        'Selling Price': selling_price
                    })
                    total_amount += portfolio[ticker] * selling_price
                    del portfolio[ticker]

            # Buy new top 10 stocks
            for ticker in current_top_10:
                if ticker not in portfolio:
                    buying_price = close_prices[ticker].asof(month)
                    buying_prices.append({
                        'Ticker': ticker,
                        'Month': month.strftime('%Y-%m'),
                        'Buying Price': buying_price
                    })
                    portfolio[ticker] = monthly_investment / len(current_top_10) / buying_price

            # Update portfolio value
            for ticker in portfolio:
                current_price = close_prices[ticker].asof(month_end)
                total_amount += portfolio[ticker] * current_price

        individual_monthly_returns_df = pd.DataFrame(individual_monthly_returns).transpose()
        top_10_monthly_df = pd.DataFrame(top_10_monthly).transpose()
        buying_prices_df = pd.DataFrame(buying_prices)
        selling_prices_df = pd.DataFrame(selling_prices)

        return total_amount, monthly_returns, individual_monthly_returns_df, top_10_monthly_df, buying_prices_df, selling_prices_df

    # Main Application Logic
    tickers = st.text_area('Enter stock tickers (comma separated):', '360ONE.NS, 3MINDIA.NS, ABB.NS, ACC.NS, AIAENG.NS, APLAPOLLO.NS, AUBANK.NS, AARTIIND.NS, AAVAS.NS, ABBOTINDIA.NS, ACE.NS, ADANIENSOL.NS, ADANIENT.NS, ADANIGREEN.NS, ADANIPORTS.NS, ADANIPOWER.NS, ATGL.NS, AWL.NS, ABCAPITAL.NS, ABFRL.NS, AEGISLOG.NS, AETHER.NS, AFFLE.NS, AJANTPHARM.NS, APLLTD.NS, ALKEM.NS, ALKYLAMINE.NS, ALLCARGO.NS, ALOKINDS.NS, ARE&M.NS, AMBER.NS, AMBUJACEM.NS, ANANDRATHI.NS, ANGELONE.NS, ANURAS.NS, APARINDS.NS, APOLLOHOSP.NS, APOLLOTYRE.NS, APTUS.NS, ACI.NS, ASAHIINDIA.NS, ASHOKLEY.NS, ASIANPAINT.NS, ASTERDM.NS, ASTRAZEN.NS, ASTRAL.NS, ATUL.NS, AUROPHARMA.NS, AVANTIFEED.NS, DMART.NS, AXISBANK.NS, BEML.NS, BLS.NS, BSE.NS, BAJAJ-AUTO.NS, BAJFINANCE.NS, BAJAJFINSV.NS, BAJAJHLDNG.NS, BALAMINES.NS, BALKRISIND.NS, BALRAMCHIN.NS, BANDHANBNK.NS, BANKBARODA.NS, BANKINDIA.NS, MAHABANK.NS, BATAINDIA.NS, BAYERCROP.NS, BERGEPAINT.NS, BDL.NS, BEL.NS, BHARATFORG.NS, BHEL.NS, BPCL.NS, BHARTIARTL.NS, BIKAJI.NS, BIOCON.NS, BIRLACORPN.NS, BSOFT.NS, BLUEDART.NS, BLUESTARCO.NS, BBTC.NS, BORORENEW.NS, BOSCHLTD.NS, BRIGADE.NS, BRITANNIA.NS, MAPMYINDIA.NS, CCL.NS, CESC.NS, CGPOWER.NS, CIEINDIA.NS, CRISIL.NS, CSBBANK.NS, CAMPUS.NS, CANFINHOME.NS, CANBK.NS, CAPLIPOINT.NS, CGCL.NS, CARBORUNIV.NS, CASTROLIND.NS, CEATLTD.NS, CELLO.NS, CENTRALBK.NS, CDSL.NS, CENTURYPLY.NS, CENTURYTEX.NS, CERA.NS, CHALET.NS, CHAMBLFERT.NS, CHEMPLASTS.NS, CHENNPETRO.NS, CHOLAHLDNG.NS, CHOLAFIN.NS, CIPLA.NS, CUB.NS, CLEAN.NS, COALINDIA.NS, COCHINSHIP.NS, COFORGE.NS, COLPAL.NS, CAMS.NS, CONCORDBIO.NS, CONCOR.NS, COROMANDEL.NS, CRAFTSMAN.NS, CREDITACC.NS, CROMPTON.NS, CUMMINSIND.NS, CYIENT.NS, DCMSHRIRAM.NS, DLF.NS, DOMS.NS, DABUR.NS, DALBHARAT.NS, DATAPATTNS.NS, DEEPAKFERT.NS, DEEPAKNTR.NS, DELHIVERY.NS, DEVYANI.NS, DIVISLAB.NS, DIXON.NS, LALPATHLAB.NS, DRREDDY.NS, DUMMYSANOF.NS, EIDPARRY.NS, EIHOTEL.NS, EPL.NS, EASEMYTRIP.NS, EICHERMOT.NS, ELECON.NS, ELGIEQUIP.NS, EMAMILTD.NS, ENDURANCE.NS, ENGINERSIN.NS, EQUITASBNK.NS, ERIS.NS, ESCORTS.NS, EXIDEIND.NS, FDC.NS, NYKAA.NS, FEDERALBNK.NS, FACT.NS, FINEORG.NS, FINCABLES.NS, FINPIPE.NS, FSL.NS, FIVESTAR.NS, FORTIS.NS, GAIL.NS, GMMPFAUDLR.NS, GMRINFRA.NS, GRSE.NS, GICRE.NS, GILLETTE.NS, GLAND.NS, GLAXO.NS, GLS.NS, GLENMARK.NS, MEDANTA.NS, GPIL.NS, GODFRYPHLP.NS, GODREJCP.NS, GODREJIND.NS, GODREJPROP.NS, GRANULES.NS, GRAPHITE.NS, GRASIM.NS, GESHIP.NS, GRINDWELL.NS, GAEL.NS, FLUOROCHEM.NS, GUJGASLTD.NS, GMDCLTD.NS, GNFC.NS, GPPL.NS, GSFC.NS, GSPL.NS, HEG.NS, HBLPOWER.NS, HCLTECH.NS, HDFCAMC.NS, HDFCBANK.NS, HDFCLIFE.NS, HFCL.NS, HAPPSTMNDS.NS, HAPPYFORGE.NS, HAVELLS.NS, HEROMOTOCO.NS, HSCL.NS, HINDALCO.NS, HAL.NS, HINDCOPPER.NS, HINDPETRO.NS, HINDUNILVR.NS, HINDZINC.NS, POWERINDIA.NS, HOMEFIRST.NS, HONASA.NS, HONAUT.NS, HUDCO.NS, ICICIBANK.NS, ICICIGI.NS, ICICIPRULI.NS, ISEC.NS, IDBI.NS, IDFCFIRSTB.NS, IDFC.NS, IIFL.NS, IRB.NS, IRCON.NS, ITC.NS, ITI.NS, INDIACEM.NS, IBULHSGFIN.NS, INDIAMART.NS, INDIANB.NS, IEX.NS, INDHOTEL.NS, IOC.NS, IOB.NS, IRCTC.NS, IRFC.NS, INDIGOPNTS.NS, IGL.NS, INDUSTOWER.NS, INDUSINDBK.NS, NAUKRI.NS, INFY.NS, INOXWIND.NS, INTELLECT.NS, INDIGO.NS, IPCALAB.NS, JBCHEPHARM.NS, JKCEMENT.NS, JBMA.NS, JKLAKSHMI.NS, JKPAPER.NS, JMFINANCIL.NS, JSWENERGY.NS, JSWINFRA.NS, JSWSTEEL.NS, JAIBALAJI.NS, J&KBANK.NS, JINDALSAW.NS, JSL.NS, JINDALSTEL.NS, JIOFIN.NS, JUBLFOOD.NS, JUBLINGREA.NS, JUBLPHARMA.NS, JWL.NS, JUSTDIAL.NS, JYOTHYLAB.NS, KPRMILL.NS, KEI.NS, KNRCON.NS, KPITTECH.NS, KRBL.NS, KSB.NS, KAJARIACER.NS, KPIL.NS, KALYANKJIL.NS, KANSAINER.NS, KARURVYSYA.NS, KAYNES.NS, KEC.NS, KFINTECH.NS, KOTAKBANK.NS, KIMS.NS, LTF.NS, LTTS.NS, LICHSGFIN.NS, LTIM.NS, LT.NS, LATENTVIEW.NS, LAURUSLABS.NS, LXCHEM.NS, LEMONTREE.NS, LICI.NS, LINDEINDIA.NS, LLOYDSME.NS, LUPIN.NS, MMTC.NS, MRF.NS, MTARTECH.NS, LODHA.NS, MGL.NS, MAHSEAMLES.NS, M&MFIN.NS, M&M.NS, MHRIL.NS, MAHLIFE.NS, MANAPPURAM.NS, MRPL.NS, MANKIND.NS, MARICO.NS, MARUTI.NS, MASTEK.NS, MFSL.NS, MAXHEALTH.NS, MAZDOCK.NS, MEDPLUS.NS, METROBRAND.NS, METROPOLIS.NS, MINDACORP.NS, MSUMI.NS, MOTILALOFS.NS, MPHASIS.NS, MCX.NS, MUTHOOTFIN.NS, NATCOPHARM.NS, NBCC.NS, NCC.NS, NHPC.NS, NLCINDIA.NS, NMDC.NS, NSLNISP.NS, NTPC.NS, NH.NS, NATIONALUM.NS, NAVINFLUOR.NS, NESTLEIND.NS, NETWORK18.NS, NAM-INDIA.NS, NUVAMA.NS, NUVOCO.NS, OBEROIRLTY.NS, ONGC.NS, OIL.NS, OLECTRA.NS, PAYTM.NS, OFSS.NS, POLICYBZR.NS, PCBL.NS, PIIND.NS, PNBHOUSING.NS, PNCINFRA.NS, PVRINOX.NS, PAGEIND.NS, PATANJALI.NS, PERSISTENT.NS, PETRONET.NS, PHOENIXLTD.NS, PIDILITIND.NS, PEL.NS, PPLPHARMA.NS, POLYMED.NS, POLYCAB.NS, POONAWALLA.NS, PFC.NS, POWERGRID.NS, PRAJIND.NS, PRESTIGE.NS, PRINCEPIPE.NS, PRSMJOHNSN.NS, PGHH.NS, PNB.NS, QUESS.NS, RRKABEL.NS, RBLBANK.NS, RECLTD.NS, RHIM.NS, RITES.NS, RADICO.NS, RVNL.NS, RAILTEL.NS, RAINBOW.NS, RAJESHEXPO.NS, RKFORGE.NS, RCF.NS, RATNAMANI.NS, RTNINDIA.NS, RAYMOND.NS, REDINGTON.NS, RELIANCE.NS, RBA.NS, ROUTE.NS, SBFC.NS, SBICARD.NS, SBILIFE.NS, SJVN.NS, SKFINDIA.NS, SRF.NS, SAFARI.NS, MOTHERSON.NS, SANOFI.NS, SAPPHIRE.NS, SAREGAMA.NS, SCHAEFFLER.NS, SCHNEIDER.NS, SHREECEM.NS, RENUKA.NS, SHRIRAMFIN.NS, SHYAMMETL.NS, SIEMENS.NS, SIGNATURE.NS, SOBHA.NS, SOLARINDS.NS, SONACOMS.NS, SONATSOFTW.NS, STARHEALTH.NS, SBIN.NS, SAIL.NS, SWSOLAR.NS, STLTECH.NS, SUMICHEM.NS, SPARC.NS, SUNPHARMA.NS, SUNTV.NS, SUNDARMFIN.NS, SUNDRMFAST.NS, SUNTECK.NS, SUPREMEIND.NS, SUVENPHAR.NS, SUZLON.NS, SWANENERGY.NS, SYNGENE.NS, SYRMA.NS, TV18BRDCST.NS, TVSMOTOR.NS, TVSSCS.NS, TMB.NS, TANLA.NS, TATACHEM.NS, TATACOMM.NS, TCS.NS, TATACONSUM.NS, TATAELXSI.NS, TATAINVEST.NS, TATAMTRDVR.NS, TATAMOTORS.NS, TATAPOWER.NS, TATASTEEL.NS, TATATECH.NS, TTML.NS, TECHM.NS, TEJASNET.NS, NIACL.NS, RAMCOCEM.NS, THERMAX.NS, TIMKEN.NS, TITAGARH.NS, TITAN.NS, TORNTPHARM.NS, TORNTPOWER.NS, TRENT.NS, TRIDENT.NS, TRIVENI.NS, TRITURBINE.NS, TIINDIA.NS, UCOBANK.NS, UNOMINDA.NS, UPL.NS, UTIAMC.NS, UJJIVANSFB.NS, ULTRACEMCO.NS, UNIONBANK.NS, UBL.NS, UNITDSPR.NS, USHAMART.NS, VGUARD.NS, VIPIND.NS, VAIBHAVGBL.NS, VTL.NS, VARROC.NS, VBL.NS, MANYAVAR.NS, VEDL.NS, VIJAYA.NS, IDEA.NS, VOLTAS.NS, WELCORP.NS, WELSPUNLIV.NS, WESTLIFE.NS, WHIRLPOOL.NS, WIPRO.NS, YESBANK.NS, ZFCVINDIA.NS, ZEEL.NS, ZENSARTECH.NS, ZOMATO.NS, ZYDUSLIFE.NS, ECLERX.NS')
    tickers_list = [ticker.strip() for ticker in tickers.split(',')]
    st.write(f'total number of companies analysed : {len(tickers_list)}')
    tickers_stats = []

    for ticker in tickers_list:
        data = get_stock_data(ticker)
        if not data.empty:
            returns = calculate_returns(data[-252:], ticker)
            if returns:
                tickers_stats.append(returns)

    tickers_data = pd.DataFrame(tickers_stats)

    if not tickers_data.empty:
        st.write('### Overall Stock Returns and Metrics')
        st.write(tickers_data)

        # Simulate investment for strategy 1
        close_prices = {}
        for ticker in tickers_list:
            data = get_stock_data(ticker)
            if not data.empty:
                close_prices[ticker] = data['Close']

        tickers_data_with_close = tickers_data.copy()
        tickers_data_with_close['Close'] = tickers_data_with_close['Ticker'].map(close_prices)

        total_amount_1, monthly_returns_1, individual_monthly_returns_df_1, top_10_monthly_df_1 = simulate_investment_strategy_1(
            tickers_data_with_close)

        st.write('### Investment Simulation Results - Strategy 1: Monthly SIP on year end top 10 companies only')
        st.write(
            'Total amount at the end of the year if invested $100,000 each month in top 10 companies based on Return to Risk Ratio:')
        st.write(f"${total_amount_1:,.2f}")

        st.write('### Monthly Returns for Top 10 Companies')
        st.write(monthly_returns_1)

        st.write('### Monthly Returns by Stock')
        st.write(individual_monthly_returns_df_1)

        st.write('### Top 10 Companies Each Month')
        st.write(top_10_monthly_df_1)

        # Simulate investment for strategy 2
        total_amount_2, monthly_returns_2, individual_monthly_returns_df_2, top_10_monthly_df_2, buying, selling = simulate_investment_strategy_2(
            tickers_list)

        st.write('### Investment Simulation Results - Strategy 2: Invest on top 10 companies monthly')
        st.write(
            'Total amount at the end of the year if invested $100,000 each month equally in top 10 companies based on Return to Risk Ratio:')
        st.write(f"${total_amount_2:,.2f}")

        st.write('### Monthly Returns for Top 10 Companies')
        st.write(monthly_returns_2)

        st.write('### Monthly Returns by Stock')
        st.write(individual_monthly_returns_df_2)

        st.write('### Top 10 Companies Each Month')
        st.write(top_10_monthly_df_2)

        st.write("### Top 10 Companies Portfolio buying selling")
        data_container = st.container()

        with data_container:
            buy, sell = st.columns(2)
            with buy:
                st.table(buying)
            with sell:
                st.table(selling)

if __name__=="__main__":
    main()