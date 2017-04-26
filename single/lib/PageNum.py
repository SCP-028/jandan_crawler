# -*- coding: utf-8 -*-
import re


def NextPage(soup):
    """Return link to next page."""
    s = soup.find("a", class_="previous-comment-page")["href"]
    return(s)


def GetPageNum(soup):
    """Get current page number."""
    page_num = re.sub(r".*page\-(\d+)(#comments)?", "\\1", NextPage(soup))
    return(int(page_num) + 1)
