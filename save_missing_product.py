#!/usr/bin/env python
#-*- coding: utf-8 -*-
##########################################################

__all__ = ["get_xls_rows", "exist_on_torsite"]

##########################################################

import os; from os import path as os_path
import urllib
import urllib2
import httplib
import Queue
import threading; from threading import Lock

import xlrd
from bs4 import BeautifulSoup, SoupStrainer
import redis

from xls_models import SheetOneRow
from redis_models import SheetOne_RR
import file_utils

##########################################################

XLS_FILENAME = "navigator.xls"
TOR_SITENAME = "tor-electro.ru"
THREAD_NUM = 5

##########################################################

class TorResultNotFound(Exception):
    def __init__(self, msg):
        super(TorResultNotFound, self).__init__(msg)

_tval = lambda c: c.value.encode("utf-8")

_tor_queue = Queue.Queue()
_product_missing = Queue.Queue()

_http_conn = []
_http_conn_lock = Lock()

##########################################################

def get_xls_rows(xls_filename):
    book = xlrd.open_workbook(xls_filename, encoding_override = "cp1252", formatting_info = True)
    sheet = book.sheet_by_index(0)
    return SheetOneRow(sheet).row_list()

##########################################################

def exist_on_torsite(conn, title, rownum):
    search_url = "http://%s/search?" % TOR_SITENAME
    params = {"search_text": title}
    headers = {
        "Content-Type" : "application/x-www-form-urlencoded",
        "Accept" : "text/html",
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:17.0) Gecko/20100101 Firefox/17.0",
        "Connection": "Keep-Alive",
        "Refer": "http://%s" % TOR_SITENAME
    }

    conn.request("POST", "/search", urllib.urlencode(params), headers)
    response = conn.getresponse()
    print response.getheaders()
    html_content = response.read()

    only_form_tags = SoupStrainer("form")
    soup = BeautifulSoup(html_content, parse_only = only_form_tags)
    form = soup.find_all("form", class_="mod-search-form ")[0]
    assert form, "Soup has no find html_form"
    p = form.find("p")
    text = p.contents[0].encode("utf-8").strip()
    print(text)
    print(title, rownum)

    if text.startswith("По Вашему запросу найдено"):
        return True
    elif text.startswith("Ничего не найдено"):
        return False
    else:
        print("text =", text, rownum)
        raise TorResultNotFound(text)

##########################################################

def tor_worker(self_id):
    conn = httplib.HTTPConnection(TOR_SITENAME)
    with _http_conn_lock:
        _http_conn.append(conn)

    while True:
        row = _tor_queue.get()

        try:
            if not exist_on_torsite(conn, row["title"], row["row"]):
                _product_missing.put(row)
        finally:
            _tor_queue.task_done()

##########################################################

if __name__ == "__main__":

    ### Parse xls ###

    if os_path.isfile(file_utils.PICKLE_FILENAME):
        titles = file_utils.load_pickle()
    else:
        titles = get_xls_rows(XLS_FILENAME)
        file_utils.write_pickle(titles)

    #### Filter missing product on tor-electro.ru ###

    temp_product = {}

    for title in titles:
        temp_product[title["row"]] = title
        _tor_queue.put(title)

    for i in range(THREAD_NUM):
        worker = threading.Thread(target = tor_worker, args = (i,))
        worker.daemon = True
        worker.start()

    print("Start waiting")
    _tor_queue.join()
    print("End")

    # close http connections
    for conn in _http_conn:
        conn.close()

    ### Save missing product to redis ###

    while not _product_missing.empty():
        row = _product_missing.get()
        SheetOne_RR(row).save()

##########################################################
# EOF