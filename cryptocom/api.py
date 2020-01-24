import logging
import hashlib
import requests
from time import sleep
from datetime import datetime

logger = logging.getLogger('cryptocom_api')

RATE_LIMIT_PER_SECOND = 10
LIMIT_ORDER = 1
MARKET_ORDER = 2


def current_timestamp():
    return int(datetime.timestamp(datetime.now()) * 1000)


class CryptoComApi:
    API_BASE = "https://api.crypto.com"

    __key = ""
    __secret = ""
    __public_only = True

    __last_api_call = 0

    def __init__(self, key=None, secret=None):
        if key and secret:
            self.__key = key
            self.__secret = secret
            self.__public_only = False

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
            delay_for_ms = 1000/RATE_LIMIT_PER_SECOND - min(1000/RATE_LIMIT_PER_SECOND, ms_from_last_api_call)
            logger.debug(f"API call '{path}' rate limiter activated, delaying for {delay_for_ms}ms")
            sleep(delay_for_ms / 1000)

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
            if r.status_code != 200:
                logger.warning(f"Response {r.status_code} NOK: {r.text}")
                return {}

            response = r.json()

            if response.get('code') != '0':
                # error occurred
                logger.warning(f'Error code: {response.get("code")}')
                logger.warning(f'Error msg: {response.get("msg")}')
                return {}
            return response.get('data')
        except Exception as e:
            logger.error(f"{e}\r\nResponse text: {r.text}")
            return {}

    def _post(self, path, params=None):
        if self.__public_only:
            return {}
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
    def tickers(self):
        return self._request('/v1/ticker')

    # Get ticker for a particular market
    def ticker(self, symbol):
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

    #####################################
    # User Group #
    def balance(self):
        """
        List all account balance of user

        @return: {
                  "total_asset": 432323.23, // user total assets (estimated in BTC)
                  "coin_list": [
                    {
                      "normal": 32323.233, // usable balance
                      "locked": 32323.233, // locked balance, e.g. locked in an active, non-executed order
                      "btcValuatin": 112.33, // value equal to BTC
                      "coin": "btc" // asset type
                    },
                    {
                      "normal": 32323.233,
                      "locked": 32323.233,
                      "btcValuatin": 112.33,
                      "coin": "ltc"
                    },
                    {
                      "normal": 32323.233,
                      "locked": 32323.233,
                      "btcValuatin": 112.33,
                      "coin": "bch"
                    }
                  ]
                }
        """
        return self._post('/v1/account')

    def create_order(self, symbol, side, _type, volume, price=None, fee_coin=None):
        """
        creates a buy or sell order on exchange

        @param fee_coin: (optional) whether to use the platform currency to pay the handling fee, 0: no, 1: yes
        @param price: (optional) Unit price. If type=2 then no need for this parameter.
        @param symbol: Market symbol ex. "ethbtc"
        @param side: BUY, SELL

        @type _type: int
        @param _type: 1 for limit order (user sets a price), 2 for market order (best available price)

        @param volume: type=1: represents the quantity of sales and purchases; \
                       type=2: buy means the total price, Selling represents the total number.

        @return: { "order_id": 34343 }
        """
        params = {'symbol': symbol, 'side': side, 'type': _type, 'volume': volume}

        if fee_coin:
            params['fee_is_user_exchange_coin'] = fee_coin
        if price:
            params['price'] = price

        return self._post('/v1/order', params)

    def create_limit_order(self, symbol, side, amount, price, fee_coin=None):
        return self.create_order(symbol, side, LIMIT_ORDER, amount, price, fee_coin)

    def create_market_order(self, symbol, side, total, fee_coin=None):
        return self.create_order(symbol, side, MARKET_ORDER, total, None, fee_coin)

    def show_order(self, symbol, order_id):
        """
        Get order detail

        @param symbol: Market symbol ex. "ethbtc"
        @param order_id: Order ID
        @return:
        {
            "trade_list": [
                {
                    "volume": "0.00100000",
                    "feeCoin": "USDT",
                    "price": "9744.25000000",
                    "fee": "0.00000000",
                    "ctime": 1571971998000,
                    "deal_price": "9.74425000",
                    "id": 6224,
                    "type": "SELL"
                }
            ],
            "order_info": {
                "id": 8140,
                "side": "SELL",
                "total_price": "8.00000000",
                "fee": 0E-8,
                "created_at": 1571971998681,
                "deal_price": 9.7442500000000000,
                "avg_price": "9744.25000000",
                "countCoin": "USDT",
                "source": 3,
                "type": 1,
                "side_msg": "SELL",
                "volume": "0.00100000",
                "price": "8000.00000000",
                "source_msg": "API",
                "status_msg": "Completely Filled",
                "deal_volume": "0.00100000",
                "fee_coin": "USDT",
                "remain_volume": "0.00000000",
                "baseCoin": "BTC",
                "tradeList": [
                    {
                        "volume": "0.00100000",
                        "feeCoin": "USDT",
                        "price": "9744.25000000",
                        "fee": "0.00000000",
                        "ctime": 1571971998000,
                        "deal_price": "9.74425000",
                        "id": 6224,
                        "type": "SELL"
                    }
                ],
                "status": 2
            }
        }
        """
        params = {'symbol': symbol, 'order_id': order_id}
        return self._post('/v1/showOrder', params)

    def cancel_order(self, symbol, order_id):
        """
        Cancel an order

        @param symbol: Market symbol ex. "ethbtc"
        @param order_id: OrderID
        @return: (null)
        """
        params = {'symbol': symbol, 'order_id': order_id}
        return self._post('/v1/orders/cancel', params)

    def cancel_all_orders(self, symbol):
        """
        Cancel all orders in a particular market

        @param symbol: Market symbol ex. "ethbtc"
        @return: (null)
        """
        params = {'symbol': symbol}
        return self._post('/v1/cancelAllOrders', params)

    def open_orders(self, symbol, page_size=None, page_number=None):
        """
        List all open orders in a particular market

        @param symbol: Market symbol ex. "ethbtc"
        @param page_size: Page size (optional)
        @param page_number: Page number (optional)
        @return:
        """
        params = {'symbol': symbol}
        if page_size and page_number:
            params['pageSize'] = page_size
            params['page'] = page_number
        return self._post('/v1/openOrders', params)

    def all_orders(self, symbol, page_size=None, page_number=None, start=None, end=None):
        """
        List all orders in a particular market (including executed, pending, cancelled orders)

        @param symbol: Market symbol ex. "ethbtc"
        @param page_size: Page size (optional)
        @param page_number: Page number (optional)
        @param start: Start time, accurate to seconds "yyyy-MM-dd mm:hh:ss" (optional)
        @param end: End time, accurate to seconds "yyyy-MM-dd mm:hh:ss" (optional)
        @return:
        """
        params = {'symbol': symbol}
        if page_size and page_number:
            params['pageSize'] = page_size
            params['page'] = page_number
        if start:
            params['startDate'] = start
        if end:
            params['endDate'] = end
        return self._post('/v1/allOrders', params)

    def all_executed_orders(self, symbol, page_size=None, page_number=None, start=None, end=None, sort=None):
        """
        List all executed orders

        @param symbol: Market symbol ex. "ethbtc"
        @param page_size: Page size (optional)
        @param page_number: Page number (optional)
        @param start: Start time, accurate to seconds "yyyy-MM-dd mm:hh:ss" (optional)
        @param end: End time, accurate to seconds "yyyy-MM-dd mm:hh:ss" (optional)
        @param sort: 1 gives reverse order
        @return:
        """
        params = {'symbol': symbol}
        if page_size and page_number:
            params['pageSize'] = page_size
            params['page'] = page_number
        if start:
            params['startDate'] = start
        if end:
            params['endDate'] = end
        if sort:
            params['sort'] = sort
        return self._post('/v1/myTrades', params)
