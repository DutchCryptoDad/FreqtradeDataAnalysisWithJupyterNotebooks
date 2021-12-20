#!/usr/bin/env python
# coding: utf-8

# # Freqtrade strategy analysis Jupyter notebook
# 
# To use this notebook in new environments, first you should have Jupyter notebooks installed on your system.  
# Second, you should activate the Freqtrade virtual environment and install the ipykernel. This way you create a new type of virtual kernel for/with freqtrade that you can activate/use for your notebooks (notebooks > new > freqtrade)
# 
# ```
# # Activate virtual environment
# source .env/bin/activate
# 
# pip install ipykernel
# ipython kernel install --user --name=freqtrade
# # Restart jupyter (lab / notebook)
# # select kernel "freqtrade" in the notebook
# ```
# 
# Then you should download backtesting data for the chosen strategy you want to analyse.
# 
# Also I had to install nbformat in order to plot some charts: ``pip install nbformat``.

# ## Change directory to root
# 
# Start jupyter from the freqtrade directory.
# 
# The following snippet searches for the project root, so relative paths remain consistent.

# In[5]:


import os
from pathlib import Path

# Change directory
# Modify this cell to insure that the output shows the correct path.
# Define all paths relative to the project root shown in the cell output
project_root = "somedir/freqtrade"
i=0
try:
    os.chdirdir(project_root)
    assert Path('LICENSE').is_file()
except:
    while i<4 and (not Path('LICENSE').is_file()):
        os.chdir(Path(Path.cwd(), '../'))
        i+=1
    project_root = Path.cwd()
print(Path.cwd())


# ## Load multiple configuration files
# 
# This option can be useful to inspect the results of passing in multiple configs. This will also run through the whole Configuration initialization, so the configuration is completely initialized to be passed to other methods.
# 
# ```
# config = Configuration.from_files(["config1.json", "config2.json"])
# ```

# In[6]:


import json
from freqtrade.configuration import Configuration

# Load config from multiple files
config = Configuration.from_files(["config.json"])

# Show the config in memory
print(json.dumps(config['original_config'], indent=2))


# For Interactive environments, have an additional configuration specifying user_data_dir and pass this in last, so you don't have to change directories while running the bot. Best avoid relative paths, since this starts at the storage location of the jupyter notebook, unless the directory is changed.

# In[7]:


# {
#     "user_data_dir": "/opt/freqtrade/user_data/"
# }


# ## Strategy Analysis example

# These two sections load the strategy and timeframe. You should change these if you want to use another strategy or timeframe to analyse (beware that you also have enough and the correct backtesting data available).

# In[8]:


from pathlib import Path
from freqtrade.configuration import Configuration

# Customize these according to your needs.

# Initialize empty configuration object
# config = Configuration.from_files([])
# Optionally, use existing configuration file
config = Configuration.from_files(["config.json"])

# Define some constants
config["timeframe"] = "5m"
# Name of the strategy class
config["strategy"] = "SampleStrategy"
# Location of the data
data_location = Path(config['user_data_dir'], 'data', 'binance')
# Pair to analyze - Only use one pair here
pair = "BTC/USDT"


# The code from the freqtrade site consists of the rule ``data_format = "hdf5",``. However this is wrong. The default data downloaded by freqtrade is in json format. 
# 
# If you want to use hdf5 high performance format permanently, add the following rules to your config.json file and download backtest data again for the correct format:
# 
# ```
#     // ...
#     "dataformat_ohlcv": "hdf5",
#     "dataformat_trades": "hdf5",
#     // ...
# 
# ```

# In[9]:


# Load data using values set above
from freqtrade.data.history import load_pair_history

candles = load_pair_history(datadir=data_location,
                            timeframe=config["timeframe"],
                            pair=pair,
                            # CHANGE HDF5 TO JSON WORKS!!
                            data_format = "json",
                            )

# Confirm success
print("Loaded " + str(len(candles)) + f" rows of data for {pair} from {data_location}")
candles.head()


# ## Load and run strategy
# 
# Rerun the cell below each time the strategy file is changed.
# 

# In[10]:


# Load strategy using values set above
from freqtrade.resolvers import StrategyResolver
strategy = StrategyResolver.load_strategy(config)

# Generate buy/sell signals using strategy
df = strategy.analyze_ticker(candles, {'pair': pair})
df.tail()


# ## Display the trade details
# 
# * Note that using data.head() would also work, however most indicators have some "startup" data at the top of the dataframe.
# * Some possible problems * Columns with NaN values at the end of the dataframe * Columns used in crossed*() functions with completely different units
# * Comparison with full backtest * having 200 buy signals as output for one pair from analyze_ticker() does not necessarily mean that 200 trades will be made during backtesting. * Assuming you use only one condition such as, df['rsi'] < 30 as buy condition, this will generate multiple "buy" signals for each pair in sequence (until rsi returns > 29). The bot will only buy on the first of these signals (and also only if a trade-slot ("max_open_trades") is still available), or on one of the middle signals, as soon as a "slot" becomes available.
# 

