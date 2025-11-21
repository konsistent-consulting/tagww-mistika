from Mistika.classes import Cconnector
from Mistika.Qt import QColor
import Mistika
from baseItemTools import totalNumberOfUPs

def init(self):
    res = True
    self.setClassName("Change Resolution")
    self.color = QColor(0x677688)
    self.addConnector("input", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("output", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)

    self.addProperty("scaleFactor", 1.00)
    self.addProperty("forceEvenRes", True)

    preResolutions = ["--- Same As Input ---", "--- Custom ---"]
    self.addProperty("_resolutionList", preResolutions + list(Mistika.app.getResolutionNames()))
    self.addProperty("resolution", "--- Same As Input ---")
    self.addProperty("imageResX", 1920)
    self.addProperty("imageResY", 1080)
    self.addProperty("mode", 0)

    self.addProperty("dstNode")

    self.bypassSupported = True
    self.setAcceptConnectors(True, "input")
    onPropertyUpdated(self,"mode")
    return res


def isReady(self):
    res = True
    if (self.bypassSupported and self.bypassEnabled):
        return True
    return res


def process(self):
    res = True
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    output = self.getFirstConnectorByName("output")
    output.clearUniversalPaths()

    dstNode = self.evaluate(self.dstNode).strip()
    mode = self.mode
    scaleFactor = float(self.scaleFactor)
    forceEvenRes = self.forceEvenRes

    resolution = self.resolution
    resX = self.imageResX
    resY = self.imageResY

    if self.bypassEnabled:
        for c in inputs:
            for up in c.getUniversalPaths():
                output.addUniversalPath(up)
        return True

    keyRes = dstNode + ".resolution"
    keyResX = dstNode + ".imageResX"
    keyResY = dstNode + ".imageResY"

    self.setComplexity(totalNumberOfUPs(self)*100)
    current=0
    self.progressUpdated(current)
    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            properties = up.getPrivateData("propertiesOverride")

            if properties == None:
                properties = {}

            try:
                data = up.getMetadata()["clip"]["image"]["resolution"]
                par = up.getMetadata()["clip"]["image"]["pixelAspectRatio"]
                print (par)
                if int(mode) == 0:
                    properties[keyResX] = int(int(data["resolutionX"]) * scaleFactor)
                    properties[keyResY] = int(int(data["resolutionY"]) * scaleFactor)
                else:
                    if resolution == "--- Same As Input ---":
                        output.addUniversalPath(up)
                        return res
                    if resolution == "--- Custom ---":
                        aspectRatio = int(data["resolutionX"]) / (int(data["resolutionY"]/float(par)))
                        if resX == 0 and resY != 0:
                            properties[keyResX] = round(resY * aspectRatio)
                            properties[keyResY] = resY
                        elif resY == 0 and resX != 0:
                            properties[keyResX] = resX
                            properties[keyResY] = round(resX / aspectRatio)
                        elif resX == 0 and resY == 0:
                            properties[keyResX] = int(data["resolutionX"])
                            properties[keyResY] = int(data["resolutionY"])
                        else:
                            properties[keyResX] = resX
                            properties[keyResY] = resY
                    else:
                        width, height = resolution.split('x')
                        properties[keyResX] = int(width)
                        properties[keyResY] = int(height)
                        print(properties[keyResX], properties[keyResY])

                if forceEvenRes:
                    # properties[keyResX] = int(properties[keyResX] / 2) * 2
                    # properties[keyResY] = int(properties[keyResY] / 2) * 2
                    if properties[keyResX]%2 != 0:
                        properties[keyResX] += 1
                    elif properties[keyResY]%2 != 0:
                        properties[keyResY] += 1
                print(properties[keyResX],properties[keyResY])


                properties[keyRes] = "--- Custom ---"
                up.setPrivateData("propertiesOverride", properties)
            except KeyError as e:
                return self.critical("changeResolution:error", "File has no key {}".format(e))
            output.addUniversalPath(up)
            current+=1
            self.progressUpdated(current*100)
    
    self.progressUpdated(self.complexity())
    return res


def onPropertyUpdated(self, name):
    try:
        if name == "mode":
            self.setPropertyVisible("scaleFactor", int(self.mode) == 0)
            # self.setPropertyVisible("forceEvenRes", int(self.mode) == 0)

            self.setPropertyVisible("resolution", int(self.mode) == 1)
            self.setPropertyVisible("imageResX", int(self.mode) == 1 and self.resolution == "--- Custom ---")
            self.setPropertyVisible("imageResY", int(self.mode) == 1 and self.resolution == "--- Custom ---")

        if name == "resolution":
            self.setPropertyVisible("imageResX", self.resolution == "--- Custom ---")
            self.setPropertyVisible("imageResY", self.resolution == "--- Custom ---")
            # self.setPropertyVisible("forceEvenRes", int(self.mode) == 1)
    except AttributeError:
        pass