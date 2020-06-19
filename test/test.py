import unittest
from cryptocom.api import CryptoComApi


class ApiV1TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.api = CryptoComApi(version=CryptoComApi.ApiVersion.V1)

    def testTicker(self):
        crobtc = self.api.ticker("crobtc")
        print(crobtc)
        self.fail()
