import Mistika
from Mistika.Qt import QColor
from Mistika.classes import CnameConvention,CuniversalPath
import xml.etree.ElementTree as ET
import os.path

class XMLtoXLSXtools: 
    def __init__(self, node):
        self.m_node = node

    def loadConfigXML(self, configXML):
        try:
            config = ET.parse(configXML)
            return config.getroot()
        except ET.ParseError as e:
            return self.m_node.critical("XMLtoXLSX:parseError","Error parsing configXML file '{}': {}".format(configXML, e))
        
    def loadContentXML(self, f, rootConfig):
        try:
            xml = ET.parse(f, parser=ET.XMLParser(encoding="utf-8"))
            rootXml = xml.getroot()
            if "itemRoot" in rootConfig.attrib:
                rootXml = xml.find(rootConfig.attrib["itemRoot"])
            return rootXml
        except ET.ParseError as e:
            return self.m_node.critical("XMLtoXLSX:parseError","Error parsing data XML file '{}': {}".format(f, e))
    
    def writeColumnTitle(self, i, item, worksheet):
        if "to" in item.attrib:
            titleValue = item.attrib["to"]
        else:
            titleArray = item.attrib["from"]
            titleSplit = titleArray.split("/")
            titleValue = titleSplit[len(titleSplit)-1]
        worksheet.cell(row = 1, column = i+1, value = titleValue)
    
    def writeRow(self, rootConfig, row, rootXml, content, workSheet):
        for i, item in enumerate(rootConfig):  
            self.writeCellValue(i, row, item, rootXml, content, workSheet)
        
    def writeCellValue(self, i, j, item, rootXml, child, worksheet):
        if item.attrib["from"] == rootXml.tag:
            cellValue = rootXml
        elif item.attrib["from"] == child.tag:
            cellValue = child
        else:
            search = item.attrib["from"]
            if search.startswith(child.tag):
                search = search.replace(child.tag + "/", "")

            #If it has extra attributes, use them to filter. Create proper XPath xpresion
            for attrib in item.attrib:
                if attrib != "from" and attrib != "to" and attrib != "getValueFromProperty":
                    search = search + "[@" + attrib + "='" + item.attrib[attrib] + "']"
            try:
                #print(search)
                cellValue = child.find(search)
            except IndexError:
                cellValue = None

        if not cellValue == None:
            if "getValueFromProperty" in item.attrib:
                propertyName = item.attrib["getValueFromProperty"]
                cellValue = cellValue.attrib[propertyName]
            else:
                cellValue = cellValue.text
        else:
            if item.attrib["from"] == "python":                     
                try: 
                    # print(item.attrib["to"])
                    exec(item.text, globals(), locals())
                    func = locals()["xml2xlsxPythonProperty"]
                    cellValue = func(self.m_node, child)
                except Exception as e:
                    #print("Error evaluating function definition:", e)
                    a=1
                locals().pop("xml2xlsxPythonProperty", None)
            else:
                cellValue = ""

        worksheet.cell(row = j+2, column = i+1, value = cellValue)