# In[11]:


# Report results
print(f"Generated {df['buy'].sum()} buy signals")
data = df.set_index('date', drop=False)
data.tail()


# ## Load backtest results to pandas dataframe
# 
# Analyze a trades dataframe (also used below for plotting)

# In[12]:


from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats

# if backtest_dir points to a directory, it'll automatically load the last backtest file.
backtest_dir = config["user_data_dir"] / "backtest_results"
# backtest_dir can also point to a specific file 
# backtest_dir = config["user_data_dir"] / "backtest_results/backtest-result-2020-07-01_20-04-22.json"


# In[13]:


# You can get the full backtest statistics by using the following command.
# This contains all information used to generate the backtest result.
stats = load_backtest_stats(backtest_dir)

strategy = 'SampleStrategy'
# All statistics are available per strategy, so if `--strategy-list` was used during backtest, this will be reflected here as well.
# Example usages:
print(stats['strategy'][strategy]['results_per_pair'])


# In[14]:


# Get pairlist used for this backtest
print(stats['strategy'][strategy]['pairlist'])


# In[15]:


# Get market change (average change of all pairs from start to end of the backtest period)
print(stats['strategy'][strategy]['market_change'])


# In[16]:


# Maximum drawdown ()
print(stats['strategy'][strategy]['max_drawdown'])


# In[17]:


# Maximum drawdown start and end
print(stats['strategy'][strategy]['drawdown_start'])
print(stats['strategy'][strategy]['drawdown_end'])


# In[18]:


# Get strategy comparison (only relevant if multiple strategies were compared)
print(stats['strategy_comparison'])


# In[19]:


# Load backtested trades as dataframe
trades = load_backtest_data(backtest_dir)

# Show value-counts per pair
trades.groupby("pair")["sell_reason"].value_counts()


# ## Plotting daily profit / equity line

# In[20]:


# Plotting equity line (starting with 0 on day 1 and adding daily profit for each backtested day)

from freqtrade.configuration import Configuration
from freqtrade.data.btanalysis import load_backtest_data, load_backtest_stats
import plotly.express as px
import pandas as pd

# strategy = 'SampleStrategy'
# config = Configuration.from_files(["user_data/config.json"])
backtest_dir = config["user_data_dir"] / "backtest_results"

stats = load_backtest_stats(backtest_dir)
strategy_stats = stats['strategy'][strategy]

dates = []
profits = []
for date_profit in strategy_stats['daily_profit']:
    dates.append(date_profit[0])
    profits.append(date_profit[1])

equity = 0
equity_daily = []
for daily_profit in profits:
    equity_daily.append(equity)
    equity += float(daily_profit)


df = pd.DataFrame({'dates': dates,'equity_daily': equity_daily})

fig = px.line(df, x="dates", y="equity_daily")
fig.show()


# ## Load live trading results into a pandas dataframe
# 
# In case you did already some trading and want to analyze your performance

# In[21]:


from freqtrade.data.btanalysis import load_trades_from_db

# Fetch trades from database
trades = load_trades_from_db("sqlite:///tradesv3.sqlite")

# Display results
trades.groupby("pair")["sell_reason"].value_counts()


# ## Analyze the loaded trades for trade parallelism
# 
# This can be useful to find the best max_open_trades parameter, when used with backtesting in conjunction with --disable-max-market-positions.
# 
# analyze_trade_parallelism() returns a timeseries dataframe with an "open_trades" column, specifying the number of open trades for each candle.

# In[29]:


from freqtrade.data.btanalysis import analyze_trade_parallelism

# Analyze the above
parallel_trades = analyze_trade_parallelism(trades, '5m')

parallel_trades.plot()


# ## Plot results
# 
# Freqtrade offers interactive plotting capabilities based on plotly.

# In[30]:


from freqtrade.plot.plotting import  generate_candlestick_graph
# Limit graph period to keep plotly quick and reactive

# Filter trades to one pair
trades_red = trades.loc[trades['pair'] == pair]

data_red = data['2019-06-01':'2019-06-10']
# Generate candlestick graph
graph = generate_candlestick_graph(pair=pair,
                                   data=data_red,
                                   trades=trades_red,
                                   indicators1=['sma20', 'ema50', 'ema55'],
                                   indicators2=['rsi', 'macd', 'macdsignal', 'macdhist']
                                  )


# In[31]:


# Show graph inline
# graph.show()

# Render graph in a separate window
graph.show(renderer="browser")


# ## Plot average profit per trade as distribution graph

# In[32]:


import plotly.figure_factory as ff

hist_data = [trades.profit_ratio]
group_labels = ['profit_ratio']  # name of the dataset

fig = ff.create_distplot(hist_data, group_labels,bin_size=0.01)
fig.show()


# In[ ]:




