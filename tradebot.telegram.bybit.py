from datetime import datetime,timezone,timedelta
from telethon import TelegramClient, events, sync
import re
from pybit import HTTP
from pprint import pprint
import time
import timeit

#####################################################
# USAGE:
#
# python3 <script>.py
#
#####################################################
#
# _______________ VARIABLES_________________
#bybit
bbapi_key="XXXXXXXXXXXXXXXXXX"
bbapi_secret="XXXXXXXXXXXXXXXXXXXXXXXXX"

investment = 100  #amount of USDT to invest each trade
profitpct = 15 #profit % WITH leverage. 
stoplosspct = 50 #loss % WITH leverage.
leverage = 20

#telegram
tgapi_id = 111111
tgapi_hash = 'abcdefghijklmnopqrst3421ddas'
tgbotname = 'anon' #arbitrary name

tg_watchgroup = -1009999999 # channel number, fill as integer (without ' '), if string, with ''

#_________________ END VARABLES_________________

def now():
    #usage: now()
    #return datetime.now().strftime('%Y-%m-%d %H:%M:%S')    
    return datetime.now()

#bybit connection
bbclient = HTTP("https://api.bybit.com", api_key=bbapi_key, api_secret=bbapi_secret)

#pull all USDT symbols and create a list
linearsymbols = []
symbollist = []
linearsymbolslist = bbclient.query_symbol()
for i in linearsymbolslist['result']:
    if i['quote_currency'] == 'USDT':
        linearsymbols.append({'symbol':i['alias'], 'price_scale':i['price_scale'], 'qty_step':i['lot_size_filter']['qty_step']})
        symbollist.append(i['alias'])
    else:
        pass

#----------------- TG -------------------------------------------

tg_search = r'(?<=Short)' #inc 'r' for python regex.

tgclient = TelegramClient(tgbotname, tgapi_id, tgapi_hash)

print('\nScouting telegram channel', tg_watchgroup, 'for SHORT signals...')

