import json

import httplib2
import os
import logging

from apiclient.discovery import build
from datetime import date, timedelta
from nsepy import get_history
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
import webbrowser
import requests


log = logging.getLogger('pynse')
log.setLevel(logging.DEBUG)
fh = logging.FileHandler('./pynse.log', mode='a')
fm = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
fh.setFormatter(fm)
log.addHandler(fh)

symbols = {
    'NIFTY 50': ['YESBANK', 'HINDPETRO', 'IBULHSGFIN', 'ADANIPORTS', 'ASIANPAINT', 'BPCL', 'HEROMOTOCO', 'SUNPHARMA', 'MARUTI',
                 'IOC', 'TECHM', 'HINDUNILVR', 'UPL', 'POWERGRID', 'BAJAJFINSV', 'GRASIM', 'BAJFINANCE', 'INDUSINDBK', 'ULTRACEMCO',
                 'AXISBANK', 'ZEEL', 'COALINDIA', 'HDFC', 'ICICIBANK', 'KOTAKBANK', 'M&M', 'LT', 'BAJAJ-AUTO', 'INFRATEL', 'VEDL', 'TATAMOTORS',
                 'HCLTECH', 'WIPRO', 'NTPC', 'ONGC', 'TITAN', 'HDFCBANK', 'EICHERMOT', 'SBIN', 'CIPLA', 'ITC', 'JSWSTEEL', 'TATASTEEL', 'RELIANCE',
                 'TCS', 'GAIL', 'DRREDDY', 'HINDALCO', 'INFY', 'BHARTIARTL'],
    'NIFTY NEXT 50': ['NIACL', 'MCDOWELL-N', 'HAVELLS', 'NHPC', 'SHREECEM', 'LUPIN', 'BRITANNIA', 'ASHOKLEY',
                      'SBILIFE', 'MARICO', 'GODREJCP', 'OIL', 'ABCAPITAL', 'DABUR', 'ABB', 'HINDZINC', 'DMART', 'SAIL', 'COLPAL', 'PEL',
                      'SRTRANSFIN', 'SUNTV', 'GICRE', 'HDFCLIFE', 'LICHSGFIN', 'OFSS', 'CADILAHC', 'AMBUJACEM', 'BOSCHLTD', 'BANDHANBNK',
                      'PIDILITIND', 'PGHH', 'MRF', 'BHEL', 'DLF', 'BANKBARODA', 'AUROPHARMA', 'ACC', 'BIOCON', 'L&TFH', 'ICICIPRULI',
                      'ICICIGI', 'PETRONET', 'MOTHERSUMI', 'BEL', 'CONCOR', 'NMDC', 'INDIGO', 'IDEA', 'SIEMENS']
}

all_symbols = {"NSE_PREFERRED_STOCKS": sum(symbols.values(), [])}
all_indexs = symbols.keys()

test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
if not os.path.exists(test_dir): os.mkdir(test_dir)

script = '''
<button id="%s-custom-button">%s basket</button>
<script src="https://kite.trade/publisher.js?v=3"></script>
<script> \
KiteConnect.ready(function() {\
    var kite_%s = new KiteConnect("boep6ejamtjwewge");\
    %s\
    kite_%s.finished(function(status, request_token) {\
        alert("Finished. Status is " + status);\
    });\
    kite_%s.renderButton("#default-button");\
    kite_%s.link("#%s-custom-button");\
});\
</script>'''

kite_html_buttom = '''<kite-button href="#" \
        data-kite="boep6ejamtjwewge" \
        data-exchange="NSE" \
        data-tradingsymbol=%s \
        data-transaction_type=%s \
        data-quantity=%d \
        data-order_type="SL" \
        data-price=%d \
        data-trigger_price=%d \
        data-product="MIS" \
        data-stoploss=%d \
        data-squareoff=%d \
        data-trailing_stoploss=%s\
        >Buy %s stock</kite-button>'''


