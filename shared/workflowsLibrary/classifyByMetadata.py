from logging import critical
from Mistika.Qt import QColor
from Mistika.classes import Cconnector, CnameConvention, CuniversalPath
import Mistika
import json
import os
from baseItemTools import totalNumberOfUPs

CLASSIFYBYMETADATA_PRESETS_JSON = "/classifyByMetadata/presets.json"
CLASSIFYBYMETADATA_PRESETS_JSON_EXAMPLE = "{\"presets\": [[\"custom\", \"value0, value1, value2, value3\"], [\"fps\", \"23.98, 24.00, 25.00, 29.97, 30.00, 60.00, 120.00\"], [\"resolution\", \"1920X1080, 2048X1080, 2048X1536, 2048X1556, 3840X2160, 4096X2160, 7680X4320\"]]}"


class CmetadataAssistant:
    def __init__(self, node):
        self.m_node = node
        self.m_cosmeticName = {'default': self.cosmeticNameDefault,
                               'fps': self.cosmeticNameFPS}  # define conversion cosmetic here

    def getMetadataValue(self, up, name):
        mfid = up.getMediaFileInfoData()
        if mfid.dataTree() == {}:
            up.readMetadataFromFile()
            mfid = up.getMediaFileInfoData()

        res = mfid.getStringKeyValue(mfid.endsStringKeyToMediaDataFieldStringKey(name))
        if self.m_node.useDecoratedValues:
            res = mfid.getTokenDecorated(name)

        if res == None: return None

        if name in self.m_cosmeticName:
            res = self.m_cosmeticName[name](res)
        else:
            res = self.m_cosmeticName['default'](res)
        return res

    def cosmeticNameDefault(self, value):
        return value

    def cosmeticNameFPS(self, value):
        roundedValue = str(round(value, 2))  # keep 2 decimals (rounded)
        return roundedValue


def init(self):
    self.setClassName("Classify By Metadata")
    jsonPath = Mistika.sgoPaths.workflowsLibrary() + CLASSIFYBYMETADATA_PRESETS_JSON
    try:
        f = open(jsonPath)
        self.addProperty("jsonString", f.read())
    except Exception:
        self.addProperty("jsonString", CLASSIFYBYMETADATA_PRESETS_JSON_EXAMPLE)
    print(self.jsonString, " aa")
    self.addProperty("presets")
    self.presets = json.loads(self.jsonString)["presets"]
    print(self.presets, " bb")
    self.addProperty("_presetList", [group[0] for group in self.presets])
    self.addProperty("caseSensitive", True)
    self.addProperty("useDecoratedValues", True)
    self.addProperty("filterMode", 0)
    self.addProperty("errorMode", 0)

    self.addProperty("dataType")
    self.addProperty("outputList")

    self.addProperty("preset", 0)
    # creating connectors
    self.addConnector("files", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_REQUIRED)
    self.addConnector("notFound", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("other", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)

    extList = self.outputList.split(",")
    if not self.caseSensitive:
        extList = self.outputList.lower().split(",")
    for ext in extList:
        ext = ext.strip()
        if ext:
            self.addConnector(ext.strip(), Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True, "files")
    # configuring the node
    self.bypassSupported = True
    self.color = QColor(0x677688)
    return True


def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    dataType = self.evaluate(self.dataType).strip()
    outputList = self.evaluate(self.outputList).strip()
    if dataType == "":
        res = self.critical("classifyByMetadata:isReady", "'datatype' can not be empty") and res
    if int(self.errorMode) < 0 or int(self.errorMode) > 3:
        res = self.critical("classifyByMetadata:isReady", "Invalid errorMode {}".format(self.errorMode),
                            "errorMode") and res
    return res


def process(self):
    res = True
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    outputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_OUTPUT)
    dataType = self.evaluate(self.dataType).strip()
    caseSensitive = self.caseSensitive
    useDecorated = self.useDecoratedValues
    filterMode = int(self.filterMode)
    func = [None, self.info, self.warning, self.critical][int(self.errorMode)]

    for c in outputs:
        c.clearUniversalPaths()
    
    self.setComplexity(totalNumberOfUPs(self))
    if self.bypassEnabled:
        self.progressUpdated(self.complexity())
        return True

    currentProgress=0
    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False

            currentProgress=currentProgress+1
            self.progressUpdated(currentProgress)
            metadataAssistant = CmetadataAssistant(self)
            v = metadataAssistant.getMetadataValue(up, dataType)
            print(v)

            if not caseSensitive and v is not None:
                v = str(v).lower()

            if v == None:
                if func:
                    res = func("classifyByMetadata:process:ext",
                               "'{}' is not a metadata value of '{}'. Sent to 'notFound'".format(dataType,
                                                                                                 up.getFileName()), "")
                out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "notFound")
                out.addUniversalPath(up)
            else:
                classified = False
                if caseSensitive:
                    outputList = self.outputList.replace(" ", "").split(",")
                else:
                    outputList = list(set(self.outputList.lower().replace(" ", "").split(",")))

                for case in outputList:
                    out = None

                    if (filterMode == 0 and v == case) or (filterMode == 1 and v.startswith(case)) or (
                            filterMode == 2 and case in v) or (filterMode == 3 and v.endswith(case)):
                        out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, case)

                    if out:
                        self.info("classifyByMetadata:process:info",
                                  "sending '{}' to '{}'".format(up.getFileName(), case), "")
                        classified = True
                        out.addUniversalPath(up)

                if not classified:
                    if func:
                        res = func("classifyByMetadata:process:ext",
                                   "'{}' has '{}' of value '{}', not in output list. Sent to 'other'".format(
                                       up.getFileName(), dataType, v), "") and res
                    out = self.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT, "other")
                    out.addUniversalPath(up)
    
    self.progressUpdated(self.complexity())
    return res


def onPropertyUpdated(self, name):
    if name == "preset":
        try:
            self.presets = json.loads(self.jsonString)["presets"]
            # Buscar la tupla donde el primer elemento coincida con self.preset
            matched = next(item for item in self.presets if item[0] == self.preset)
            print("mached",matched[0])
            print("matched1",matched[1])
            self.dataType = matched[0]
            self.outputList = matched[1]
            self.rebuild()
        except Exception:
            print("pass")
            pass
    if name == "outputList":
        self.rebuild()

    if name == "caseSensitive":
        self.rebuild()
