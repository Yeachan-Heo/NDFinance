import datetime
import time
import re
import os
from bs4 import BeautifulSoup
from selenium import webdriver

def crawl(path, name, start_date="20130101"):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome("/usr/bin/chromedriver", options=chrome_options)

    if not os.path.exists(path):
        print("making dir")
        os.makedirs(path)

    driver.get(f"https://public.bitmex.com/?prefix=data/{name}/")

    while True:
        if input("type Y if webpage is open") == "Y":
            break

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

        os.system(f"wget -bq -P {path} {link}")

        print(link)


if __name__ == '__main__':
    crawl(path="/home/bellmanlabs/Data/bitmex/trade/raw/", name="trade", start_date="20200829")