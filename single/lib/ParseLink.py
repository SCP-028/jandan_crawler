# -*- coding: utf-8 -*-
import re


def PicScore(post):
    """Return score of the post. Could be more than 1 pic."""
    oo_regex = re.compile("cos_support")
    xx_regex = re.compile("cos_unsupport")
    oo_num = int(post.find("span", id=oo_regex).get_text())
    xx_num = int(post.find("span", id=xx_regex).get_text())
    score = oo_num - xx_num
    return(score)


def NamePic(post):
    """Return a unique name for the post.
    If there're multiple pics in the post, give underscore names like
    123456_1.jpg, 123456_2.jpg."""
    pic_id = re.search("\d+", post["id"]).group(0)
    pic_link = post("a", text=re.compile("查看原图"))
    pic_link = [link["href"] for link in pic_link]
    pic_link = [re.sub("^//", "http://", link)
                for link in pic_link]
    pic_suffix = [re.search("(\.\w+)$", link).group(0) for link in pic_link]
    pic_name = []
    if len(pic_link) > 1:
        for i, suffix in enumerate(pic_suffix):
            pic_name.append("{0}_{1}{2}".format(pic_id, i + 1, suffix))
    elif len(pic_link) == 1:
        pic_name.append("{0}{1}".format(pic_id, pic_suffix[0]))
    else:  # A mystery.
        pass
    return(pic_name, pic_link)


def PicLink(soup, min_score=100):
    """
    Return dict of links to pics with scores higher than min_score. Example:
    {'3424760.jpg':
    'wx3.sinaimg.cn/large/00667GqHgy1feopsyig6kj30jg0pxab7.jpg'}
    """
    comment_list = soup.find("ol", class_="commentlist").find_all("li")
    result = {}
    for comment in comment_list:
        try:
            score = PicScore(comment)
            if score >= min_score:
                pic_name, pic_link = NamePic(comment)
                pic_link = dict(zip(pic_name, pic_link))
                result = {**result, **pic_link}
        except AttributeError as e:  # Catch AdSense
            pass
    return(result)
