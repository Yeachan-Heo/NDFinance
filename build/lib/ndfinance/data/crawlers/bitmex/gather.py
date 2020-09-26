import multiprocessing
from ndfinance.data import *
import datetime
import time
import re
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from pprint import pprint
from ndfinance.utils.array_utils import to_timestamp


def split_list(alist, wanted_parts=1):
    length = len(alist)
    return [ alist[i*length // wanted_parts: (i+1)*length // wanted_parts]
             for i in range(wanted_parts) ]

def _gather_wrapper(args):
    return _gather(*args)

def _gather(data_dir, fname, period, symbol):
    df = pd.DataFrame()
    for f in (fname):
        b = resample_tick([data_dir, f, period, symbol])
        if b.empty:
            continue
        df = df.append(b)
    return df

def gather_wrapper(args):
    return gather(*args)

def gather(data_dir, export_path, symbol, period="1T"):
    if not os.path.exists(export_path):
        os.makedirs(export_path)

    df = _gather(data_dir, os.listdir(data_dir), period, symbol)

    df.to_csv(export_path + f"{symbol}_{period}.csv")

def _resample_tick(args):
    return resample_tick(*args)

def return_symbol_dict(path, symbols=['BCHUSD', 'ETHUSD', 'LTCUSD', 'XBTUSD', 'XRPUSD']):
    df = pd.read_csv(path)
    if symbols is None:
        symbols = df["symbol"].values
    args = [(df, symbol) for symbol in symbols]
    with multiprocessing.Pool(12) as p:
        ret = p.map(_resample_tick, args)
    ret = [(symbol, r) for symbol, r in zip(symbols, ret)]
    return ret

def gather_v2(data_dir, export_dir, symbols=None):
    df_dict = {}
    paths = sorted(os.listdir(data_dir))
    paths = [data_dir + path for path in paths]

    for path in (paths):
        ret = return_symbol_dict(path, symbols)
        for key, value in ret:
            if key in df_dict.keys():
                df_dict[key] = df_dict[key].append(value)
            else:
                df_dict[key] = value

    for key, value in df_dict.items():
        value.to_csv(export_dir + key + "_1T.csv")


def make_directories(data_path, export_path):
    args = [(data_path, fname, export_path) for fname in os.listdir(data_path)]
    with multiprocessing.Pool(12) as p:
        p.map(_make_dir, (args))


def _make_dir(args):
    return make_dir(*args)

def make_dir(data_path, fname, export_path):
    df = pd.read_csv(data_path + fname)
    tickers = list(set(df["symbol"]))
    for ticker in reversed(tickers):
        if not os.path.exists(export_path + ticker):
            for x in ["raw","1T","3T","5T","10T","15T","30T","1H","1D","1M","1Y"]:
                os.makedirs(export_path + ticker + "/" + x)

def make_date(start_date):
    y, m, d = int(start_date[:4]), int(start_date[4:6]), int(start_date[6:])
    start_date = datetime.date(y, m, d)
    return start_date


def read_csv(path):
    return pd.read_csv(path)


class BitmexDataManager:
    def __init__(self, raw_data_dir, ticker_data_dir, ohlc_data_dir):
        self.raw_data_dir = raw_data_dir
        self.ticker_data_dir = ticker_data_dir
        self.ohlc_data_dir = ohlc_data_dir
        self.pool = multiprocessing.Pool(12)
        pass

    @staticmethod
    def make_dict(df):
        symbols = list(set(df["symbol"].values))
        return {symbol : df.loc[df["symbol"] == symbol] for symbol in symbols}

    def export_tick_data(self, fnames):
        df = pd.read_csv(self.raw_data_dir + fnames)
        df_dict = self.make_dict(df)

        for key, value in df_dict.items():
            value.to_csv(self.ticker_data_dir + key + "/raw/" + fnames)


    def split_tick_data(self, start_date="19700101"):
        start_date = make_date(start_date)
        fnames = list(filter(lambda x: make_date(x[:8]) >= start_date, os.listdir(self.raw_data_dir)))
        fnames.sort()
        for fname in (fnames):
            self.export_tick_data(fname)

    def resample_tick(self, data_path, period):
        df = pd.read_csv(data_path)
        df.index = pd.to_datetime(df["timestamp"].str.replace("D", " "))

        bar = df["price"].resample(period).ohlc().fillna(method="ffill")
        bar["volume"] = df["size"].resample(period).sum().fillna(0)
        return bar


    def resample_tick_data(self, start_date="19700101"):
        start_date = make_date(start_date)
        for i in (os.listdir(self.ticker_data_dir)):
            raw_fnames = os.listdir(self.ticker_data_dir + i + "/raw/")
            print(raw_fnames)
            raw_fnames = list(filter(lambda x: make_date(x[:8]) >= start_date, raw_fnames))
            for rfname in raw_fnames:
                df = self.resample_tick(self.ticker_data_dir + i + "/raw/" + rfname, "1T")
                df.to_csv(self.ticker_data_dir + i + "/1T/" + rfname)
                print(self.ticker_data_dir + i + "/1T/" + rfname)

    def gather_ohlc_data(self, start_date="19700101"):
        start_date = make_date(start_date)
        for i in (os.listdir(self.ticker_data_dir)):
            fnames = sorted(os.listdir(self.ticker_data_dir + i + "/1T/"))
            fnames = list(filter(lambda x: make_date(x[:8]) >= start_date, fnames))
            if fnames == []:
                continue
            fpaths = [self.ticker_data_dir + i + "/1T/" + fname for fname in fnames]
            dfs = self.pool.map(read_csv, fpaths)
            df = pd.DataFrame()
            for d in dfs:
                df = df.append(d)
            df.to_csv(self.ohlc_data_dir + "raw/" + i + ".csv")

    def gather_quarterly(self):
        fnames = os.listdir(self.ohlc_data_dir + "1T/")
        p = re.compile("[A-Z]*[M,H,Z,U][0-9][0-9].csv")
        fnames = list(filter(lambda x: p.match(x) is not None, fnames))
        tickers = [f[:-7] for f in fnames]

        tickers = sorted(list(set(tickers)))

        for ticker in (tickers):
            pattern = re.compile(f"{ticker}[M,H,Z,U]*[0-9][0-9].csv")
            ticker_fnames = list(filter(lambda x: pattern.match(x) is not None, fnames))
            ticker_fpaths = [self.ohlc_data_dir + "1T/" + f for f in ticker_fnames]
            pprint(ticker_fpaths)
            dfs = self.pool.map(read_csv, ticker_fpaths)
            df = pd.DataFrame()
            for d in reversed(dfs):
                df = df.append(d)

            df["ts"] = to_timestamp(df["timestamp"])
            df = df.sort_values(by="ts")
            df = df.drop_duplicates("ts", keep="last")
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            print(ticker, df)
            df.to_csv(self.ohlc_data_dir + "1T/" + ticker + "QUT.csv")

    def resample_ohlc_dir(self, period):
        if not os.path.exists(self.ohlc_data_dir + period):
            os.makedirs(self.ohlc_data_dir + period)
        fnames = os.listdir(self.ohlc_data_dir + "1T/")
        for fname in fnames:
            self.resample_ohlc(self.ohlc_data_dir + "1T/" + fname, self.ohlc_data_dir + period + "/" + fname, period)


    @staticmethod
    def resample_ohlc(path, export_path, period):
        df = pd.read_csv(path)
        df.index = pd.to_datetime(df["timestamp"])

        df = df.resample(period).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        })

        df = df.fillna(method="ffill")

        df.to_csv(export_path)

    def crawl(self, name="trade", start_date="20130101"):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        driver = webdriver.Chrome("/usr/bin/chromedriver", options=chrome_options)

        if not os.path.exists(self.raw_data_dir):
            print("making dir")
            os.makedirs(self.raw_data_dir)

        driver.get(f"https://public.bitmex.com/?prefix=data/{name}/")
        
        time.sleep(10)

        y, m, d = int(start_date[:4]), int(start_date[4:6]), int(start_date[6:])
        start_date = datetime.date(y, m, d)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        for i, link in enumerate(soup.findAll('a', attrs={'href': re.compile("^https://")})):

            link = (link.get('href'))

            date_str = link.split("/")[-1][:8]

            if len(date_str) < 8:
                continue

            y, m, d = int(date_str[:4]), int(date_str[4:6]), int(date_str[6:])

            date = datetime.date(y, m, d)

            if not date >= start_date:
                continue

            os.system(f"wget -P {self.raw_data_dir} {link}")
            print(link)


def get_date():
    date =  datetime.datetime.now().date().strftime("%Y%m%d")
    return date

if __name__ == '__main__':
    make_directories("/home/bellmanlabs/Data/bitmex/trade/raw/", "/home/bellmanlabs/Data/bitmex/trade/tickers/")
    manager = BitmexDataManager("/home/bellmanlabs/Data/bitmex/trade/raw/", "/home/bellmanlabs/Data/bitmex/trade/tickers/", "/home/bellmanlabs/Data/bitmex/trade/ohlc/") #asdf
    #date = get_date()
    #manager.crawl(start_date="20200907")
    manager.split_tick_data(start_date="20200908")
    manager.resample_tick_data(start_date="20200908")
    manager.gather_ohlc_data(start_date="20200908")
    manager.gather_quarterly()
    for period in (["1T", "3T","5T","10T","15T","30T","1H","1D","1M","1Y"]):
        manager.resample_ohlc_dir(period)


