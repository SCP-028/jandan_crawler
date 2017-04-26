# -*- coding: utf-8 -*-
def GetCookie(raw_cookies):
    """Get raw_cookies with Chrome or Fiddler."""
    COOKIE = {}
    for line in raw_cookies.split(';'):
        key, value = line.split("=", 1)
        COOKIE[key] = value
    return(COOKIE)
