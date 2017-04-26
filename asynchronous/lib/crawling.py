"""Class of a web crawler."""

import asyncio
import aiohttp
import aiofiles
import logging
import re
import time
import cgi
import os
import urllib.parse
from collections import namedtuple
from asyncio import Queue
from bs4 import BeautifulSoup as bs

from lib.GenHeader import GenHeader
from lib.ParseLink import PicLink
from lib.PageNum import NextPage
# from lib.ParseCookie import GetCookie

LOGGER = logging.getLogger(__name__)


def is_redirect(response):
    return response.status in (300, 301, 302, 303, 307)


FetchStatistic = namedtuple('FetchStatistic',
                            ['url',
                             'next_url',
                             'status',
                             'exception',
                             'size',
                             'content_type',
                             'encoding',
                             'num_urls'])


class Crawler:
    """Crawl URLs given root URL(s).
    Manages two sets of URLs: 'urls': set of seen URLs, and
    'done': set of FetchStatistics.
    """

    def __init__(self, roots, filepath, exclude=None,
                 max_redirect=10, max_tries=4, max_tasks=10,
                 *, loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self.roots = roots
        self.filepath = filepath
        self.filename_regex = re.compile(r"^.*\/(\w+\.\w{3,4})")
        self.exclude = exclude
        self.max_redirect = max_redirect
        self.max_tries = max_tries
        self.max_tasks = max_tasks
        self.q = Queue(loop=self.loop)
        self.seen_urls = set()
        self.done = []
        # raw_cookies =
        # """Hm_lvt_fd93b7fb546adcfbcf80c4fc2b54da2c=1482727221,1482823296,1483068503,1483525103;_ga=GA1.2.295882019.1479009106;voted_comments_2648016=-1;jdna=01b0531fab6a989460dd1b231010b496#1492509737502"""
        self.session = aiohttp.ClientSession(loop=self.loop)
        # self.root_domains = set()
        # for root in roots:
        #     parts = urllib.parse.urlparse(root)
        #     host, port = urllib.parse.splitport(parts.netloc)
        #     if not host:
        #         continue
        #     if re.match(r"^[\d\.]*$", host):
        #         self.root_domains.add(host)
        #     else:
        #         host = host.lower()
        #         self.root_domains.add(host)
        for root in roots:
            self.add_url(root)
        self.t0 = time.time()
        self.t1 = None

    def close(self):
        """Close aiohttp session."""
        self.session.close()

    # def host_okay(self, host):
    #     """Check if host should be crawled."""
    #     host = host.lower()
    #     if host in self.root_domains:
    #         return(True)

    def record_statistic(self, fetch_statistic):
        """Record the FetchStatistic for completed / failed URL."""
        self.done.append(fetch_statistic)

    def fix_url(self, url):
        """Add http:// prefix to url if it doesn't have one."""
        if "://" not in url:
            if url.startswith("//"):
                url = "http:" + url
            else:
                url = "http://" + url
        return(url)

    async def parse_links(self, response):
        """Return a FetchStatistic and two lists:
        filenames and links.
        links store pic links and links to next page."""
        links = set()
        content_type = None
        encoding = None
        # body = await response.read()  # Binary, non-text requests
        if response.status == 200:
            content_type = response.headers.get("content-type")
            pdict = {}
            if content_type:
                content_type, pdict = cgi.parse_header(content_type)
            encoding = pdict.get("charset", "utf-8")

            if content_type in ("text/html", "application/xml"):
                text = await response.text()  # HTML content of response
                soup = bs(text, "lxml")
                urls = PicLink(soup, min_score=300)  # {filename: link}
                if urls:
                    LOGGER.info("Got {0} pics from {1}.".format(
                        len(urls), response.url))
                for url in urls.values():
                    url = self.fix_url(url)
                    print(url)
                    links.update(url)
                next_page = NextPage(soup)
                print(next_page)
                links.add(next_page)
            elif "image/jpeg" in content_type:
                filename = re.sub(self.filename_regex, r"\1", response.url)
                filepath = os.path.join(self.filepath, filename)
                print(filepath)
                with open(filepath, "wb") as pic:
                    async for data in response.content.iter_chunked(2**11):
                        pic.write(data)
        else:
            LOGGER.error("Response code: {0} for page {1}".format(
                response.status, response.url))

        stat = FetchStatistic(
            url=response.url,
            next_url=None,
            status=response.status,
            exception=None,
            size=len(text),
            content_type=content_type,
            encoding=encoding,
            num_urls=len(links))
        return(stat, links)

    async def fetch(self, url, max_redirect):
        """Fetch one url."""
        tries = 0
        exception = None
        while tries < self.max_tries:
            try:
                HEADER = GenHeader()
                print(HEADER["User-Agent"])
                response = await self.session.get(
                    url, allow_redirects=False,
                    headers=HEADER)  # Add proxy here.
                if tries > 1:
                    LOGGER.info("Try No.{0} for {1} success.".format(
                        tries, url))
                break
            except aiohttp.ClientError as client_error:
                LOGGER.info("Try No.{0} for {1} raised {2}.".format(
                    tries, url, client_error))
                exception = client_error
            tries += 1
        else:  # All tries failed
            LOGGER.error("{0} failed after {1} tries.".format(
                url, self.max_tries))
            self.record_statistic(FetchStatistic(url=url,
                                                 next_url=None,
                                                 status=None,
                                                 exception=exception,
                                                 size=0,
                                                 content_type=None,
                                                 encoding=None,
                                                 num_urls=0))
            return
        try:
            if is_redirect(response):
                location = response.headers["location"]
                next_url = urllib.parse.urljoin(url, location)
                LOGGER.info("Redirect to {0}".format(next_url))
                self.record_statistic(FetchStatistic(url=url,
                                                     next_url=next_url,
                                                     status=response.status,
                                                     exception=None,
                                                     size=0,
                                                     content_type=None,
                                                     encoding=None,
                                                     num_urls=0))
                if next_url in self.seen_urls:
                    return
                if max_redirect > 0:
                    LOGGER.info("Redirect to {0} from {1}".format(
                        next_url, url))
                    self.add_url(next_url, max_redirect - 1)
                else:
                    LOGGER.error("Redirect limit reached for "
                                 "{0} from {1}".format(next_url, url))
            else:
                stat, links = await self.parse_links(url, response)
                self.record_statistic(stat)
                for link in links.difference(self.seen_urls):  # set()
                    self.q.put_nowait((link, self.max_redirect))
                    self.seen_urls.update(link)
        finally:
            pass
        #     await response.release()  # Don't know what this line does.

    async def work(self):
        """Process items in queue forever."""
        try:
            while not self.q.empty():
                url, max_redirect = await self.q.get()
                assert url in self.seen_urls
                await self.fetch(url, max_redirect)
                self.q.task_done()
        except asyncio.CancelledError:
            pass

    def add_url(self, url, max_redirect=None):
        """Add URL to the queue if it's not seen before."""
        if max_redirect is None:
            max_redirect = self.max_redirect
        LOGGER.debug("Adding {0} {1}".format(url, max_redirect))
        self.seen_urls.add(url)
        self.q.put_nowait((url, max_redirect))

    async def crawl(self):
        """Run crawler until all URLs are finished."""
        workers = [asyncio.Task(self.work(), loop=self.loop)
                   for _ in range(self.max_tasks)]
        self.t0 = time.time()
        await self.q.join()
        self.t1 = time.time()
        for w in workers:
            w.cancel()
