from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected  =False
        self.historical_data ={}


    def nextValidId(self, orderId: int):
        self.connected = True
        print("Connected to IB")

    def error(self, reqId, errorCode, errorString):
        if errorCode == 2176 and "fractional share" in errorString.lower():
            return  # Ignore this specific warning
        print(f"Error: {reqId} {errorCode} {errorString}")

    def create_contract(self, symbol, sec_type="STK", exchange="SMART", currency="USD"):
        contract = Contract()
        contract.symbol = symbol
        contract.secType = sec_type
        contract.exchange = exchange
        contract.currency = currency
        return contract
    
    def create_vix_contract(self):
        """Create a VIX contract"""
        contract = Contract()
        contract.symbol = "VIX"
        contract.secType = "IND"
        contract.exchange = "CBOE"
        contract.currency = "USD"
        return contract


    def historicalData(self, reqId, bar):
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
        self.historical_data[reqId].append({
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close, 
            "volume": bar.volume,
            })

    def historicalDataEnd(self, reqId:int, start:str, end:str):
        print(f"Historical data received for request {reqId}:")
        # print(self.historical_data[reqId])
        print("End of historical data.")