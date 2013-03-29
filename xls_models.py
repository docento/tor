#!/usr/bin/env python
#-*- coding: windows-1251 -*-
##########################################################

__all__ = [ "XlsParser", "SheetOneRow" ]

##########################################################

_tval = lambda cell: cell.value.encode("utf-8")

class NotImplemented(Exception):
    def __init__(self, msg = "This method must be ovveride in subclass"):
        Exception.__init__(msg)

##########################################################

class XlsParser:

    extracted_columns = dict()
    list_by_column = 0

    @classmethod
    def exclude_rules(cls, cell):
        raise NotImplemented()

    ##########################################

    def __init__(self, sheet):
        self.sheet = sheet
        self.result = []
        self.available_row_list = []
        self.merged_cells = self.get_merged_cells() # [{cownum: (row_start, row_end)}, {..,}, ...]

    def __getstate__(self):
        return self.result

    def get_merged_cells(self):
        need_columns = self.__class__.extracted_columns.values()
        merged_list = {}

        for i in need_columns:
            merged_list[i] = []

        for crange in self.sheet.merged_cells:
            rlo, rhi, clo, chi = crange
            if clo in need_columns:
                merged_list[clo].append((rlo, rhi,))

        return merged_list

    def row_list(self):
        for rownum in range(self.sheet.nrows):
            cell = self.sheet.cell(rownum, self.__class__.list_by_column)

            if self.pass_row(cell):
                continue

            self.available_row_list.append(rownum)
            self.add_result(rownum)

        return self.result

    def add_result(self, rownum):
        column = dict()
        for column_name, colx in self.__class__.extracted_columns.items():
            cell = self.sheet.cell(rownum, colx)

            cell_value = cell.value

            # if cell is merged, cell_value placed in first cell
            if cell_value == "":
                if colx in self.merged_cells.keys():
                    ranges = self.merged_cells[colx]

                    # find range
                    for r in ranges:
                        if rownum in range(r[0], r[1]) and r[0] in self.available_row_list:
                            cell = self.sheet.cell(r[0], colx)
                            cell_value = cell.value
                            break

            cell_value = self.parse_cell_value(cell, cell_value)
            column.update({ column_name: cell_value })

        column.update({ "row": rownum + 1 })
        self.result.append(column)

    def parse_cell_value(self, cell, value):

        CELL_EMPTY   = 0  # u""
        CELL_TEXT    = 1  # u"text unicode"
        CELL_NUMBER  = 2  # float
        CELL_DATE    = 3  # float
        CELL_BOOLEAN = 4  # 1 => True, 0 => False
        CELL_BLANK   = 6  # u""

        cell_type = cell.ctype

        if cell_type == CELL_EMPTY:
            return None
        elif cell_type == CELL_TEXT:
            return value.encode("utf-8")
        elif cell_type == CELL_NUMBER:
            return float(value)
        elif cell_type == CELL_DATE:
            raise NotImplemented("value %s need convert to datetime format" % value)
        elif cell_type == CELL_BOOLEAN:
            return bool(value)
        elif cell_type == CELL_BLANK:
            return None
        else:
            raise NotImplemented("Cell type not recognized")

    def pass_row(self, cell):
        for rule in self.__class__.exlude_rules(cell):
            if rule:
                return True

        return False

##########################################################

class SheetOneRow(XlsParser):

    extracted_columns = dict \
    (
        power = 2,
        color_temp = 3,
        base_code1 = 4,
        base_code2 = 5,
        title = 6,
        price = 7
    )

    list_by_column = extracted_columns["title"]

    @staticmethod
    def exlude_rules(cell):
        return [
            (cell.ctype in [0, 5, 6]),
            (cell.ctype in [1, 2, 3, 4] and
                    (_tval(cell).startswith("Код продукта") or
                     _tval(cell).startswith("Справочная")))
        ]

##########################################################

def run_tests():
    import xlrd;

    book = xlrd.open_workbook("navigator.xls",
                              encoding_override = 'cp1252',
                              formatting_info = True)
    sheet = book.sheet_by_index(0)

    s = SheetOneRow(sheet)
    for r in s.row_list()[:37]:
        print(r)
    # SheetOneRow.exlude_rules(12)

##########################################################

if __name__ == "__main__":
    run_tests()

##########################################################
# EOF