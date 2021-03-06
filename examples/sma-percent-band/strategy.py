"""
stategy
---------
"""

# use future imports for python 3.x forward compatibility
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division
from __future__ import absolute_import

# other imports
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from talib.abstract import *

# project imports
import pinkfish as pf

pf.DEBUG = False

class Strategy():

    def __init__(self, symbol, capital, start, end, use_adj=False,
                 sma_period=200, percent_band=0):
        self._symbol = symbol
        self._capital = capital
        self._start = start
        self._end = end
        self._use_adj = use_adj
        self._sma_period = sma_period
        self._percent_band = percent_band/100

    def _algo(self):
        """ Algo:
            1. The SPY closes above its upper band, buy
            2. If the SPY closes below its lower band, sell your long position.
        """
        self._tlog.cash = self._capital

        for i, row in enumerate(self._ts.itertuples()):

            date = row.Index.to_pydatetime()
            high = row.high
            low = row.low
            close = row.close
            sma = row.sma
            sma200 = row.sma200
            upper_band = sma + sma * self._percent_band
            lower_band = sma - sma * self._percent_band
            upper_band200 = sma200 + sma200 * self._percent_band
            lower_band200 = sma200 - sma200 * self._percent_band
            end_flag = True if (i == len(self._ts) - 1) else False
            shares = 0

            # buy
            if (self._tlog.num_open_trades() == 0
                and ((close < upper_band200 and close > upper_band) or (close > upper_band200))
                and not end_flag):

                # enter buy in trade log
                shares = self._tlog.enter_trade(date, close)

            # sell
            elif (self._tlog.num_open_trades() > 0
                  and (close < lower_band200 and close < lower_band)
                  or end_flag):

                # enter sell in trade log
                shares = self._tlog.exit_trade(date, close)

            if shares > 0:
                pf.DBG("{0} BUY  {1} {2} @ {3:.2f}".format(
                       date, shares, self._symbol, close))
            elif shares < 0:
                pf.DBG("{0} SELL {1} {2} @ {3:.2f}".format(
                       date, -shares, self._symbol, close))

            # record daily balance
            self._dbal.append(date, high, low, close,
                              self._tlog.shares, self._tlog.cash)

    def run(self):
        self._ts = pf.fetch_timeseries(self._symbol)
        self._ts = pf.select_tradeperiod(self._ts, self._start,
                                         self._end, self._use_adj)       

        # Add technical indicator:  day sma
        sma = SMA(self._ts, timeperiod=self._sma_period)
        self._ts['sma'] = sma
        
        # Add technical indicator:  day sma
        sma200 = SMA(self._ts, timeperiod=200)
        self._ts['sma200'] = sma200
        
        self._ts, self._start = pf.finalize_timeseries(self._ts, self._start)

        self._tlog = pf.TradeLog()
        self._dbal = pf.DailyBal()

        self._algo()

    def get_logs(self):
        """ return DataFrames """
        self.rlog = self._tlog.get_log_raw()
        self.tlog = self._tlog.get_log()
        self.dbal = self._dbal.get_log(self.tlog)
        return self.rlog, self.tlog, self.dbal

    def get_stats(self):
        stats = pf.stats(self._ts, self.tlog, self.dbal, self._capital)
        return stats

def summary(strategies, *metrics):
    """ Stores stats summary in a DataFrame.
        stats() must be called before calling this function """
    index = []
    columns = strategies.index
    data = []
    # add metrics
    for metric in metrics:
        index.append(metric)
        data.append([strategy.stats[metric] for strategy in strategies])

    df = pd.DataFrame(data, columns=columns, index=index)
    return df
    
def plot_bar_graph(df, metric):
    """ Plot Bar Graph: Strategy
        stats() must be called before calling this function """
    df = df.loc[[metric]]
    df = df.transpose()
    fig = plt.figure()
    axes = fig.add_subplot(111, ylabel=metric)
    df.plot(kind='bar', ax=axes, legend=False)
    axes.set_xticklabels(df.index, rotation=0)
