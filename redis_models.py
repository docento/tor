#!/usr/bin/env python
#-*- coding: windows-1251 -*-
##########################################################

__all__ = ["RedisRecord", "RedisHashStruct", "SheetOne_RR", "ProductSheetOneRR"]

##########################################################

import redis

##########################################################

_tval = lambda cell: cell.value.encode("utf-8")

class NotImplemented(Exception):
    def __init__(self):
        Exception.__init__("this method must be ovveride in subclass")

##########################################################

# TODO: class ConnectionPool::Singleton

class RedisRecord:

    schema = "static"

    db_name = "users:admin"
    db_key_field = "title"

    cursor = None

    @classmethod
    def _pk(cls, key):
        if key.startswith(":"):
            key = "%s%s" % (cls.db_name, key)
        return key

    @classmethod
    def get_cursor(cls, host = "localhost", port = 6379, db = 0):
        if not cls.cursor:
            pool = redis.ConnectionPool(host = host, port = port, db = db)
            cls.cursor = redis.Redis(connection_pool=pool)
        return cls.cursor

    ###################################

    def __init__(self, fields = None):
        self.__dict__["fields"] = fields if fields else {}

    def __getattr__(self, attr_name):
        if attr_name == "fields":
            return self.__dict__["fields"]

        if attr_name in self.fields.keys():
            return self.fields[attr_name]
        else:
            raise AttributeError("Can't find attr")

    def __setattr__(self, attr_name, value):
        if attr_name == "fields":
            self.__dict__["fields"] = value
            return

        if "schema" not in self.__class__.__dict__.keys():
            self.fields[attr_name] = value
            return

        if attr_name in self.fields.keys():
            self.fields[attr_name] = value
        else:
            raise AttributeError("Can't find attr")

    def save(self, key):
        raise NotImplemented()

    def get(self, key):
        raise NotImplemented()

class RedisHashStruct(RedisRecord):

    def save(self, key = None, fields = None):
        if fields:
            self.fields = fields
        if not self.fields:
            raise Exception("Empty fields")
        if key is None:
            key_field = self.__class__.db_key_field
            if key_field not in self.fields.keys():
                raise Exception("Default key_field = %s not in self.fields" % key_field)
            key = self.__class__._pk(":" + str(self.fields[key_field]) )

        cursor = self.__class__.get_cursor()
        cursor.hmset(key, self.fields)

        if self.fields.get("row"):
            cursor.lpush(self.__class__.db_name + ":keys", self.fields["row"])

    def get(self, key):
        cursor = self.__class__.get_cursor()

        if key.startswith(":"):
            key = self.__class__._pk(key)

        res = cursor.hgetall(key)
        self.fields = res
        return self

    def get_all_records(self):
        result = []

        cursor = self.__class__.get_cursor()
        keys_list = cursor.lrange(self.__class__.db_name + ":keys", 0, -1)

        for k in keys_list:
            r = self.get(":" + k)
            result.append( r.fields )

        return result

    def get_all_keys(self):
        cursor = self.__class__.get_cursor()
        return cursor.lrange(self.__class__.db_name + ":keys", 0, -1)

class SheetOne_RR(RedisHashStruct):
    schema = "static"

    db_name = "xls:missing:sheet1:by_id"
    db_key_field = "row"

class RR(RedisHashStruct):
    pass

##########################################################

class ProductSheetOneRR(RedisHashStruct):

    db_name = "navigator:sheet1:by_id"
    db_key_field = "row"

##########################################################

def run_tests():

    SheetOne_RR().get_all_records()

##########################################################

if __name__ == "__main__":
    run_tests()

##########################################################
# EOF
