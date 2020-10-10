import yfinance as yf
import ray


@ray.remote
def get_yf_ticker(ticker):
    hist = yf.Ticker(ticker).history(period="max")
    hist.columns = [a.lower() for a in hist.columns]
    hist["timestamp"] = [str(a) for a in hist.index]
    return hist

def get_yf_ticker_async(*tickers):
    yf_tickers = [get_yf_ticker.remote(ticker) for ticker in tickers]
    return [ray.get(x) for x in yf_tickers]