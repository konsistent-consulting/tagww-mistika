from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import Mistika
import json
import os

CHANGECURVESDATA_USER_PRESETS_JSON = "/changeCurvesData/presets.user.json"
CHANGECURVESDATA_PRESETS_JSON = "/changeCurvesData/presets.json"
CHANGECURVESDATA_USER_PRESETS_JSON_EXAMPLE = "{\"presets\":[[\"userPreset1\", {  \"key1\":\"value1\",   \"key2\":2,\"key3\":true}],[\"userPreset2\",{\"key1\":\"value3\",   \"key2\":4,\"key3\":false}]]}"

def init(self):
    res = True
    self.setClassName("Change Curves Data") 
    self.color=QColor(0x677688)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)

    self.addProperty("jsonsReadCorrectly", True)
    self.addProperty("preset")
    self.addProperty("jsonCurvesData")
    self.addProperty("_presetKeyList")
    self.addProperty("_finalPresetsList")
    self.addProperty("customJsonCurvesData")

    userJsonPath = Mistika.sgoPaths.workflowsLibrary()+ CHANGECURVESDATA_USER_PRESETS_JSON

    if os.path.exists(userJsonPath):
        uf = open(userJsonPath)
    else:
        f = open(userJsonPath, "w")
        data = json.loads(CHANGECURVESDATA_USER_PRESETS_JSON_EXAMPLE)
        json.dump(data, f)

    try:
        f = open(Mistika.sgoPaths.workflowsLibrary()+ CHANGECURVESDATA_PRESETS_JSON)
        presetsJson = json.load(f)   
        userPresetsJson = json.load(uf)  
    except (ValueError,IOError) as e:
        self.jsonsReadCorrectly = False
        res = self.critical("changeCurvesData:innit:userPresetsJson", "'presetsJson' has errors: {}".format(e)) and res


    if(self.jsonsReadCorrectly):
        finalPresetList = presetsJson["presets"] + userPresetsJson["presets"]
        self._finalPresetsList = finalPresetList

        presetKeyList = []
        for preset in finalPresetList:
            presetKeyList.append(preset[0])
        self._presetKeyList = presetKeyList
    else:
        self._presetKeyList = ["Error"]
        self._finalPresetsList = [["Error", "{}"]]

    self.bypassSupported=True
    self.setAcceptConnectors(True, "input")
    return res

def isReady(self):
    if (self.bypassSupported and self.bypassEnabled):
        return True
    if not self.jsonsReadCorrectly:
        self.warning("changeCurvesData:isready:jsonCurvesData", "There is an error in preset json files")
    res = True
    if not self.evaluate(self.jsonCurvesData).strip():
        return True
    else:
        try:
            json.loads(self.evaluate(self.jsonCurvesData).strip())
        except ValueError as e:
            res = self.critical("changeCurvesData:isready:jsonCurvesData", "'jsonCurvesData' has errors: {}".format(e)) and res
    return res

def process(self):
    res = True
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output=self.getFirstConnectorByName("output")
    output.clearUniversalPaths()
    jsonString = self.evaluate(self.jsonCurvesData).strip()
   
    if self.bypassEnabled:
        for c in inputs:
            for up in c.getUniversalPaths():
                output.addUniversalPath(up)
        return True

    if not jsonString:
        jsonString = "{}"
    jsonCurvesData = json.loads(jsonString)

    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            curvesMap = up.getPrivateData("CurvesData")
            if curvesMap == None:
                curvesMap = {}
            for key in jsonCurvesData:
                curvesMap[key] = jsonCurvesData[key]
            up.setPrivateData("CurvesData", curvesMap)
            output.addUniversalPath(up)
    return res

def  onPropertyUpdated(self,name):
    try:
        if name=="preset":
            if (self.preset == "Custom" or self.preset == ""):
                self.jsonCurvesData = self.customJsonCurvesData
            else:
                self.jsonCurvesData = json.dumps(self._finalPresetsList[self._presetKeyList.index(self.preset)][1])
        elif name == "jsonCurvesData" and (self.preset == "Custom" or self.preset == "") and not self.jsonCurvesData == "":
            self.customJsonCurvesData = self.evaluate(self.jsonCurvesData).strip()
        elif name == "customJsonCurvesData" and (self.preset == "Custom" or self.preset == "") and not self.customJsonCurvesData == self.jsonCurvesData:
            self.jsonCurvesData = self.evaluate(self.customJsonCurvesData).strip()
    except (AttributeError,IndexError,ValueError):
        pass
 