import os
import sys
module_path = os.path.abspath(os.path.join('..'))
if module_path not in sys.path:
    sys.path.append(module_path)
module_path = os.path.abspath(os.path.join('indicators'))
if module_path not in sys.path:
    sys.path.append(module_path)


from ttrpy.trend.sma import sma
from ttrpy.trend.dema import dema
from ttrpy.trend.ema import ema
#from ttrpy.trend.macd import macd
from ttrpy.momentum.stoch import stoch
from ttrpy.momentum.mom import mom
from ttrpy.momentum.ppo import ppo

from indicators import SuperTrend
from indicators import ATR
from finta import TA
import ta

import time

import pandas as pd
import warnings
from constants import *

def indicatorDF(candlefile,timeframe):
    pd.set_option('display.max_columns', None)
    warnings.simplefilter("ignore")

    df = pd.read_csv(candlefile)

    df = df.rename(columns={
        'date': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    })

    df['Timestamp'] = pd.to_datetime(df['Date']*1000000)
    #df = df[df['Date']>1572566400*1000]


    df = sma(df, 'Close', 'ma', iParams['SMAWINDOW']['val'])
    df = dema(df, 'Close', 'dema', iParams['DEMAWINDOW']['val'])
    df = ema(df, 'Close', 'ema', iParams['EMAWINDOW']['val'])
    #df = macd(df, 'Close', 'macd', iParams['MACDFAST']['val'],iParams['MACDSLOW']['val'],iParams['MACDSIGNAL']['val'])

    indicator_psar = ta.trend.PSARIndicator(high=df['High'], low=df['Low'], close=df['Close'],
                                            step=iParams['PSARAF']['val'], max_step=iParams['PSARMAX']['val'])
    df['psar'] = indicator_psar.psar()

    df = SuperTrend(df=df, period=iParams['STPERIOD']['val'], multiplier=iParams['STMULTIPLIER']['val'])
    df = ATR(df=df, period=iParams['ATRWINDOW']['val'])

    df = stoch(df=df, high='High', low='Low', close='Close', fast_k_n=iParams['STOCHFAST']['val'],
               slow_k_n=iParams['STOCHSLOWK']['val'], slow_d_n=iParams['STOCHSLOWD']['val'])

    df.rename(columns={'slow_%k': 'slow_k', 'slow_%d': 'slow_d'}, inplace=True)

    indicator_rsi = ta.momentum.RSIIndicator(close=df['Close'], n=iParams['RSIWINDOW']['val'])
    df['rsi'] = indicator_rsi.rsi()

    indicator_uo = ta.momentum.UltimateOscillator(high=df['High'], low=df['Low'], close=df['Close'],
                                                  s=iParams['UOS']['val'], m=iParams['UOM']['val'],
                                                  len=iParams['UOWINDOW']['val'])
    df['uo'] = indicator_uo.uo()

    indicator_macd = ta.trend.MACD(close=df['Close'], n_fast=iParams['MACDFAST']['val'],
                                   n_slow=iParams['MACDSLOW']['val'], n_sign=iParams['MACDSIG']['val'])

    df['macd'] = indicator_macd.macd()
    df['macd_diff'] = indicator_macd.macd_diff()
    df['macd_signal'] = indicator_macd.macd_signal()

    df = mom(df, 'Close', 'mom', iParams['MOMWINDOW']['val'])


    indicator_adx = ta.trend.ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], n=iParams['ADXWINDOW']['val'])
    df['adx'] = indicator_adx.adx()
    df['DI-'] = indicator_adx.adx_neg()
    df['DI+'] = indicator_adx.adx_pos()

    df.rename(columns={'Close': 'close', 'High': 'high', 'Low': 'low'}, inplace=True)

    df = pd.concat([df, TA.WTO(ohlc=df, channel_lenght=iParams['WTO_CHANNEL_LENGTH']['val'],
                               average_lenght=iParams['WTO_AVERAGE_LENGTH']['val'])], axis=1)
    df.rename(columns={'close': 'Close', 'high': 'High', 'low': 'Low'}, inplace=True)

    df = ppo(df, 'Close', 'ppo', fast_period=iParams['PPOFAST']['val'],
             slow_period=iParams['PPOSLOW']['val'], ma_type=0)

    indicator_cci = ta.trend.CCIIndicator(high=df['High'], low=df['Low'], close=df['Close'],
                                          n=iParams['CCIWINDOW']['val'], c=iParams['CCIcoeff']['val'])
    df['cci'] = indicator_cci.cci()


    df['Date'] = pd.to_datetime(df['Date']/1000,unit='s')   #kill off the microseconds

    timestamp_index = pd.DatetimeIndex(df['Date'].values)
    df = df.set_index(timestamp_index)

    export_csv = df.to_csv(r'indicators-'+candlefile, index=None, header=True)

    return df

