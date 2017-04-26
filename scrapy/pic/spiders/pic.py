import scrapy
# import re


class Pic(scrapy.Spider):
    name = "Pic"
    start_urls = [
        "http://jandan.net/pic",
        "http://jandan.net/pic-2016"
    ]

    def parse(self, response):
        # for quote in response.xpath(("//ol[@class='commentlist']/"
        #                              "li[contains(@id, 'comment')")):
        self.logger.info("Parsing page: {}".format(response.url))
        for quote in response.css(".commentlist").css("li[id^='comment']"):
            oo_num = int(quote.css("span[id^='cos_support']").xpath(
                "text()").extract_first())
            xx_num = int(quote.css("span[id^='cos_unsupport']").xpath(
                "text()").extract_first())
            score = oo_num - xx_num
            if score >= 300:  # Minimum score needed to download.
                pics = quote.css(".view_img_link").xpath("@href").extract()
                pics = ["http:" + link for link in pics]
                yield {
                    "file_urls": pics
                }

        next_page_url = response.css(
            "a.previous-comment-page::attr(href)").extract_first()
        if next_page_url is not None:
            yield scrapy.Request(response.urljoin(next_page_url))
