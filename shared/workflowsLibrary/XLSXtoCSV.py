from Mistika.Qt import QColor
from Mistika.classes import Cconnector
from Mistika.classes import CuniversalPath, CnameConvention
import xml.etree.ElementTree as ET
import openpyxl
import xlrd
from pyxlsb import open_workbook as open_xlsb
import csv


def init(self):
    self.setClassName("XLSX to CSV")
    self.color=QColor(0x677688)
# creating properties
    self.addProperty("delimiter", ";")
    self.addProperty("dstPath")
#creating connectors
    self.addConnector("xlsx",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_REQUIRED)
    self.addConnector("csv",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"xlsx")
#configuring the node
    self.bypassSupported=True
    self.color=QColor(0,180,180)
    return True


def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    if not self.delimiter:
        res=self.critical("XMLtoXLSX:configXML:empty","'delimiter' can not be empty") and res
    if len(self.delimiter) > 1:
        res=self.critical("XMLtoXLSX:configXML:empty","'delimiter' has to be 1 character") and res
    return res


def process(self):
    #And finally, Do the thing here!
    res=True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output=self.getFirstConnectorByName("csv")

    dstPath=self.evaluate(self.dstPath).strip()  

    output.clearUniversalPaths()
    if self.bypassEnabled:
        return True

    for c in inputs:                                 
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            f = up.getFilePath()     

            dst=self.composeDstFilePath(dstPath,up,False,0)
            dst.setExtension("csv")
  
            if not f.endswith((".xlsx", ".xls", ".xlsb")):
                self.critical("XMLtoXLSX:notXML", "The file'{}' is not an XLSX, XLS, or XLSB, cannot convert to CSV".format(f))
                continue

            if f.endswith(".xlsx"):
                newWorkbook = openpyxl.load_workbook(f)
                firstWorksheet = newWorkbook.active
            elif f.endswith(".xls"):
                newWorkbook = xlrd.open_workbook(f)
                firstWorksheet = newWorkbook.sheet_by_index(0)
            elif f.endswith(".xlsb"):
                newWorkbook = open_xlsb(f)
                firstWorksheet = newWorkbook.get_sheet(newWorkbook.sheets[0])

            OutputCsvFile = csv.writer(open(dst.getFilePath(), 'w'), delimiter=self.delimiter)
            
            if f.endswith(".xlsx"):
                for eachrow in firstWorksheet.rows:
                    OutputCsvFile.writerow([cell.value for cell in eachrow])
            elif f.endswith(".xls"):
                for row_idx in range(firstWorksheet.nrows):
                    row = firstWorksheet.row(row_idx)
                    OutputCsvFile.writerow([cell.value for cell in row])
            elif f.endswith(".xlsb"):
                for row in firstWorksheet.rows():
                    OutputCsvFile.writerow([item.v for item in row]) 

            output.addUniversalPath(dst)
    return res