def js_script(type, data):
    """
    :param type: Trading type
    :param data: dict of order time
    :return:
    """
    button_scripts = list()
    kite_buttons_capcity =50
    buttons = round(len(data)/kite_buttons_capcity + 1)
    for x in range(buttons):
        data_str = str()
        real_index = x+1
        button_items = data[(real_index-1)*kite_buttons_capcity: real_index*kite_buttons_capcity]
        button_name = '{}_{}'.format(type,real_index)
        for trx in button_items:
            data_str = data_str + 'kite_{}.add({}); '.format(button_name, json.dumps(trx))
        button_scripts.append(script % (button_name, button_name, button_name, data_str, button_name, button_name, button_name, button_name))
    return button_scripts


def get_order_item(trade_direction, sym, trigger_price, qantity, profit_margin=0.0, stoploss_margin=0.0, product="MIS", variety="bo"):
    """
    :param trade_direction: Trading type
    :param sym: symbol
    :param price: trading/trigger price
    :param qantity: quantity of stocks
    :param profit_margin: profit margin
    :param stoploss_margin: stoploss margin
    :return:
    """
    sqoff = round_off((trigger_price * profit_margin) / 100)
    stoploss = round_off((trigger_price * stoploss_margin) / 100)
    trailing_stoploss = round_off(stoploss * tsl) if product == "MIS" else 0
    order_item = {
        "tradingsymbol": sym,
        "exchange": "NSE",
        "transaction_type": trade_direction,
        "order_type": "SL",
        "product": product,
        "price": trigger_price,
        "trigger_price": trigger_price,
        "quantity": qantity,
        "variety": variety,
        "stoploss": stoploss,
        "squareoff": sqoff,
        "trailing_stoploss": trailing_stoploss
    }
    return order_item


def get_html_button(sym, type, price, quantity, profit_margin=0.0, stoploss_margin=0.0):
    """
    :param sym: symbol
    :param type: BUY/SELL
    :param price: trading/trigger price
    :param qantity: quantity of stocks
    :param profit_margin: profit margin
    :param stoploss_margin: stoploss margin
    :return:
    """
    sqoff = round_off((price * profit_margin) / 100)
    stoploss = round_off((price * stoploss_margin) / 100)
    trailing_sl = round_off(stoploss * tsl)
    btn = kite_html_buttom % (sym, type, quantity, price, price, stoploss, sqoff, trailing_sl, sym)
    return btn


