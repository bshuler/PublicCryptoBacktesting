import getindicators as gi
import ExchangeFetch as ef
import os, time

# this function simply checks to see if the bot SHOULDNT place a long order
#if it finds that there is no reason not to, it returns a True
def goLong(row):
    if row['slow_k'] < 51 or row['slow_d'] < 51:  # stoch check
        return False

    if row['rsi'] < 53:
        return False

    if row['uo'] < 53:
        return False

    if row['DI+'] < row['DI-']:
        return False

    if row['macd'] < row['macd_signal']:
        return False

    if row['cci'] < 91:
        return False

    if row['Close'] < max(row['psar'], row['ma'], row['ST_10_3']):
        return False

    if row['dema'] < row['ema']:
        return False

    if row['mom'] < 21:
        return False

    if row['WT1.'] <= 0:
        return False

    if row['ppo'] <= 0:
        return False

    return True

# this function simply checks to see if the bot SHOULDNT place a short order
#if it finds that there is no reason not to, it returns a True
def goShort(row):
    if row['slow_k'] > 49 or row['slow_d'] > 49:  # stoch check
        return False

    if row['rsi'] > 47:
        return False

    if row['uo'] > 47:
        return False

    if row['DI+'] > row['DI-']:
        return False

    if row['macd'] > row['macd_signal']:
        return False

    if row['cci'] > -91:
        return False

    if row['Close'] > min(row['psar'], row['ma'], row['ST_10_3']):
        return False

    if row['dema'] > row['ema']:
        return False

    if row['mom'] > -21:
        return False

    if row['WT1.'] > 0:
        return False

    if row['ppo'] >= 0:
        return False

    return True

#this is actually the trading bot, it chooses to go long, go short, or to bail out of a current order
def longOrShort(row):
    global lastorder
    global startOrders
    global rowTrigger
    global oldPrice
    global safetyloss
    global leverage

#first, check that enough time has passed before it places ANY trade
    if row['Date'] == rowTrigger:           #first check that enough time has passed for indicators to be valid
        startOrders = True
    else:
        if startOrders == False:
            row['order'] = 'PASS'
            return row

    if startOrders == True:  #if we are good to go trading...

        # kill the order we have if the order is in the red by "safetyloss" leveraged percent
        if lastorder in  ['LONG','SHORT']:  # if our order is LONG., check if we have dropped in price by a negative safetyloss amount
            loss=row['Close'] - oldPrice / oldPrice * leverage

            if ( lastorder == 'LONG' and loss < -1 * safetyloss) or \
                ( lastorder == 'SHORT' and loss > safetyloss):
                lastorder = 'PASS'          #indicate that we are switching to no order at all
                row['order'] = 'PASS'       #record this choice in dataframe
                oldPrice = row['Close']     #record the price at which this happened
                return row

# now check if we should go long or short

        if goLong(row):  #if we should go long, record the long order
            row['order'] = 'LONG'
            if lastorder == 'LONG':
                return row
            lastorder = "LONG"      #this only happens if the previous state was NOT long
            oldPrice=row['Close']
            return row

        if goShort(row):
            row['order'] = 'SHORT'
            if lastorder == 'SHORT':
                return row
            lastorder = "SHORT"
            oldPrice = row['Close']
            return row

    row['order'] = lastorder  #if no change in order is requested, just hold the same order
    return row


#once the bot has recorded its actions, time to calculate profits!

def calculateBalance(row):
    global balance
    global oldPrice
    global leverage
    global lastorder

    percentchange = 0
    diff = 0

    if row['order'] == 'PASS':  # need calculate diff we are moving from a position into PASS,
        if lastorder == 'SHORT':
            diff = oldPrice-row['Close']
        if lastorder == 'LONG':
            diff = row['Close'] - oldPrice   #if last order was PASS, then the diff and %change are 0
        percentchange = diff / oldPrice * leverage
        lastorder = 'PASS'
        oldPrice = row['Close']

    elif row['order'] == 'SHORT':  # calculate balance if moved to a short position
        if lastorder == 'PASS':
            oldPrice = row['Close']     #if the was no order, the start a new short, recor dprice
        if lastorder == 'LONG':     #if we were long, close it out, record %change in balance
            diff = row['Close'] - oldPrice
            percentchange = diff / oldPrice * leverage
            oldPrice = row['Close']
        lastorder='SHORT'           #remember that we created a short position when evaluating next row

    elif row['order'] == 'LONG':
        if lastorder == 'PASS':
            oldPrice = row['Close']
        if lastorder == 'SHORT':
            diff = oldPrice - row['Close']
            percentchange = diff / oldPrice * leverage
            oldPrice = row['Close']
        lastorder='LONG'

    balance = percentchange * balance + balance  #modify balance based on %change in balance when closing a position
    row['balance'] = balance                     #record the balance in dataframe row
    return row


#Main Routine
# ================================
#globals
lastorder = 'PASS'
startOrders = False
rowTrigger = ""
balance = 10000
leverage = 5
safetyloss = 0.2

#file name construction
exchange = 'bitfinex'
timeframe = '1h'
base = 'USD'
cfStartDate = "2019-11-01"
candlefile = exchange + timeframe + base + cfStartDate+'.csv'


#make a new candlefile if one does not exist or it is too old
try:
    f = open(candlefile)
    fileage = time.time() - os.path.getmtime(candlefile)  # get age of file in seconds (later just addend to file)
    if fileage > 3600:  # if the candle file is old, make another)
        ef.scrape_candles_to_csv(candlefile, exchange, 3, 'BTC/' + base, timeframe, cfStartDate+'T00:00:00Z', 100)
except FileNotFoundError:  # if the candlefile doesnt exist, make one
    ef.scrape_candles_to_csv(candlefile, exchange, 3, 'BTC/' + base, timeframe, cfStartDate+'T00:00:00Z', 100)
    f = open(candlefile)
finally:
    f.close()

print("Creating Indicator array...")
df = gi.indicatorDF(candlefile, timeframe)

rowTrigger = df.iloc[60]['Date']
oldPrice = df.iloc[60]['Close']

print("Backtesting...")
df = df.apply(longOrShort, axis=1)

lastorder = 'PASS'

print("calculating returns...")
df = df.apply(calculateBalance, axis=1)

export_csv = df.to_csv(r'orders6-' + candlefile, index=None, header=True)
