import logging
import hashlib
import requests
from time import sleep
from datetime import datetime

logger = logging.getLogger('cryptocom_api')

RATE_LIMIT_PER_SECOND = 10


def current_timestamp():
    return int(datetime.timestamp(datetime.now()) * 1000)


class CryptoComApi:
    API_BASE = "https://api.crypto.com"

    __key = ""
    __secret = ""

    __last_api_call = 0

    def __init__(self, key, secret):
        self.__key = key
        self.__secret = secret

    def _sign(self, params):
        to_sign = ""
        for param in sorted(params.keys()):
            to_sign += param + str(params[param])
        to_sign += str(self.__secret)
        h = hashlib.sha256(to_sign.encode()).hexdigest()
        return h

    def _request(self, path, param=None, method='get'):
        ms_from_last_api_call = current_timestamp() - self.__last_api_call
        if ms_from_last_api_call < 1000/RATE_LIMIT_PER_SECOND:
            delay_for_ms = 1000/RATE_LIMIT_PER_SECOND - max(1000/RATE_LIMIT_PER_SECOND, ms_from_last_api_call)
            logger.debug(f"API call rate limiter activated, delaying for {delay_for_ms}ms")
            sleep(delay_for_ms * 1000)

        self.__last_api_call = current_timestamp()

        if method == 'post':
            r = requests.post(self.API_BASE + path, data=param)
        elif method == 'delete':
            r = requests.delete(self.API_BASE + path, data=param)
        elif method == 'get':
            r = requests.get(self.API_BASE + path, params=param)
        else:
            return {}

        try:
            response = r.json()
            if response.get('code') != '0':
                # error occurred
                logger.warning(f'Error code: {response.get("code")}')
                logger.warning(f'Error msg: {response.get("msg")}')
                return response
            return response.get('data')
        except Exception as e:
            logger.error(f"{e}\r\nResponse text: {r.text}")
            return {}

    def _post(self, path, params=None):
        if params is None:
            params = {}
        params['api_key'] = self.__key
        params['time'] = current_timestamp()
        params['sign'] = self._sign(params)

        return self._request(path, params, method='post')

    ### Market Group ###
    # List all available market symbols
    def symbols(self):
        return self._request('/v1/symbols')

    # Get tickers in all available markets
    def ticker(self):
        return self._request('/v1/tickers')

    # Get ticker for a particular market
    def tickers(self, symbol):
        return self._request('/v1/ticker', param={'symbol': symbol})

    # Get k-line data over a specified period
    def klines(self, symbol, period):
        return self._request('/v1/klines', param={'symbol': symbol, 'period': period})

    # Get last 200 trades in a specified market
    def trades(self, symbol):
        return self._request('/v1/trades', param={'symbol': symbol})

    # Get latest execution price for all markets
    def prices(self):
        return self._request('/v1/ticker/price')

    # Get the order book for a particular market, type: step0, step1, step2 (step0 is the highest accuracy)
    def order_book(self, symbol, _type='step0'):
        return self._request('/v1/depth', param={'symbol': symbol, 'type': _type})

    ### User Group ###
    # List all account balance of user
    def balance(self):
        return self._post('/v1/account')

    # Create an order
    def create_order(self, symbol, side, _type, volume, price, fee_coin):
        """
        creates a buy or sell order on exchange

        @param fee_coin: whether to use the platform currency to pay the handling fee, 0: no, 1: yes
        @param price: Unit price. If type=2 then no need for this parameter.
        @param symbol: Market symbol "ethbtc"
        @param side: BUY, SELL

        @type _type: int
        @param _type: 1 for limit order (user sets a price), 2 for market order (best available price)

        @param volume: type=1: represents the quantity of sales and purchases; \
                       type=2: buy means the total price, Selling represents the total number.
        """
        params = {'symbol': symbol, 'side': side, 'type': _type}
        if price:
            params['price'] = price
        if fee_coin:
            params['fee_is_user_exchange_coin'] = fee_coin
        return self._post('/v1/order', params)

    # List all open orders in a particular market (current pending orders)
    def open_orders(self, symbol, page_size=None, page_number=None):
        params = {'symbol': symbol}
        if page_size and page_number:
            params['pageSize'] = page_size
            params['page'] = page_number
        return self._post('/v1/openOrders', params)

    # List all orders in a particular market (including executed, pending, cancelled orders)
    # start, end --> accurate to seconds "yyyy-MM-dd mm:hh:ss"
    def all_orders(self, symbol, page_size=None, page_number=None, start=None, end=None):
        params = {'symbol': symbol}
        if page_size and page_number:
            params['pageSize'] = page_size
            params['page'] = page_number
        if start:
            params['startDate'] = start
        if end:
            params['endDate'] = end
        return self._post('/v1/allOrders', params)

    # List all executed orders
    def all_executed_orders(self, symbol, page_size=None, page_number=None, start=None, end=None):
        params = {'symbol': symbol}
        if page_size and page_number:
            params['pageSize'] = page_size
            params['page'] = page_number
        if start:
            params['startDate'] = start
        if end:
            params['endDate'] = end
        return self._post('/v1/myTrades', params)
