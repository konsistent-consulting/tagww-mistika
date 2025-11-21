from Mistika.Qt import QColor
from Mistika.classes import Cconnector

def init(self):
    self.color=QColor(0x677688)
# creating properties
    self.addProperty("inputs","input0, input1, input2")
    self.addProperty("outputs","output0, output1, output2")

#creating connectors
    inputList=self.inputs.split(",")
    if inputList != [""]:
        for inputCase in inputList:
            self.addConnector(inputCase.strip(),Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)

    outputList=self.outputs.split(",")
    if outputList != [""]:
        for outputCase in outputList:
            self.addConnector(outputCase.strip(),Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)

#configuring the node
    self.bypassSupported=True
    self.color=QColor(0,180,180)
    return True

def isReady(self):
    #Always ready to prototype!
    return True

def process(self):
    #No process just WOW
    return True

def  onPropertyUpdated(self,name):
    if name=="inputs":
        self.rebuild()
    if name=="outputs":
        self.rebuild()
