# -*- coding: utf-8 -*-
"""
Asynchronous web spider for jandan.net/pic .
"""
import argparse
import asyncio
import logging
# import sys

import lib.crawling as crawling
import lib.reporting as reporting

ARGS = argparse.ArgumentParser(description="Web crawler for jandan.")
ARGS.add_argument(
    "--iocp", action="store_true", dest="iocp",
    default=False, help="Use IOCP event loop (only on Windows!)")
ARGS.add_argument(
    "--select", action="store_true", dest="select",
    default=False, help="Use Select event loop (use this option on Linux!)")
ARGS.add_argument(
    "roots", nargs="*",
    default=[], help="Root URL for spider, must be 1 or more.")
ARGS.add_argument(
    "directory", action="store", type=str, nargs=1, metavar=".\\",
    default="", help="Directory to save pics.")
ARGS.add_argument(
    "--max_redirect", action="store", type=int, metavar="N",
    default=10, help="Limit redirection chains (for 301, 302 etc.)")
ARGS.add_argument(
    "--max_tries", action="store", type=int, metavar="N",
    default=4, help="Limit retries on network errors")
ARGS.add_argument(
    "--max_tasks", action="store", type=int, metavar="N",
    default=100, help="Limit concurrent connections")
# ARGS.add_argument(
#     "--exclude", action="store", metavar="REGEX",
#     help="Exclude matching URLs")
# ARGS.add_argument(
#     "--strict", action="store_true",
#     default=True, help="Strict host matching (default)")
# ARGS.add_argument(
#     "--lenient", action="store_false", dest="strict",
#     default=False, help="Lenient host matching")
ARGS.add_argument(
    "-v", "--verbose", action="count", dest="level",
    default=2, help="Verbose logging (repeat for more verbose, eg. -vvv)")
ARGS.add_argument(
    "-q", "--quiet", action="store_const", const=0, dest="level",
    default=2, help="Only log errors")


def fix_url(url):
    """Add http:// prefix to url if it doesn't have one."""
    if "://" not in url:
        if url.startswith("//"):
            url = "http:" + url
        else:
            url = "http://" + url
    return(url)


if __name__ == "__main__":
    """Main program.
    Parse arguments, set up event loop, run crawler, print report.
    """
    args = ARGS.parse_args()
    if not args.roots and args.directory:
        print("See --help for what you should input!")
    LEVEL = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    logging.basicConfig(level=LEVEL[min(args.level, len(LEVEL) - 1)])
    # format='%(asctime)s %(message)s',
    # datefmt='%a, %b %d %Y %H:%M:%S',
    # filename='download.log',
    # filemode='a')
    if args.iocp:  # Set up event loop on windows
        from asyncio.windows_events import ProactorEventLoop
        loop = ProactorEventLoop()
        asyncio.set_event_loop(loop)
    elif args.select:  # Event loop on Linux
        try:  # uvloop has better performance
            import uvloop
            loop = uvloop.new_event_loop()
            asyncio.set_event_loop(loop)
        except ImportError:
            loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(loop)
    else:
        loop = asyncio.get_event_loop()

    roots = {fix_url(root) for root in args.roots}
    directory = args.directory[0]
    logging.info("Start crawling!")
    crawler = crawling.Crawler(roots, directory,
                               # exclude=args.exclude,
                               max_redirect=args.max_redirect,
                               max_tries=args.max_tries,
                               max_tasks=args.max_tries)
    # try:
    loop.run_until_complete(crawler.crawl())
    # except KeyboardInterrupt:
    #     sys.stderr.flush()
    #     print("\nInterrupted...\n")
    # finally:
    reporting.report(crawler)
    crawler.close()
    # Don't understand the following lines, aiohttp resource cleanup.
    # loop.stop()
    # loop.run_forever()  # Make sure all tasks get executed
    loop.close()
