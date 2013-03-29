#!/usr/bin/env python
#-*- coding: utf-8 -*-
##########################################################

__all__ = [ "ContentManager", "create_card" ]

##########################################################

import os; from os import path as os_path
import urllib
import urllib2
import httplib
import Queue
import threading; from threading import Lock
import mimetypes

from bs4 import BeautifulSoup, SoupStrainer

from xls_models import SheetOneRow
from redis_models import SheetOne_RR, ProductSheetOneRR
from tor_models import TorProduct
import file_utils

##########################################################

SITENAME    = ""
ADMIN_LOGIN = ""
ADMIN_PWD   = ""

##########################################################

def login():
    return manager.go("/login", {"login[login]": ADMIN_LOGIN,
                          "login[password]": ADMIN_PWD},
                          "POST", ajax = True)

def check_admin(category_id):
    manager.go("/product/%s/edit" % category_id)

def logout():
    manager.go("/logout")
    manager.bye()

def index():
    return manager.go("/")

##########################################################

def create_card(test_cat_id, row_num):
    p = TorProduct(row_num, parent_id = test_cat_id).add()

    return manager.go(url = p["url"], params = p["params"], method = p["method"],
                      headers = p["headers"])

##########################################################

def create_category(name, parent_id = None):
    return manager.go("/product/add", {"product_category[title]": name,
                                "product_category[parent_id]": ""},
                                "POST")

def delete_category(item_id):
    return manager.go("/product/%s/delete" % item_id, params = None, method = "POST")

##########################################################

class ContentManager:

    conn = None

    @classmethod
    def get_connection(cls):
        conn = cls.conn
        if conn is None:
            conn = httplib.HTTPConnection(SITENAME)
        return conn

    def __init__(self):
        self.sitename = SITENAME
        self.conn = self.__class__.get_connection()
        self.headers = {
            "content-type" : "application/x-www-form-urlencoded",
            "Accept" : "text/html",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:17.0) Gecko/20100101 Firefox/17.0",
            "Referer": "http://tor-electro.ru",
            "Connection": "Keep-Alive"
        }

    def bye(self):
        self.conn.close()
        print("[Manger]: bye-bye")

    def go(self, url = None, params = None, method = "GET", ajax = False, upload = False, headers = None):

        if headers:
            for d in headers:
                self.headers.update(d)

        if params and self.headers["content-type"] == "application/x-www-form-urlencoded":
            params = urllib.urlencode(params)

        # if ajax:
        #     self.headers.update({ "x-requested-with": "XMLHttpRequest" })

        # if url.endswith("delete"):
        #     self.headers.update({ "Content-length": "0" })

        # if upload:
        #     self.headers.update({"Content-Type": upload})

        self.conn.request(method, url, params, self.headers)
        response = self.conn.getresponse()

        res_html = response.read()
        res_headers = response.getheaders()

        res_status = response.status

        print("[{0}] {1} => {2} ===========================".format(method, url, res_status))
        print("status", res_status)
        print(res_headers)

        # delete headers on rq
        if headers:
            if self.headers["content-type"] != "application/x-www-form-urlencoded":
                self.headers["content-type"] = "application/x-www-form-urlencoded"
            if "x-requested-with" in self.headers.keys():
                self.headers.pop("x-requested-with")

        # if ajax:
        #     self.headers.pop("x-requested-with")
        # if upload:
        #     self.headers.update({"Content-Type": "application/x-www-form-urlencoded"})

        # update cookie
        for (h, v) in res_headers:
            if "set-cookie" == h:
                if len(v.split(";")) == 3:
                    cookie = v.split(";")[1].split(",")[1].strip()
                else:
                    cookie = v.split(";")[0].strip()
                self.headers.update({ "Cookie": cookie})

        return res_html


if __name__ == "__main__":

    manager = ContentManager()
    products = ProductSheetOneRR().get_all_records()

    ############################

    login()

    for item in products:
        p = create_card("131", ":%s" % item["row"])
        print(p)

    logout()

    ############################

    # index()
    # p = login()
    # print(p)
    # p = delete_category("129")
    # p = get_options()
    # p = create_category("Принглс")
    # print(p)
    # p = check_admin("125") #125 - unpublished, 111 - publilshed
    # p = create_card("130", ":100") # 130 - test_category_id
    # print(p)
    # logout()

    ############################3


##########################################################
# EOF
