#!/usr/bin/env python
#-*- coding: windows-1251 -*-
##########################################################

__all__ = [ "TorProduct" ]

##########################################################

import mimetypes
import os; from os import path as os_path

import redis

from redis_models import SheetOne_RR, ProductSheetOneRR
from file_utils import get_image_from_archive

##########################################################

class TorProduct:

    form_name = "product"
    parent = "cat_id"

    form_fields = {
        "brand":           "Navigator",
        "image_full_size": "on",
        "cat_id":        None,
        "title":         None,
        "price":         None,
        "sku":           None,
        "body":          None,
        "id":            None,
        "unit":          None,
        "remains":       None,
        "anounce":       None,
        "feature_title": None
    }


    def create_form_fields(self):
        fields = {}
        for name, v in self.fields.items():
            key = "{model}[{field}]".format(model = TorProduct.form_name,
                                            field = name)
            fields[key] = v if v else ""
        return fields

    def __init__(self, row, parent_id = None):
        self.parent_id = parent_id
        self.fields = TorProduct.form_fields.copy() #
        self.files = None

        self.fill_fields(row)

        self.fields = self.create_form_fields()

    def fill_fields(self, row):
        xls = SheetOne_RR().get(row)
        np = ProductSheetOneRR().get(row)

        self.fields["cat_id"] = str(self.parent_id)
        self.fields["title"]  = "%s %s %s" % (xls.title, row, np.photo_name)
        self.fields["price"]  = str(xls.price)
        self.fields["sku"]    = str(int(float(xls.base_code1))) + xls.base_code2
        self.fields["body"]   = self._prepare_body(np.desc, xls.color_temp, xls.power)

        p = os_path.join(os.getcwd(), "photo")
        archive_path = os_path.join(p, np.photo_name)
        self.files = [("product[image]", np.photo_name,
                       lambda: get_image_from_archive(archive_path, ends = np.photo_empiric_name) )]

    def _prepare_body(self, desc, temp, power):
        cokole, color_temp = temp.split(",")
        html = """<p>{desc}</p>
                  <table>
                    <tbody>
                        <tr>
                            <td><strong>Мощность:</strong></td>
                            <td><strong>{power} Вт</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Цветовая температура:</strong></td>
                            <td><strong>{color_temp}</strong></td>
                        </tr>
                        <tr>
                            <td><strong>Цоколь:</strong></td>
                            <td><strong>{cokole}</strong></td>
                        </tr>
                    </tbody>
                  </table>"""
        # TODO: regexp
        try:
            power = str(int(float(power)))
        except:
            pass

        return html.format(desc = desc, power = power,
                           color_temp = color_temp.strip(),
                           cokole = cokole.strip())

    def add(self):
        result = {}
        result["url"] = "/product/%s/add" % self.parent_id
        result["method"] = "POST"

        content_type, body = self.post_multipart()

        result["params"] = body
        result["headers"] = [{ "content-type": content_type }]

        return result

    def post_multipart(self):
        fields = self.fields
        files = self.files

        LIMIT = "---------------------------18075586539976118481281949986"
        CRLF = "\r\n"
        result = []

        for field, value in fields.items():
            result.append('--' + LIMIT)
            result.append('Content-Disposition: form-data; name="%s"' % field)
            result.append('')
            result.append(value)

        for key, filename, value in files:
            result.append('--' + LIMIT)
            result.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
            result.append('Content-Type: %s' % self._get_content_type(filename))
            result.append('')
            result.append(value())

        result.append('--' + LIMIT + '--')
        result.append('')
        body = CRLF.join(result)
        content_type = 'multipart/form-data; boundary=%s' % LIMIT
        return content_type, body

    def _get_content_type(self, filename):
        return mimetypes.guess_type(filename)[0] or 'application/octet-stream'


##########################################################

def run_tests():

    r = TorProduct(":130", parent_id = 131).add()
    for k, v in r.items():
        print k, v

    # SheetOne_RR().get_all_records()
    # row = 5
    # xls_row = get_xls_row(row)
    # nav_row = Navigator_RR().get(row)
    # product = TorProduct(xls_row, nav_row)
    # product.add()

##########################################################

if __name__ == "__main__":
    run_tests()

##########################################################
# EOF