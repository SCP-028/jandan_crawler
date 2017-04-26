# -*- coding: utf-8 -*-
import argparse
import logging
import time
import random
import requests
from bs4 import BeautifulSoup as bs
from lib.GenHeader import GenHeader
from lib.ParseCookie import *
from lib.PageNum import *
from lib.ParseLink import *


logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    datefmt='%a, %b %d %Y %H:%M:%S',
                    filename='download.log',
                    filemode='a')


parser = argparse.ArgumentParser()
parser.add_argument("-y", "--year", type=int,
                    choices=[i for i in range(2010, 2017)],
                    help="Input if you want archive pages.")
parser.add_argument("-s", "--start", type=int,
                    help="Set start page. Default is the latest page.")
parser.add_argument("-n", "--num", type=int, default=200,
                    help=("Set number of pages to scrawl. "
                          "Default is 200 pages.\n"
                          "NOTE: scrawls backwards!"))
parser.add_argument("--score", type=int, default=100,
                    help="Set minimum score of pic. Default is 200.")
args = parser.parse_args()

PATH = """.\\pic\\"""  # Path to save downloaded pics.
HEADER = GenHeader(ua="desktop")
raw_cookies = ""  # Input raw_cookies copied from Chrome here.
COOKIE = GetCookie(raw_cookies)
URL = "http://jandan.net/pic"  # Page root url.


def DownloadPic(filename, url, header, filepath):
    """Try to download a pic given a url and a filename."""
    try:
        r = requests.get(url, headers=header)
        with open(filepath + filename, "wb") as pic:
            pic.write(r.content)
        logging.info("{0}: {1}".format(filename, url))
    except Exception as e:
        logging.exception("Missed pic: {}".format(url))


if __name__ == "__main__":
    ss = requests.Session()
    try:
        URL = "{0}-{1}/".format(URL, args.year)  # The / is important...
        print("Accessing {0} ...".format(URL))
    except TypeError as e:
        pass
    try:
        current_page = int(args.start)
        print("Starting from page {}...".format(current_page))
    except TypeError as e:
        r = ss.get(url=URL, headers=HEADER, cookies=COOKIE)
        soup = bs(r.content, "lxml")
        current_page = GetPageNum(soup)
        print("Starting from latest page... {}".format(current_page))
    try:
        PAGE_NUM = min(int(args.num), current_page)
        SCORE = int(args.score) if args.score else 200
        print("Crawling {0} pages of pics with score larger than {1}.".format(
              PAGE_NUM, SCORE))
    except ValueError as e:
        PAGE_NUM = 200
        SCORE = 200
        print("Wrong input, crawling with default value:\n"
              "{0} pages of pics with score larger than {1}.".format(
                  PAGE_NUM, SCORE))

    for i in range(current_page, current_page - PAGE_NUM, -1):
        page_url = URL + "page-{}".format(i)
        HEADER["Referer"] = URL + "page-{}".format(i + 1)
        try:
            r = ss.get(url=page_url, headers=HEADER, cookies=COOKIE)
            if r.ok:
                soup = bs(r.content, "lxml")
                link_dict = PicLink(soup, min_score=SCORE)
                print("Downloading {0} pics from {1}".format(
                    len(link_dict), page_url))
                for filename, link in link_dict.items():
                    DownloadPic(filename=filename, url=link,
                                header=HEADER, filepath=PATH)
                    time.sleep(random.randint(1, 3))
                time.sleep(random.randint(3, 10))
            else:
                logging.exception("Missed page {}!".format(i))
        except requests.exceptions.ConnectionError as e:
            logging.exception("Missed page {}!".format(i))
