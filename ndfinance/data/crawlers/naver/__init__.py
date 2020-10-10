import pandas as pd
import multiprocessing
import ray
import re

def cleanText(readData):
    # 텍스트에 포함되어 있는 특수 문자 제거

    text = re.sub('[,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]', '', readData)
    if text[0] == "-":
        return -float(text[1:])
    else:
        return float(text[1:])


@ray.remote
def _crawl_price(url):
    try:
        df = pd.read_html(url)[0]
    except ValueError:
        df = pd.DataFrame()
        return df
    df = df.dropna()
    df = df.reindex(list(reversed(df.index)))
    df.columns =  ["date", "close", "change", "open", "high", "low", "volume"]
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d")
    df.index = df["date"]

    df.replace(to_replace=0, method="ffill")

    del df["date"]

    return df

def crawl_price(code, page):
    url = f"https://finance.naver.com/item/sise_day.nhn?code={code}&page="
    urls = [url + f"{p}" for p in reversed(range(1, page+1))]
    
    _dfs = [_crawl_price.remote(url) for url in urls]
    dfs = [ray.get(x) for x in _dfs]
    df = pd.DataFrame()
    
    for d in dfs:
        df = df.append(d)

    return df

def _crawl_frgn(url):
    try:
        df = pd.read_html(url)[2]
    except ValueError:
        df = pd.DataFrame()
        return df
    df = df.dropna()
    df = df.reindex(list(reversed(df.index)))
    df = df[df.columns[[0, 5, 6]]]
    df.columns = ["date", "agency", "foreigner"]

    df["agency"] = [cleanText(x) for x in df["agency"].values]
    df["foreigner"] = [cleanText(x) for x in df["foreigner"].values]

    df["date"] = pd.to_datetime(df["date"], format="%Y.%m.%d")
    df.index = df["date"]

    del df["date"]

    return df


def crawl_frgn(code, page):
    url = f"https://finance.naver.com/item/frgn.nhn?code={code}&page="
    urls = [url + f"{p}" for p in reversed(range(1, page + 1))]

    with multiprocessing.Pool(page) as p:
        dfs = p.map(_crawl_frgn, urls)

    df = pd.DataFrame()

    for d in dfs:
        df = df.append(d)

    return df

    