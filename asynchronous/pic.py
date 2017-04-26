import aiohttp
import asyncio
import async_timeout
import cgi
import re
import os

# from urllib.parse import urljoin, urldefrag
from asyncio.windows_events import ProactorEventLoop
from bs4 import BeautifulSoup as bs
from lib.GenHeader import GenHeader

root_url = "http://jandan.net/pic/page-5"
crawled_urls, url_hub = [], [root_url]


def next_page(soup):
    """Return link to next page."""
    s = soup.find("a", class_="previous-comment-page")["href"]
    print(s)
    return(s)


def pic_score(post):
    """Return score of the post. Could be more than 1 pic."""
    oo_regex = re.compile("cos_support")
    xx_regex = re.compile("cos_unsupport")
    oo_num = int(post.find("span", id=oo_regex).get_text())
    xx_num = int(post.find("span", id=xx_regex).get_text())
    score = oo_num - xx_num
    return(score)


def pic_link(soup, min_score=100):
    """
    Return set of links to pics with scores higher than min_score.
    """
    links = set()
    # soup = bs(html, "lxml")
    comment_list = soup.find("ol", class_="commentlist").find_all("li")
    for comment in comment_list:
        try:
            score = pic_score(comment)
            if score >= min_score:
                pic_link = comment("a", text=re.compile("查看原图"))
                pic_link = [link["href"] for link in pic_link]
                pic_link = [re.sub("^//", "http://", link)
                            for link in pic_link]
                for link in pic_link:
                    print(link)
                    links.add(link)
        except AttributeError as e:  # Catch AdSense
            pass
    return(links)


async def parse_resp(response):
    links = set()
    filename_regex = re.compile(r"^.*\/(\w+\.\w{3,4})")
    content_type = response.headers.get("content_type")
    if content_type:
        pdict = {}
        content_type, pdict = cgi.parse_header(content_type)
    if content_type in ("text/html", "application/xml"):  # jandan page
        html = await response.text()
        soup = bs(html)
        links.add(next_page(soup))
        urls = pic_link(soup)
        for url in urls:
            links.add(url)
            # print(url)
        # links.update(pic_link(html))
        return(links)
    if content_type in ("image/jpeg", "image/gif"):
        filename = re.sub(filename_regex, r"\1", response.url)
        filepath = os.path.join(r".\pic", filename)
        print(filepath)
        with open(filepath, "wb") as pic:
            while True:
                chunk = await response.content.read(2**11)
                if not chunk:
                    break
                pic.write(chunk)
        return(response.url)


async def get_body(url):
    async with aiohttp.ClientSession() as session:
        # try:
        headers = GenHeader()
        # print(headers)
        with async_timeout.timeout(10):
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    # html = await response.text()
                    links = await parse_resp(response)
                    return {'error': response.status, 'html': links}
                else:
                    return {'error': response.status, 'html': ''}
        # except Exception as err:
        #     return {'error': err, 'html': ''}


async def handle_task(task_id, work_queue):
    while not work_queue.empty():
        queue_url = await work_queue.get()
        if queue_url not in crawled_urls:
            crawled_urls.append(queue_url)
            body = await get_body(queue_url)
            if not body['error']:
                for new_url in body["html"]:
                    if new_url not in crawled_urls:
                        work_queue.put_nowait(new_url)
            else:
                print("Error: {0} - {1}".format(body['error'], queue_url))


if __name__ == "__main__":
    loop = ProactorEventLoop()
    asyncio.set_event_loop(loop)
    q = asyncio.Queue(loop=loop)
    [q.put_nowait(url) for url in url_hub]
    # loop = asyncio.get_event_loop()
    tasks = [handle_task(task_id, q) for task_id in range(3)]
    loop.run_until_complete(asyncio.wait(tasks))
    loop.close()
    for u in crawled_urls:
        print(u)
    print('-' * 30)
    print(len(crawled_urls))
