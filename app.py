from urllib import request
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import *
import threading
import time
import math

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self,self)
        self.latest = 0

    def tickPrice(self, reqId, tickType, price, attrib):
        if tickType == 2 and reqId == 1:
            self.latest = price*100000

    def historicalData(self,reqId,bar):
            print(f'Time: {bar.date} Close: {bar.close}')

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextorderId = orderId
        # print('The next valid order id is: ', self.nextorderId)

    def orderStatus(self, orderId, status, filled, remaining, avgFullPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print('orderStatus - orderID:', orderId, 'status:', status, 'filled',filled,'remaining',remaining,'lastFillPrice',lastFillPrice)
    
    def openOrder(self, orderId, contract, order, orderState):
        print('openOrder id:',orderId,contract.symbol,contract.secType,'@',contract.exchange,':',order.action,order.orderType,order.totalQuantity,orderState.status)
    
    def execDetails(self, reqId, contract, execution):
        print('Order Executed: ', reqId, contract.symbol, contract.secType, contract.currency, execution.execId, execution.orderId, execution.shares, execution.lastLiquidity)
    
    def error(self, reqId, errorCode, errorString, test):
        if errorCode == 202:
            print('order canceled') 

class tracker:
    def __init__(self):
        self.quantity = 0
        self.avg_price = 0
        self.history = []
        self.step = 0
        self.first_entry_price = 0
        self.current_high = 0
        self.current_low = 0
    
    def add(self, quantity, price):
        if(len(self.history) == 0):
            self.first_entry_price == price
        record = {"id" : len(self.history) + 1, "quantity" : quantity, "price" : price}
        self.avg_price = round(((self.quantity*self.avg_price) + (quantity * price))/(self.quantity + quantity),5)
        self.quantity += quantity
        self.history.append(record)
        self.step += 1
        return {'status' : f'BOT {quantity} @ ${price} -> AVG. PRICE ${self.avg_price}'}
    
    def close(self, price):
        pnl = self.review(price)
        self.quantity = 0
        self.avg_price = 0
        self.history = []
        self.step = 0
        self.first_entry_price = 0
        self.current_high = 0
        self.current_low = 0
        return pnl

    def review(self, current_price):
        if current_price > self.avg_price:
            sign = "+"
            pnl = round((current_price - self.avg_price) * self.quantity, 5)
        else:
            sign = "-"
            pnl = round((self.avg_price - current_price) * self.quantity, 5)
        return({"status": f'PNL: {sign}{pnl} QTY:{self.quantity} AVG.PRICE:{self.avg_price} STEP:{self.step} FEP:{self.first_entry_price} CHIGH:{self.current_high} CLOW:{self.current_low}'})

    def reset(self):
        self.quantity = 0
        self.avg_price = 0
        self.history = []
        self.step = 0

class strategy:
    def __init__(self, initial_price):
        self.t = tracker()
        self.t.current_high = initial_price
        self.t.current_low = initial_price
        self.tp_alert = 0
        self.ae_alert = 0

        ##### ##### #####
        # SETTINGS
        ##### ##### #####
        self.tpm = [round(6/100000, 5),round(6/100000, 5), round(6/100000, 5), round(15/100000, 5), round(50/100000, 5), round(100/100000, 5), round(330/100000, 5)] # Take Profit Margin (TPM) in decimals.
        self.arm = round(1/100000,5) # Accepted Reversal Margin (ARM) in decimals.
        self.bel = [0, 5/100000, 20/100000, 65/100000, 135/100000, 625/100000, 3125/100000, 15625/100000, 50000/100000,1] # Bearish Entry Level (BEL) the percentage down target for opening additional positions.
        self.meu = [1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192] # Martingale Progression in Units (MEU) to calculate the amount to open for additional positions.

    def alignHighLow(self):
        self.t.current_high = self.t.avg_price
        self.t.current_low = self.t.avg_price

    def request_action(self, price):
        if((self.t.current_high - price) > self.t.current_high * self.arm and self.tp_alert == 1):
            self.tp_alert = 0
            self.ae_alert = 0
            self.t.current_high = 0
            return({"status": f'TP REVERSAL', "action" : 1})
        elif(price > self.t.avg_price*(1+self.tpm[self.t.step]+self.arm) and self.tp_alert == 1):
            self.tp_alert = 1
            self.ae_alert = 0
            self.t.current_high = price if price > self.t.current_high else self.t.current_high
            return({"status": f'TP ALERT FOLLOW', "action" : 0})
        elif(price > self.t.avg_price*(1+self.tpm[self.t.step]+self.arm) and self.tp_alert == 0):
            self.tp_alert = 1
            self.ae_alert = 0
            self.t.current_high = price if price > self.t.current_high else self.t.current_high
            return({"status": f'TP ALERT ON', "action" : 0})
        elif(price > self.t.current_low*(1+self.arm) and self.ae_alert == 1):
            self.ae_alert = 0
            self.tp_alert = 0
            self.t.current_low = 0
            return({"status": f'AE REVERSAL', "action" : 1})
        elif(price < self.t.avg_price*(1-self.bel[self.t.step]-self.arm) and self.ae_alert == 1):
            self.tp_alert = 0
            self.ae_alert = 1
            self.t.current_low = price if price < self.t.current_low else self.t.current_low
            return({"status": f'AE ALERT FOLLOW', "action" : 0})
        elif(price < self.t.avg_price*(1-self.bel[self.t.step]-self.arm) and self.ae_alert == 0):
            self.tp_alert = 0
            self.ae_alert = 1
            self.t.current_low = price if price < self.t.current_low else self.t.current_low
            return({"status": f'AE ALERT ON', "action" : 0})
        else:
            self.t.current_high = price if price > self.t.current_high else self.t.current_high
            self.t.current_low = price if price < self.t.current_low else self.t.current_low
            return({"status": f'WATCH', "action" : 0})

def run_loop():
    app.run()

def CRYPTO_contract(symbol):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = 'CRYPTO'
    contract.exchange = 'PAXOS'
    contract.currency = 'USD'
    return contract

def FX_contract(symbol):
	contract = Contract()
	contract.symbol = symbol[:3]
	contract.secType = 'CASH'
	contract.exchange = 'IDEALPRO'
	contract.currency = symbol[3:]
	return contract

def request_live_data(contract):
    app.reqMktData(1, contract, '', False, False, [])

def request_historical_data(contract):
    app.reqHistoricalData(1, contract, '', '2 D', '1 hour', 'BID', 0, 2, False, [])

def buy_order(cashOrQty, value):
    order = Order()
    order.action = 'BUY'
    order.orderType = 'MKT'
    order.tif = 'IOC'
    if(cashOrQty=="cash"):
        order.cashQty = value
    else:
        order.totalQuantity = value
    return order

def sell_order(cashOrQty, value):
    order = Order()
    order.action = 'SELL'
    order.orderType = 'MKT'
    order.tif = 'IOC'
    if(cashOrQty=="cash"):
        order.cashQty = value
    else:
        order.totalQuantity = value
    return order

app = IBapi()
app.connect('127.0.0.1', 7497, 100)
app.nextorderId = None
api_thread = threading.Thread(target=run_loop, daemon=True) # Start the socker in a thread
api_thread.start()
while True:
    if isinstance(app.nextorderId, int):
        print('connected')
        break
    else:
        print('waiting for connection')
        time.sleep(1)

# STREAM
current_symbol = "EURUSD"
app.reqMktData(1, FX_contract(current_symbol), '', False, False, [])
time.sleep(3)

# STRATEGY
s = strategy(app.latest)
initial_quantity = 95000
app.placeOrder(app.nextorderId, FX_contract(current_symbol), buy_order("qty", initial_quantity*s.meu[s.t.step]))
app.nextorderId += 1
s.t.add(initial_quantity, app.latest)

for x in range(1000000000):
    print(f'>>> {app.latest}')
    if(x%10 == 0):
        print(s.t.review(app.latest))
    resp = s.request_action(app.latest)
    print(resp)
    if(resp["status"] == 'AE REVERSAL' and resp["action"] == 1):
        app.placeOrder(app.nextorderId, FX_contract(current_symbol), buy_order("qty", initial_quantity*s.meu[s.t.step]))
        app.nextorderId += 1
        s.t.add(initial_quantity*s.meu[s.t.step], app.latest)
        s.alignHighLow()
    elif(resp["status"] == 'TP REVERSAL' and resp["action"] == 1):
        app.placeOrder(app.nextorderId, FX_contract(current_symbol), sell_order("qty", s.t.quantity))
        app.nextorderId += 1
        print(s.t.close(app.latest))
        time.sleep(2)
        app.placeOrder(app.nextorderId, FX_contract(current_symbol), buy_order("qty", initial_quantity*s.meu[s.t.step]))
        app.nextorderId += 1
        s.t.add(initial_quantity, app.latest)
    time.sleep(2)


time.sleep(10)
print('cancelling order')
app.cancelOrder(app.nextorderId,1)

time.sleep(3)
app.disconnect()