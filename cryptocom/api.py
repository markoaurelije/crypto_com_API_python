import logging
import hashlib
import hmac
import requests
from time import sleep, time
from datetime import datetime
from enum import Enum

logger = logging.getLogger('cryptocom_api')

RATE_LIMIT_PER_SECOND = 10
LIMIT_ORDER = 1
MARKET_ORDER = 2


def current_timestamp():
    return int(datetime.timestamp(datetime.now()) * 1000)


class CryptoComApi:
    class ApiVersion(Enum):
        V1 = "v1"
        V2 = "v2"

    _API_VERSION_ROOT_PATH = {
        # ApiVersion.V1: "https://uat-api.3ona.co/v1/",
        ApiVersion.V1: "https://api.crypto.com/v1/",
        # ApiVersion.V2: "https://uat-api.3ona.co/v2/",
        ApiVersion.V2: "https://api.crypto.com/v2/"
    }

    __key = ""
    __secret = ""
    __public_only = True

    __last_api_call = 0

    version = ApiVersion.V1

    response_code = {
        ApiVersion.V1: 'code',
        ApiVersion.V2: 'code'
    }
    response_message = {
        ApiVersion.V1: 'msg',
        ApiVersion.V2: 'message'
    }
    response_result = {
        ApiVersion.V1: 'data',
        ApiVersion.V2: 'result'
    }

    response = None

    error = None

    def __init__(self, key=None, secret=None, version=ApiVersion.V2):
        self.version = CryptoComApi.ApiVersion(version)
        self.API_ROOT = self._API_VERSION_ROOT_PATH[self.version]

        logger.debug(f"API version {version} initialized, root path is: {self.API_ROOT}")

        if key and secret:
            self.__key = key
            self.__secret = secret
            self.__public_only = False

    def get_code(self):
        return self.response and self.response[self.response_code[self.version]]

    def get_message(self):
        return self.response and self.response[self.response_message[self.version]]

    def get_result(self):
        return self.response and self.response[self.response_result[self.version]]

    def _sign(self, params, method=None, id=None, nonce=None):
        to_sign = ""
        for key in sorted(params.keys()):
            to_sign += key + str(params[key])

        if self.version == CryptoComApi.ApiVersion.V1:
            to_sign += str(self.__secret)
            return hashlib.sha256(to_sign.encode()).hexdigest()
        if self.version == CryptoComApi.ApiVersion.V2:
            to_sign = method + \
                      (str(id) if id else "") + \
                      self.__key + \
                      to_sign + \
                      str(nonce)
            return hmac.new(
                bytes(str(self.__secret), 'utf-8'),
                msg=bytes(to_sign, 'utf-8'),
                digestmod=hashlib.sha256
            ).hexdigest()

    def _request(self, path, param=None, method='get'):
        ms_from_last_api_call = current_timestamp() - self.__last_api_call
        if ms_from_last_api_call < 1000/RATE_LIMIT_PER_SECOND:
            delay_for_ms = 1000/RATE_LIMIT_PER_SECOND - min(1000/RATE_LIMIT_PER_SECOND, ms_from_last_api_call)
            logger.debug(f"API call '{path}' rate limiter activated, delaying for {delay_for_ms}ms")
            sleep(delay_for_ms / 1000)

        self.__last_api_call = current_timestamp()

        self.error = None

        if method == 'post':
            if self.version == CryptoComApi.ApiVersion.V1:
                r = requests.post(self.API_ROOT + path, data=param)
            else:
                r = requests.post(self.API_ROOT + path, json=param, headers={"Content-Type": "application/json"})
        elif method == 'delete':
            if self.version == CryptoComApi.ApiVersion.V1:
                r = requests.delete(self.API_ROOT + path, data=param)
            else:
                r = requests.delete(self.API_ROOT + path, json=param, headers={"Content-Type": "application/json"})
        elif method == 'get':
            r = requests.get(self.API_ROOT + path, params=param)
        else:
            return {}

        try:
            if r.elapsed:
                logger.debug(f"{path}, elapsed: {r.elapsed}")
        finally:
            pass

        try:
            if r.status_code != 200:
                logger.warning(f"Response {r.status_code} NOK: {r.text}")
                self.error = {'http_code': r.status_code}
                try:
                    self.error.update(r.json())
                except:
                    pass
                return {}

            self.response = r.json()

            if int(self.get_code()) != 0:
                # error occurred
                logger.warning(f'Error code: {self.get_code()}')
                logger.warning(f'Error msg: {self.get_message()}')
                self.error = self.response
                return {}
            return self.get_result()
        except Exception as e:
            logger.error(f"{e}\r\nResponse text: {r.text}")
            self.error = {'exception': r.text}
            return {}

    def _post(self, path, params=None):
        if self.__public_only:
            return {}
        if params is None:
            params = {}

        if self.version == CryptoComApi.ApiVersion.V1:
            params['api_key'] = self.__key
            params['time'] = current_timestamp()
            params['sign'] = self._sign(params)

        if self.version == CryptoComApi.ApiVersion.V2:
            # nonce = int(time() * 1000)
            id = 1
            nonce = current_timestamp()
            sig = self._sign(params, method=path, id=id, nonce=nonce)
            param = {
                'params': params,
                'sig': sig,
                'api_key': self.__key,
                'method': path,
                'nonce': nonce,
                'id': id}
            return self._request(path, param, method='post')

        return self._request(path, params, method='post')

    ### Market Group ###
    # List all available market symbols
    def symbols(self, **kwargs):
        path = {
            CryptoComApi.ApiVersion.V1: "symbols",
            CryptoComApi.ApiVersion.V2: "public/get-instruments",
        }
        return self._request(path[self.version])

    # Get tickers in all available markets
    def tickers(self, param=None, **kwargs):
        path = {
            CryptoComApi.ApiVersion.V1: "ticker",
            CryptoComApi.ApiVersion.V2: "public/get-ticker",
        }
        return self._request(path[self.version], param=param)

    # Get ticker for a particular market
    def ticker(self, symbol, **kwargs):
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol},
            CryptoComApi.ApiVersion.V2: {'instrument_name': symbol},
        }
        return self.tickers(param[self.version])

    # Get k-line data over a specified period
    def klines(self, symbol, period, **kwargs):
        if self.version != CryptoComApi.ApiVersion.V1:
            return {}
        return self._request('klines', param={'symbol': symbol, 'period': period})

    # Get last 200 trades in a specified market
    def trades(self, symbol, **kwargs):
        path = {
            CryptoComApi.ApiVersion.V1: "trades",
            CryptoComApi.ApiVersion.V2: "public/get-trades",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol},
            CryptoComApi.ApiVersion.V2: {'instrument_name': symbol},
        }
        return self._request(path[self.version], param[self.version])

    # Get latest execution price for all markets
    def prices(self, **kwargs):
        if self.version != CryptoComApi.ApiVersion.V1:
            return {}
        return self._request('ticker/price')

    # Get the order book for a particular market, type: step0, step1, step2 (step0 is the highest accuracy)
    def order_book(self, symbol, _type='step0', **kwargs):
        path = {
            CryptoComApi.ApiVersion.V1: "depth",
            CryptoComApi.ApiVersion.V2: "public/get-book",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol, 'type': _type},
            CryptoComApi.ApiVersion.V2: {'instrument_name': symbol, 'depth': _type},
        }
        return self._request(path[self.version], param[self.version])

    #####################################
    # User Group #
    def balance(self, currency=None, **kwargs):
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
        path = {
            CryptoComApi.ApiVersion.V1: "account",
            CryptoComApi.ApiVersion.V2: "private/get-account-summary",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {},
            CryptoComApi.ApiVersion.V2: {'currency': currency} if currency else {},
        }
        return self._post(path[self.version], params=param[self.version])

    def create_order(self, symbol, side, _type, quantity=None, price=None, fee_coin=None, notional=None, client_oid=None, **kwargs):
        """
        creates a buy or sell order on exchange

        @param fee_coin: (optional) whether to use the platform currency to pay the handling fee, 0: no, 1: yes
        @param price: (optional) Unit price. If type=2 then no need for this parameter.
        @param symbol: Market symbol ex. "ethbtc"
        @param side: BUY, SELL

        @type _type: int
        @param _type: 1 for limit order (user sets a price), 2 for market order (best available price)

        @param quantity: type=1: represents the quantity of sales and purchases; \
                         type=2: buy means the total price, Selling represents the total number.

        @param notional:
        @return: { "order_id": 34343 }
        """
        path = {
            CryptoComApi.ApiVersion.V1: "order",
            CryptoComApi.ApiVersion.V2: "private/create-order",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol, 'side': side, 'type': _type, 'volume': quantity},
            CryptoComApi.ApiVersion.V2: {
                'instrument_name': symbol,
                'side': side,
                'type': 'MARKET' if _type == 2 else 'LIMIT'
            },
        }

        if price:
            param[self.version]['price'] = price

        if quantity:
            # ApiVersion.V2 !!!!
            # For LIMIT Orders and MARKET (SELL) Orders only:
            # Order Quantity to be Sold
            param[CryptoComApi.ApiVersion.V2]['quantity'] = quantity

        if notional:
            # ApiVersion.V2 !!!!
            # For MARKET (BUY) Orders only - Amount to spend
            param[CryptoComApi.ApiVersion.V2]['notional'] = notional

        if client_oid:
            param[CryptoComApi.ApiVersion.V2]['client_oid'] = client_oid

        if self.version == CryptoComApi.ApiVersion.V1:
            if fee_coin:
                param[self.version]['fee_is_user_exchange_coin'] = fee_coin

        return self._post(path[self.version], params=param[self.version])

    def create_limit_order(self, symbol, side, amount, price, fee_coin=None, client_oid=None, **kwargs):
        return self.create_order(symbol, side, LIMIT_ORDER, amount, price, fee_coin=fee_coin, client_oid=client_oid)

    def create_market_order(self, symbol, side, total, fee_coin=None, client_oid=None, **kwargs):
        return self.create_order(symbol, side, MARKET_ORDER, total, None, fee_coin=fee_coin, client_oid=client_oid)

    def show_order(self, symbol, order_id, **kwargs):
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
        path = {
            CryptoComApi.ApiVersion.V1: "showOrder",
            CryptoComApi.ApiVersion.V2: "private/get-order-detail",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol, 'order_id': order_id},
            CryptoComApi.ApiVersion.V2: {'order_id': order_id}
        }
        return self._post(path[self.version], params=param[self.version])

    def cancel_order(self, symbol, order_id, **kwargs):
        """
        Cancel an order

        @param symbol: Market symbol ex. "ethbtc"
        @param order_id: OrderID
        @return: (null)
        """
        path = {
            CryptoComApi.ApiVersion.V1: "orders/cancel",
            CryptoComApi.ApiVersion.V2: "private/cancel-order",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol, 'order_id': order_id},
            CryptoComApi.ApiVersion.V2: {'instrument_name': symbol, 'order_id': order_id}
        }
        return self._post(path[self.version], params=param[self.version])

    def cancel_all_orders(self, symbol, **kwargs):
        """
        Cancel all orders in a particular market

        @param symbol: Market symbol ex. "ethbtc"
        @return: (null)
        """
        path = {
            CryptoComApi.ApiVersion.V1: "cancelAllOrders",
            CryptoComApi.ApiVersion.V2: "private/cancel-all-orders",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol},
            CryptoComApi.ApiVersion.V2: {'instrument_name': symbol}
        }
        return self._post(path[self.version], params=param[self.version])

    def open_orders(self, symbol=None, page_size=None, page_number=None, **kwargs):
        """
        List all open orders in a particular market

        @param symbol: Market symbol ex. "ethbtc"
        @param page_size: Page size (optional)
        @param page_number: Page number (optional)
        @return:
        """
        path = {
            CryptoComApi.ApiVersion.V1: "openOrders",
            CryptoComApi.ApiVersion.V2: "private/get-open-orders",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol},
            CryptoComApi.ApiVersion.V2: ({'instrument_name': symbol} if symbol else {})
        }

        if page_size:
            param[CryptoComApi.ApiVersion.V1]['pageSize'] = page_size
            param[CryptoComApi.ApiVersion.V2]['page_size'] = page_size
        if page_number:
            param[self.version]['page'] = page_number
        return self._post(path[self.version], params=param[self.version])

    def all_orders(self, symbol=None, page_size=None, page_number=None, start=None, end=None, **kwargs):
        """
        List all orders in a particular market (including executed, pending, cancelled orders)

        @param symbol: Market symbol ex. "ethbtc"
        @param page_size: Page size (optional)
        @param page_number: Page number (optional)
        @param start: Start time, accurate to seconds "yyyy-MM-dd mm:hh:ss" (optional)
        @param end: End time, accurate to seconds "yyyy-MM-dd mm:hh:ss" (optional)
        @return:
        """
        path = {
            CryptoComApi.ApiVersion.V1: "allOrders",
            CryptoComApi.ApiVersion.V2: "private/get-order-history",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol},
            CryptoComApi.ApiVersion.V2: ({'instrument_name': symbol} if symbol else {})
        }

        if page_size:
            param[CryptoComApi.ApiVersion.V1]['pageSize'] = page_size
            param[CryptoComApi.ApiVersion.V2]['page_size'] = page_size
        if page_number:
            param[self.version]['page'] = page_number
        if start:
            param[CryptoComApi.ApiVersion.V1]['startDate'] = start
            param[CryptoComApi.ApiVersion.V2]['start_ts'] = start
        if end:
            param[CryptoComApi.ApiVersion.V1]['endDate'] = end
            param[CryptoComApi.ApiVersion.V2]['end_ts'] = end
        return self._post(path[self.version], params=param[self.version])

    def all_executed_orders(self, symbol=None, page_size=None, page_number=None, start=None, end=None, sort=None, **kwargs):
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
        path = {
            CryptoComApi.ApiVersion.V1: "myTrades",
            CryptoComApi.ApiVersion.V2: "private/get-trades",
        }
        param = {
            CryptoComApi.ApiVersion.V1: {'symbol': symbol},
            CryptoComApi.ApiVersion.V2: ({'instrument_name': symbol} if symbol else {}),
        }

        if page_size:
            param[CryptoComApi.ApiVersion.V1]['pageSize'] = page_size
            param[CryptoComApi.ApiVersion.V2]['page_size'] = page_size
        if page_number:
            param[self.version]['page'] = page_number
        if start:
            param[CryptoComApi.ApiVersion.V1]['startDate'] = start
            param[CryptoComApi.ApiVersion.V2]['start_ts'] = start
        if end:
            param[CryptoComApi.ApiVersion.V1]['endDate'] = end
            param[CryptoComApi.ApiVersion.V2]['end_ts'] = end
        if sort:
            param[CryptoComApi.ApiVersion.V1]['sort'] = sort
        return self._post(path[self.version], params=param[self.version])
