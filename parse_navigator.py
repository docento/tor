#!/usr/bin/env python
#-*- coding: windows-1251 -*-
##########################################################

__all__ = ["get_product_link"]

##########################################################

import os; from os import path as os_path
import urllib
import urllib2
import httplib
import Queue
import threading; from threading import Lock
import re

import xlrd
from bs4 import BeautifulSoup, SoupStrainer
from soupselect import select
import redis
import lxml.html

from xls_models import SheetOneRow
from redis_models import SheetOne_RR, ProductSheetOneRR
import file_utils

##########################################################

SITENAME = "www.navigator-light.ru"
THREAD_NUM = 5

##########################################################

_link_queue = Queue.Queue()
_not_found_queue = Queue.Queue()

_http_conn = []
_http_conn_lock = Lock()
photo_regexp = re.compile(".*\/[12]\.jpg$", re.I)

##########################################################

def get_product_link(conn, title):

    search_url = "http://%s" % SITENAME
    params = { "advSearch": "oneword", "search": title }
    headers = {
        "Content-Type" : "application/x-www-form-urlencoded",
        "Accept" : "text/html",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:17.0) Gecko/20100101 Firefox/17.0",
        "Refer": "http://%s/index.html" % SITENAME,
        "Connection": "Keep-Alive",
        "Cookie": "SN4d5b770ac5d67=d2357dee6e6071b55c4fd917904af225"
    }

    conn.request("POST", "/search.html", urllib.urlencode(params), headers)
    response = conn.getresponse()
    html_content = response.read()

    a_tags_only = SoupStrainer("a")
    soup = BeautifulSoup(html_content, parse_only = a_tags_only)

    a_list = select(soup, "a.ajaxSearch_resultLink")

    if not a_list:
        print "no result in search by key %s" % title
        return False
    else:
        print a_list[0]["href"]
    return a_list[0]["href"]

##########################################################

def grab_product_page(conn, link, title, row):

    product = {
        "title": title,
        "row": row,
        "product_page" : link,
        "desc": "",
        "photo_link": "",
        "photo_name": "",
        "photo_empiric_name": "",
        "table": ""
    }

    search_url = "http://%s" % SITENAME
    params = {}
    headers = {
        "Content-Type" : "application/x-www-form-urlencoded",
        "Accept" : "text/html",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:17.0) Gecko/20100101 Firefox/17.0",
        "Connection": "Keep-Alive",
        "Refer": "http://%s/index.html" % SITENAME
    }

    conn.request("POST", link, urllib.urlencode(params), headers)
    response = conn.getresponse()
    html_content = response.read()

    doc = lxml.html.document_fromstring(html_content)

    ### get photo ###

    photo = doc.cssselect("html > body > div#body_style > table > tr:nth-child(2) > "
                          "td > div.content_full > " +
                          "table > tr > td > table:nth-child(2) > tr > td")[0]

    a = photo.xpath("//a[@title='%s']" % "Фотографии товаров".decode("utf-8"))

    photo_href = a[0].attrib["href"]
    filename = photo_href.split("/")[-1]
    assert filename.endswith(".zip"), "File name is not ended with *.zip"

    # save *.zip photos
    save_photo(photo_href, filename)

    product["photo_name"] = filename
    product["photo_link"] = photo_href

    print photo_href

    ### get alternative photo name ###

    div = doc.cssselect("html > body > div#body_style > table > tr:nth-child(2) > "
                    "td > div.content_full > " +
                    "table > tr > td > table:nth-child(2) > tr > td > "
                    "div:nth-child(1) > table#table1 > tr:nth-child(1) > td > div")[0]

    print div.attrib["class"]

    print str(row) + " " + str(title) + " " + "####" * 9

    hrefs = div.xpath("//div[@class='foto_layer']/div[@class='foto_mini']/div[@class='foto_in']/a[@class='highslide']")
    if hrefs:
            if photo_regexp.match(hrefs[0].attrib["href"]):
                print("re::MATCH")
                idx = 0
            else:
                idx = 1

            _ef = hrefs[idx].attrib["href"].split("/")[-1]
            print _ef
            product["photo_empiric_name"] = _ef.lower()
    else:
        print("!!!!!!!!!!!!!!!!!!!!!! No hrefs found !!!!!!!!!!!!!!!!!!!!!")

    div = doc.cssselect("html > body > div#body_style > table > tr:nth-child(2) > "
                        "td > div.content_full > " +
                        "table > tr > td > table:nth-child(2) > tr > td > "
                        "div:nth-child(1)")[0]

    for c in div.getchildren():
        c.drop_tree()

    product["desc"] = div.text_content().encode("utf-8").strip()

    return product

##########################################################

def save_photo(href, filename):
    p = os_path.join(os.getcwd(), "photo")
    archive_path = os_path.join(p, filename)

    if not os_path.exists(archive_path):
        with open(archive_path, "w") as f:
            f.write(urllib.urlopen(href).read())
    else:
        print("path =", archive_path, "existed")

##########################################################

def grabber_worker(self_id):

    conn = httplib.HTTPConnection(SITENAME)
    with _http_conn_lock:
        _http_conn.append(conn)

    while True:
        record = _link_queue.get()

        try:
            link = get_product_link(conn, record["title"])

            if not link:
                _not_found_queue.put(record["title"])
            else:
                product = grab_product_page(conn, link, record["title"], record["row"])
                ProductSheetOneRR(product).save()

        except Exception as e:
            print(e, str(e))
        finally:
            _link_queue.task_done()

##########################################################

if __name__ == "__main__":

    # find info about product

    missing_product = SheetOne_RR().get_all_records()

    #################################

    for product in missing_product:
        _link_queue.put(product)

    for i in range(THREAD_NUM):
        worker = threading.Thread(target = grabber_worker, args = (i,))
        worker.daemon = True
        worker.start()

    print("Start waiting")
    _link_queue.join()
    print("End")

    # close http connections

    for conn in _http_conn:
        conn.close()

    not_founded = []
    while not _not_found_queue.empty():
        _title = _not_found_queue.get()
        not_founded.append(_title)

    # save in redis

    ProductSheetOneRR().save("navigator:sheet1:not_founded", { "titles":  not_founded })

##########################################################
# EOF