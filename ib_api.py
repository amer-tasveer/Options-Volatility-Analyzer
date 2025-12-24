from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import threading
import time

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.connected  =False
        self.historical_Data ={}


    def nextValidId(self, orderId: int):
        self.connected = True
        print("Connected to IB")

    def error(self, reqId, errorCode, errorString):
        if errorCode == 2176 and "fractional share" in errorString.lower():
            return  # Ignore this specific warning
        print(f"Error: {reqId} {errorCode} {errorString}")


    def historicalData(self, reqId, bar):
        if reqId not in self.historical_Data:
            self.historical_Data[reqId] = []
        self.historical_Data[reqId].append(bar)

    def historicalDataEnd(self, reqId:int, start:str, end:str):
        print(f"Historical data received for request {reqId}:")
        for bar in self.historical_Data.get(reqId, []):
            print(bar)
        print("End of historical data.")