@tgclient.on(events.NewMessage(chats=tg_watchgroup))
async def my_event_handler(event):
#    global symbol #define global variable outside this private space
#    global buy_price
    text = event.raw_text
    #print (text)
    match = re.findall(r'(^Short)', text) #match firstline and specific text
    if match:
        start = timeit.default_timer() #start timer.

        try:
               
            #print ("match: ")
            if match[0] == 'Short':
                side = 'Sell'
            else:
                side = 'Buy'

            coin = (re.findall("^(?:\S+\s){1}(\S+)", text)) # 1 = match 2nd item       
            # print (coin) 
            symbol = str(coin[0]).upper() + 'USDT'
            if symbol == "SHIBUSDT":
                symbol = "SHIB1000USDT" #bybit
            # print (symbol)
            print (f"{now()}: symbol '{symbol}' published") 

            if not symbol in symbollist:
                print (f"{now()}: symbol '{symbol}' not on Bybit")                
                print (f"{now()}: returning to scouting")
            else:
                buyprice = (re.findall("^(?:\S+\s){2}(\S+)", text)) # 2 = match 3rd item
                #print (buyprice[0])
                buyprice = str(buyprice[0]) # float to string for text replace
                #print (buyprice)
                buyprice = buyprice.replace(",", "") # replace , with nothing , is 1000 separator. 
                buyprice = float(buyprice)
                #print (f"buyprice: {buyprice}")

                for i in linearsymbols:
                    if i['symbol']== symbol:
                        pricescale = i['price_scale']
                        #print (f"price scale: {pricescale}")
                sellprice = buyprice/((profitpct/leverage)/100+1) # * is long, / is short
                #print (f"sellprice: {sellprice}")
                sellprice = (round(sellprice,pricescale))
                #print (f"sellprice pricescale: {sellprice}")

                stoplossprice = buyprice*((stoplosspct/leverage)/100+1) # * is long, / is short
                #print (f"stoplossprice: {stoplossprice}")
                stoplossprice = (round(stoplossprice,pricescale))
                #print (f"stoplossprice pricescale: {stoplossprice}")

                for i in linearsymbols:
                    if i['symbol']== symbol:
                        qtystep = i['qty_step']
                        #print (f"qty_step: {qtystep}")    
                qty = investment/buyprice*leverage
                #print (f"qty: {qty}")
                if qtystep >= 1:
                    roundvalue = 1
                else: 
                    roundvalue = 2
                qty = round(qty,(len(str(qtystep)))-roundvalue)
                #print (f"qtystep: {qty}")

                sum = round((qty*buyprice),2)
                print (f"{now()}: {match[0]} {symbol}: {qty} @ ${buyprice} = ${sum}; TP: ${sellprice}; stop: ${stoplossprice} (leverage:{leverage}, profitpct:{profitpct}%)"  )
                
                stop1 = timeit.default_timer()
                print(f"{now()}: Runtime.calc: {round(stop1 - start,3)} seconds") 

                try:
                    # set margin to isolated and set leverage BEFORE opening a order/position
                    # if this takes to long, pre set all symbols before scouting ?
                    result = (bbclient.cross_isolated_margin_switch(
                        symbol=symbol,
                        is_isolated=True,
                        buy_leverage=leverage,
                        sell_leverage=leverage
                        ))
                    print (f"{now()}: set isolated and leverage {leverage}: {result['ret_msg']}")
                except Exception as e:
                    print(f"{now()}: error in margin switch: {e}")    

                stop2 = timeit.default_timer()
                print(f"{now()}: Runtime.margin_switch.api: {round(stop2 - stop1,3)} seconds") 

                try:
                    buyorder = (bbclient.place_active_order(
                        symbol=symbol,
                        side=side,
                        order_type="Market",
                        qty=qty,
                        # price=buyprice, # No price set = MARKET buy order.
                        # https://help.bybit.com/hc/en-us/articles/360039749233-What-Are-Time-In-Force-TIF-GTC-IOC-FOK-
                        # https://bybit-exchange.github.io/docs/linear/#time-in-force-time_in_force
                        # https://help.bybit.com/hc/en-us/articles/360039749433-What-Is-A-Post-Only-Order-
                        time_in_force="FillOrKill", # note: PostOnly does no buy when price is lower than buyprice, it cancels if price is lower. 
                        reduce_only=False,
                        close_on_trigger=False,
                        take_profit=sellprice,
                        stop_loss=stoplossprice
                        ) )  
                    if buyorder['ret_code'] == 0 and buyorder['ext_code'] == "":            
                        print (f"{now()}: result buyorder: {buyorder['ret_msg']}")
                    else:
                        print (f"{now()}: error in buyorder: {buyorder}")
                except Exception as e:
                    print(f"{now()}: exception in buyorder: {e}")

                stop3 = timeit.default_timer()
                print(f"{now()}: Runtime.place_order.api: {round(stop3 - stop2,3)} seconds")  
            
                # #check if position is opened. on cancelled: break and stop.  if there, do sell order.
                # while True:
                #     try:
                #         if buyorder['ret_code']==0 and buyorder['ext_code']=="" :
                #             openorder = bbclient.get_active_order(symbol=symbol)
                #             if openorder['result']['data'] and openorder['result']['data']['order_status'] == 'New':
                #                 if side == "Sell":
                #                     side = "Buy"
                #                 else:
                #                     side = "Sell"
                            
                #                 sellorder = (bbclient.place_active_order(
                #                     symbol=symbol,
                #                     side=side,
                #                     order_type="Limit",
                #                     qty=qty,
                #                     price=sellprice,
                #                     # https://help.bybit.com/hc/en-us/articles/360039749233-What-Are-Time-In-Force-TIF-GTC-IOC-FOK-
                #                     # https://bybit-exchange.github.io/docs/linear/#time-in-force-time_in_force
                #                     # https://help.bybit.com/hc/en-us/articles/360039749433-What-Is-A-Post-Only-Order-
                #                     time_in_force="PostOnly",   
                #                     reduce_only=True,
                #                     close_on_trigger=True
                #                     ) )  
                #                 print (f"{now()}: result sellorder: {sellorder['ret_msg']}")
                #             else:
                #                 print (f"{now()}: positioncheck: position not there yet. Waiting 5s to retry.") # <-- doesnt work yet, always this one is hit.
                #                 #WHAT TO DO WHEN MULTIPLE SIGNALS ARE COMING IN?
                #                 time.sleep(5)
                #                 pass
                #         else:
                #             print (f"{now()}: buyorder error: {buyorder}") #NOTE: error for BUYorder, not sellorder  
                #     except Exception as e:
                #         print(f"{now()}: error in positioncheck: {e}")
                #     else:
                #         break #break out of loop when no error. 
             
                # stop4 = timeit.default_timer()
                # print(f"{now()}: Runtime.positioncheck and sellorder.api: {round(stop4 - stop3,3)} seconds")                    

            stop5 = timeit.default_timer()
            print(f"{now()}: Runtime.total: {round(stop5 - start,3)} seconds")  
                
        except Exception as e:
            print(f"{now()}: error somewhere in script: {e}")
            print(f"{now()}: returning to scouting.")  

tgclient.start()
tgclient.run_until_disconnected()