def get_credentials():
    scope = 'https://www.googleapis.com/auth/blogger'
    flow = flow_from_clientsecrets(
        'conf/client_id.json', scope,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    storage = Storage('conf/credentials.dat')
    credentials = storage.get()
    if not credentials or credentials.invalid:
        auth_uri = flow.step1_get_authorize_url()
        webbrowser.open(auth_uri)
        auth_code = input('Enter the auth code: ')
        credentials = flow.step2_exchange(auth_code)
        storage.put(credentials)
    return credentials


def get_service():
    """Returns an authorised blogger api service."""
    credentials = get_credentials()
    http = httplib2.Http()
    http = credentials.authorize(http)
    service = build('blogger', 'v3', http=http)
    return service


def blogger_create_post(type, index=None, pick_day=None, suggested_day=None, content_file=None):
    """
    :param type: type of post
    :param index: stock index
    :param pick_day: trading day
    :param suggested_day: suggested day
    :return:
    """
    foot_note = "\nNote: All the above content is for educational purpose, \n" \
                "\nDo your home work before considering above content, " \
                "not recommended to try without knowledge (try at your own risk)."

    if type == 'nr_pick':
        title = '{} NR7 - Narrow day Range 7 stock pick as of {}'.format(index, str(pick_day))
    elif type == 'nr_pick_analysis':
        title = '{} NR7 - Narrow day Range 7 stock pick analysis for stocks suggested on {}'.format(index, str(suggested_day))
    elif type == 'oh_ol_pick':
        title = 'OH_OL - OPEN HIGH OPEN LOW stock pick as of {}'.format(str(pick_day))
    elif type == 'oh_ol_pick_analysis':
        title = 'OH_OL - OPEN HIGH OPEN LOW stock pick analysis as of {}'.format(str(suggested_day))

    content_file = content_file
    content = open(content_file, "r").read().replace('\n', '<br />')

    if os.stat(content_file).st_size == 0:
        log.info("No content for post: {}".format(title))
        return
    else:
        content = content + break_item() + foot_note
    if not title in post_titles:
        body = {
            "kind": "blogger#post",
            "title": title,
            "content": content
        }
        posts.insert(blogId=blog_id, body=body, isDraft=False).execute()
        log.info("created post: {}".format(title))
    else:
        log.info("post already exists: {}".format(title))


def html_bold(content):
    return '<b>{}</b>'.format(content)


def html_h2(content):
    return '<h2>{}</h2>'.format(content)


def break_item():
    return '<div><b>\n=======================================</b></div>'


def round_off(value, precison=2):
    return round(value, precison)


def nr_fetch_data(index, day):

    str_day = str(day)

    log.info("As of {}, fetching data".format(day))

    nr_picks = list()
    oh_ol_picks = list()
    picks_data = dict()

    if os.path.exists(nr_pick_file):
        with open(nr_pick_file, 'r') as data_file:
            if os.stat(nr_pick_file).st_size != 0:
                picks_data = json.load(data_file)

    picks_data.keys()
    if picks_data.get(str_day + '_nr_picks_' + index) and picks_data.get(str_day + '_oh_ol_picks_' + index):
        log.info("There is picks data for this date {}, \n"
              "nr_pick_data: {} \n"
              "oh_ol_pick_data: {}".format(day, picks_data[str_day + '_nr_picks_' + index], picks_data[str_day + '_oh_ol_picks_' + index]))
        return

    for sym in all_symbols[index]:

        sym = sym.upper()

        # SYMBOL DATA FILE, SAVES EVERYDAY DATA
        sym_file = os.path.join(test_dir, '{}.json'.format(sym))
        sym_data = dict()

        if os.path.exists(sym_file):
            with open(sym_file, 'r') as data_file:
                if os.stat(sym_file).st_size != 0:
                    sym_data = json.load(data_file)

        # SKIP IF DATA ALREADY EXISTS FOR THAT DAY
        if str_day in sym_data.keys():
            log.info("There is stats for this date {}, symbol {}, , data: {}".format(str_day, sym, sym_data[str_day]))
            if sym_data[str_day]['nr_pick']: nr_picks.append(sym)
            if sym_data[str_day]['oh_ol_pick']: oh_ol_picks.append(sym)
            continue

        # GET HISTORY OF SYMBOL
        sym_history = history(symbol=sym, start_day=today - nr_range, end_day=today)

        if day not in sym_history['Open'].keys():
            log.info("\ndata is not available for {} on this {}".format(sym, day))
            continue

        if len(sym_history):
            nr = sym_history['High'] - sym_history['Low']
            nr_data = nr.to_dict()
        else:
            log.info("\n{} seems to be incorrect".format(sym))
            continue

        # SYMBOL STATS FOR THE DAY
        day_open_price = sym_history['Open'][day]
        day_high_price = sym_history['High'][day]
        day_low_price = sym_history['Low'][day]
        day_close_price = sym_history['Close'][day]


        # ANALYSE IF IT IS A NR PICK
        if not set(last_seven_trading_days).issubset(set(nr_data.keys())):
            log.info("{} doesnot match with last 7 std trading days as \nstd:{} \n actual: {}".format(sym, last_seven_trading_days, nr_data.keys()))
            continue

        if day in nr_data.keys():
            last_day_price_range = round_off(nr_data[day])
            last_seven_days_range = [round_off(nr_data[d]) for d in last_seven_trading_days]
        else:
            log.info("\n{} does not have data as of {}".format(sym, str_day))
            continue

        log.info("last day range = {}".format(last_day_price_range))
        log.info("last_seven_days_range = {}".format(last_seven_days_range))
        if last_day_price_range == min(last_seven_days_range):
            log.info("I am NR pick {} on {}".format(sym, day))
            nr_picks.append(sym)
            nr_pick_status = True
        else:
            nr_pick_status = False

        # ANALYSE IF IT IS A OH_OL PICK
        if day_open_price in [day_high_price, day_low_price]:
            oh_ol_picks.append(sym)
            oh_ol_pick_status = True
        else:
            oh_ol_pick_status = False

        # SUMMARY
        sym_data.update({str_day: {'high': sym_history['High'][day],
                                    'low': sym_history['Low'][day],
                                    'open': sym_history['Open'][day],
                                    'close': sym_history['Close'][day],
                                    'nr_pick': nr_pick_status,
                                    'oh_ol_pick': oh_ol_pick_status}})

        with open(sym_file, 'w') as fp:
            try:
                json.dump(sym_data, fp, indent=4)
            except Exception:
                log.info("with {}: {}".format(sym, Exception))

    picks_data.update({str_day + '_nr_picks_' + index : nr_picks})
    picks_data.update({str_day + '_oh_ol_picks_' + index : oh_ol_picks})
    with open(nr_pick_file, 'w') as fp:
        json.dump(picks_data, fp, indent=4)


def nr_pick(index, day):

    content_file = os.path.join(test_dir, '{}_nr_pick_post.txt'.format(index))
    nr_pick_post = open(os.path.join(test_dir, '{}_nr_pick_post.txt'.format(index)), 'w')
    nr_picks = dict()
    if os.path.exists(nr_pick_file):
        with open(nr_pick_file, 'r') as data_file:
            if os.stat(nr_pick_file).st_size != 0:
                nr_picks = json.load(data_file)
    else:
        return

    try:
        picks = nr_picks[str(day) + '_nr_picks_' + index]
    except KeyError as e:
        log.info("{} Looks data not available or key is incorrect, more info: {}".format(nr_pick.__name__, e.message))
        return

    if not picks:
        nr_pick_post.write("\n")
        nr_pick_post.write(html_bold("\n{} NR PICKS : None of the stocks under this index looks to be NR7 pick.".format(index)))
    else:
        nr_pick_post.write(html_bold("\n{} NR PICKS : {}.\n".format(index, ", ".join(picks))))
        nr_pick_post.write("\nKeep an eye on these stocks, find the below key points for more information")

    buy_all_with_no_limits = list()
    sell_all_with_no_limits = list()

    buy_all_low_target_high_risk = list()
    sell_all_low_target_high_risk = list()

    btst_orders = list()
    funds = list()

    for ind, sym in enumerate(picks):

        if ind == 1:
            nr_pick_post.write("<!--more--><br />")

        sym = sym.upper()
        sym_file = os.path.join(test_dir, '{}.json'.format(sym))
        sym_data = dict()

        with open(sym_file, 'r') as data_file:
            if os.stat(sym_file).st_size != 0:
                sym_data = json.load(data_file)
        nr_pick_post.write(html_h2(html_bold("\n{} looks to be a nr7 pick".format(sym))))

        # GET PRICES
        sugg_high = sym_data[day]['high']
        sugg_low = sym_data[day]['low']

        # HTML BUTTONS
        nr_pick_post.write("\nBuy  : {}, if it goes above {}".format(sym, sugg_high))
        nr_pick_post.write(get_html_button(sym, "BUY", sugg_high, 10, profit_margin=profit_margin_quick, stoploss_margin=sl_margin_quick))

        nr_pick_post.write("\nSell : {}, if it goes below {}".format(sym, sugg_low))
        nr_pick_post.write(get_html_button(sym, "SELL", sugg_low, 10, profit_margin=profit_margin_quick, stoploss_margin=sl_margin_quick))

        for profit_margin, quantity, sl_margin in profit_margin_with_quantity:

            # COLLECT ORDERS FOR JS
            buy_all_with_no_limits.append(get_order_item("BUY", sym, sugg_high, quantity, stoploss_margin=sl_margin))
            buy_all_low_target_high_risk.append(get_order_item("BUY", sym, sugg_high, quantity, profit_margin=profit_margin, stoploss_margin=sl_margin))

            sell_all_with_no_limits.append(get_order_item("SELL", sym, sugg_low, quantity, stoploss_margin=sl_margin))
            sell_all_low_target_high_risk.append(get_order_item("SELL", sym, sugg_low, quantity, profit_margin=profit_margin, stoploss_margin=sl_margin))

            funds.append((quantity * sugg_high * (profit_margin + sl_margin)) / 100)

        btst_orders.append(get_order_item("BUY", sym, sugg_high, 1, product="CNC", variety="regular"))

        nr_pick_post.write(break_item())

    if picks:
        for button in js_script('TRADE_WITH_LIMITS_WITH_HIGH_RISK', buy_all_low_target_high_risk + sell_all_low_target_high_risk): nr_pick_post.write(button)
        for button in js_script('TRADE_WITH_NO_LIMITS', sell_all_with_no_limits + buy_all_with_no_limits): nr_pick_post.write(button)
        for button in js_script('BTST_ORDERS', btst_orders): nr_pick_post.write(button)
        nr_pick_post.write(html_bold('FUNDS REQUIRED FOR TRADE_WITH_LIMITS_WITH_HIGH_RISK WOULB BE {}\n\n'.format(10 * round_off(sum(funds)))))
        nr_pick_post.write(html_bold('ABOVE MENTIONED FUNDS IS JUST A CALCULATION, WHICH IS JUST AN ESTIMATION BASED ON AUTHOR KNOWLEDGE.\n\n'))
        nr_pick_post.write(html_bold('ABOVE MENTIONED SUGGESTIONS IS UPTO AUTHOR KNOWLEDGE, PLEASE REACH OUT IF ANY CORRECTIONS TO BE DONE.\n\n'))
    nr_pick_post.close()
    blogger_create_post('nr_pick', index, pick_day=day, content_file=content_file)


def nr_pick_analysis(index, analysis_day, suggested_day):

    content_file = os.path.join(test_dir, '{}_nr_pick_analysis_post.txt'.format(index))
    nr_pick_analysis_post = open(content_file, 'w')
    nr_picks = dict()
    profit = 0
    loss = 0

    if os.path.exists(nr_pick_file):
        with open(nr_pick_file, 'r') as data_file:
            if os.stat(nr_pick_file).st_size != 0:
                nr_picks = json.load(data_file)
    else:
        return

    try:
        picks = nr_picks[str(suggested_day) + '_nr_picks_' + index]
    except KeyError as e:
        log.info("{} Looks data not available or key is incorrect, more info: {}".format(nr_pick_analysis.__name__, e.message))
        return

    if picks:
        nr_pick_analysis_post.write("{} NR PICKS suggested on {}: {}".format(index, suggested_day, ", ".join(picks)))
    for ind, sym in enumerate(picks):

        if ind == 1:
            nr_pick_analysis_post.write("<!--more--><br />")
        sym = sym.upper()
        sym_file = os.path.join(test_dir, '{}.json'.format(sym))
        sym_data = dict()

        with open(sym_file, 'r') as data_file:
            if os.stat(sym_file).st_size != 0:
                sym_data = json.load(data_file)

        suggested_high = sym_data[suggested_day]['high']
        suggested_low = sym_data[suggested_day]['low']

        actual_high = sym_data[analysis_day]['high']
        actual_low = sym_data[analysis_day]['low']
        actual_close = sym_data[analysis_day]['close']

        nr_pick_analysis_post.write(html_h2(html_bold("\n{} was previous day [{}] nr pick\n".format(sym, str(suggested_day)))))
        nr_pick_analysis_post.write(html_bold("\nKey points from yesterday for {}:".format(sym)))
        nr_pick_analysis_post.write("\n{} was Buy  : if it goes above {}".format(sym, suggested_high))
        nr_pick_analysis_post.write("\n{} was Sell : if it goes below {}".format(sym, suggested_low))
        nr_pick_analysis_post.write("\n")

        buy_trend = actual_high > suggested_high
        sell_trend = actual_low < suggested_low

        expected_buy_sq_off = suggested_high + ((suggested_high * profit_margin_quick)/100)
        expected_sell_sq_off = suggested_low - ((suggested_low * profit_margin_quick)/100)

        expected_buy_sl = (suggested_high * sl_margin_quick)/100
        expected_sell_sl = (suggested_low * sl_margin_quick)/100

        if buy_trend and expected_buy_sq_off < actual_high:
            buy_profit_in_amount = expected_buy_sq_off - suggested_high
        elif buy_trend and expected_buy_sq_off >= actual_high:
            buy_profit_in_amount = actual_high - suggested_high

        if sell_trend and expected_sell_sq_off > actual_low:
            sell_profit_in_amount = suggested_low - expected_sell_sq_off
        elif sell_trend and expected_sell_sq_off <= actual_low:
            sell_profit_in_amount = suggested_low - actual_low

        buy_loss_in_amount = suggested_high - actual_close if actual_close < suggested_high and expected_buy_sq_off > actual_high else 0
        sell_loss_in_amount = actual_close - suggested_low if actual_close > suggested_low and expected_sell_sq_off < actual_low else 0

        buy_profit = round_off((actual_high - suggested_high)/suggested_high, 3) * 100
        sell_profit = round_off((suggested_low - actual_low)/suggested_low, 3) * 100


        if buy_trend and sell_trend:
            nr_pick_analysis_post.write("\nTrend was not so clear, looks nr7 dint workout")
            nr_pick_analysis_post.write("\n{} made new high {} than nr high {}".format(sym, actual_high, suggested_high))
            nr_pick_analysis_post.write("\nThere was chance of making {} % of profit if you placed order on buy side".format(buy_profit))
            nr_pick_analysis_post.write("\nAlso")
            nr_pick_analysis_post.write("\n{} made new low {} than nr low {}".format(sym, actual_low, suggested_low))
            nr_pick_analysis_post.write("\nThere was chance of making {} % of profit if you placed order on sell side".format(sell_profit))
            loss = loss + min(buy_loss_in_amount, expected_buy_sl)
            loss = loss + min(sell_loss_in_amount, expected_sell_sl)
        elif buy_trend:
            nr_pick_analysis_post.write("\nTrend was on buy side, made new high {} than nr high {} and closed at {}".format(actual_high, suggested_high, actual_close))
            nr_pick_analysis_post.write("\nThere was chance of making {} % of profit".format(buy_profit))
            profit = profit + buy_profit_in_amount
        elif sell_trend:
            nr_pick_analysis_post.write("\nTrend was on sell side, making new low {} than nr low {} and closed at {}".format(actual_low, suggested_low, actual_close))
            nr_pick_analysis_post.write("\nThere was chance of making {} % of profit".format(sell_profit))
            nr_pick_analysis_post.write("\n")
            profit = profit + sell_profit_in_amount
        else:
            nr_pick_analysis_post.write("\nTrend was not so clear, looks nr7 dint workout")
            nr_pick_analysis_post.write("\n{} din't go above {}, stuck below {}".format(sym, suggested_high, actual_high))
            nr_pick_analysis_post.write("\n{} din't go below {}, stuck above {}".format(sym, suggested_low, actual_low))
            nr_pick_analysis_post.write("\nLooks like, this stock {} gonna be nr pick for next day".format(sym))

        nr_pick_analysis_post.write(break_item())

    pls = "\nIF YOU GOT A CHANCE TO EXECUTE ALL POSSIBLE TRADES\n" \
          "EACH QUANTITY WITH TRADE_BOTH_WITH_LIMITS_WITH_HIGH_RISK BUTTON, \n" \
          "THEN \n " \
          "1. PROFIT AMOUNT WOULD HAVE BEEN {}\n " \
          "2. LOSS AMOUNT WOULD HAVE BEEN {}".format(profit, loss)

    log.info(pls)

    nr_pick_analysis_post.write(pls)
    nr_pick_analysis_post.write(break_item())
    nr_pick_analysis_post.close()
    blogger_create_post('nr_pick_analysis', index, pick_day=analysis_day, suggested_day=suggested_day, content_file=content_file)


def ol_oh(day):

    content_file = os.path.join(test_dir, 'oh_ol_pick_post.txt')
    ol_oh_pick_post = open(content_file, 'w')

    if os.path.exists(nr_pick_file):
        with open(nr_pick_file, 'r') as data_file:
            if os.stat(nr_pick_file).st_size != 0:
                picks_data = json.load(data_file)

    for index in all_indexs:
        ol_oh_picks = picks_data.get(str(day) + '_oh_ol_picks_' + index)

    if not ol_oh_picks:
        ol_oh_pick_post.write("\n")
        ol_oh_pick_post.write(html_bold("\nOPEN HIGH OPEN LOW PICKS : None of the stocks under this index looks to be NR7 pick. \n".format(index)))
        return
    else:
        ol_oh_pick_post.write(html_bold("\nOPEN HIGH OPEN LOW PICKS as of {} are {} \n\n".format(day, ol_oh_picks)))
        ol_oh_pick_post.write("\nKeep an eye on these stocks, find the below key points for more information\n")

    for sym in ol_oh_picks:

        sym = sym.upper()

        sym_file = '/tmp/nr/{}.json'.format(sym)
        sym_data = dict()

        if os.path.exists(sym_file):
            with open(sym_file, 'r') as data_file:
                if os.stat(sym_file).st_size != 0:
                    sym_data = json.load(data_file)

        post_market_data = sym_data[day]

        open_price = post_market_data['open']
        day_low = post_market_data['low']
        day_high = post_market_data['high']

        buy_trend = open_price == day_low
        sell_trend = open_price == day_high

        ol_oh_pick_post.write(html_h2(html_bold("\nSYM: {} looks to be OPEN HIGH OPEN LOW PICK \n\n".format(sym))))

        if buy_trend:
            ol_oh_pick_post.write("SYM: {}\n"
                                  "Open Price: {}, \n"
                                  "day_low: {} \n"
                                  "was same\n"
                                  "Buy at {}, target: {}, stop loss: {}".format(sym,open_price, day_low, day_high, day_high*1.03, day_high*0.97))

        if sell_trend:
            ol_oh_pick_post.write("SYM: {}\n"
                                  "Open Price: {}, \n"
                                  "day_high: {} \n"
                                  "was same\n"
                                  "Sell at {}, target: {}, stop loss: {}".format(sym,open_price, day_high, day_low, day_low*0.97, day_low*1.03))

        ol_oh_pick_post.write(break_item())

    ol_oh_pick_post.close()
    blogger_create_post('oh_ol_pick', pick_day=day, content_file=content_file)


def ol_oh_analysis(analysis_day, suggested_day):

    content_file = os.path.join(test_dir, 'oh_ol_pick_analysis_post.txt')
    ol_oh_pick_analysis_post = open(content_file, 'w')

    if os.path.exists(nr_pick_file):
        with open(nr_pick_file, 'r') as data_file:
            if os.stat(nr_pick_file).st_size != 0:
                picks_data = json.load(data_file)

    for index in all_indexs:
        ol_oh_picks = picks_data.get(str(suggested_day) + '_oh_ol_picks_' + index)

    if ol_oh_picks:
        ol_oh_pick_analysis_post.write(html_bold("OPEN HIGH OPEN LOW PICKS suggested as of {}, were {}.\n".format(suggested_day, ", ".join(ol_oh_picks))))
    else:
        return

    for sym in ol_oh_picks:

        sym = sym.upper()

        sym_file = '/tmp/nr/{}.json'.format(sym)
        sym_data = dict()

        if os.path.exists(sym_file):
            with open(sym_file, 'r') as data_file:
                if os.stat(sym_file).st_size != 0:
                    sym_data = json.load(data_file)

        sugg_market_data = sym_data[suggested_day]

        s_open_price = sugg_market_data['open']
        s_day_low = sugg_market_data['low']
        s_day_high = sugg_market_data['high']

        buy_trend = s_open_price == s_day_low
        sell_trend = s_open_price == s_day_high

        if buy_trend or sell_trend:
            ana_market_data = sym_data[analysis_day]
            a_open_price = ana_market_data['open']
            a_day_low = ana_market_data['low']
            a_day_high = ana_market_data['high']
            a_close_price = ana_market_data['close']

            bought_trend = a_day_high > s_day_high
            sold_trend = a_day_low < s_day_low
            ol_oh_pick_analysis_post.write(html_h2(html_bold("SYM: {} was yesterday's OPEN HIGH OPEN LOW pick\n".format(sym))))
            if buy_trend:
                ol_oh_pick_analysis_post.write("was Buy: {}, \n"
                                      "with target: {} \n"
                                      "was stoploss: {}\n".format(s_day_high, s_day_high * 1.03, s_day_high * 0.97))
                if bought_trend:
                    ol_oh_pick_analysis_post.write("\n"
                                          "Today opened at {} and it went high as {}".format(a_open_price,a_day_high))
                else:
                    ol_oh_pick_analysis_post.write("OL_OH suggestion was not clear for sym: {},\n"
                                          "Trend was not clear.\n"
                                          "open price was {}\n"
                                          "went as high as {}\n"
                                          "went as low as {}\n"
                                          "and eventually closed at {}".format(sym, a_open_price, a_day_high, a_day_low, a_close_price))

            if sell_trend:
                ol_oh_pick_analysis_post.write("was Sell: {}, \n"
                                      "with target: {} \n"
                                      "was stoploss: {}\n".format(s_day_low, s_day_low * 0.97, s_day_low * 1.03))
                if sold_trend:
                    ol_oh_pick_analysis_post.write("\n"
                                          "Today opened at {} and it went low as {}".format(a_open_price,a_day_low))
                else:
                    ol_oh_pick_analysis_post.write("OL_OH suggestion was not clear for sym: {},\n"
                                          "Trend was not clear.\n"
                                          "open price was {}\n"
                                          "went as high as {}\n"
                                          "went as low as {}\n"
                                          "and eventually closed at {}".format(sym, a_open_price, a_day_high, a_day_low, a_close_price))

    ol_oh_pick_analysis_post.close()
    blogger_create_post('oh_ol_pick_analysis', pick_day=analysis_day, suggested_day=suggested_day, content_file=content_file)


def history(symbol, start_day, end_day):
    try:
        test = get_history(symbol=symbol, start=start_day, end=end_day)
    except requests.exceptions.ConnectionError as e:
        log.info(e.message)
        test = get_history(symbol=symbol, start=start_day, end=end_day)
    return test

if __name__ == '__main__':

    # def profit & stop loss margin
    tsl = 1.0/6

    # Intraday trading limits
    profit_margin_quick = 0.6
    sl_margin_quick = 1.0
    diff = 0.2
    profit_margin_with_quantity = ((profit_margin_quick - diff, 1, sl_margin_quick - diff), (profit_margin_quick, 1, sl_margin_quick), (profit_margin_quick + diff, 1, sl_margin_quick + diff))

    # Running for last x days
    last_few_days = 3
    for x in reversed(range(last_few_days)):
        today = date.today() - timedelta(x)

        # Getting history of last 20 day, to pick last 7 trading days data
        nr_range = timedelta(20)
        test = history(symbol='INFY', start_day=today-nr_range, end_day=today)
        test_days = test['High'].to_dict()
        last_seven_trading_days = sorted(test_days)[-7:]
        log.info("last_seven_trading_days; {}".format(last_seven_trading_days))
        last_trading_day = last_seven_trading_days[len(last_seven_trading_days) - 1]
        last_trading_day_1 = last_seven_trading_days[len(last_seven_trading_days) - 2]

        service = get_service()
        with open("conf/blog_id.txt", 'r') as blog_id_file:
            blog_id = blog_id_file.read()
        print(blog_id)
        blogs = service.blogs()
        blog_get_obj = blogs.get(blogId=blog_id)

        blogs = service.blogs()
        posts = service.posts()

        # List the posts for each blog this user has
        request = posts.list(blogId=blog_id)
        posts_details = request.execute()
        all_posts = posts_details['items'] if 'items' in posts_details.keys() else []
        post_titles = [x['title'] for x in all_posts]

        for index in all_symbols:
            nr_pick_file = os.path.join(test_dir, 'picks.json')
            # fetch latest trading day data and its previous day
            nr_fetch_data(index, last_trading_day)
            nr_fetch_data(index, last_trading_day_1)
            nr_pick_analysis(index, str(last_trading_day), str(last_trading_day_1))
            nr_pick(index, str(last_trading_day))

        ol_oh_analysis(str(last_trading_day), str(last_trading_day_1))
        ol_oh(str(last_trading_day))
