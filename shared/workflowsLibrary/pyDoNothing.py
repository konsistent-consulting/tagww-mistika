## @file pyDoNothing.py
#  Python Node Example.
#
# This example creates a Task with one input and one output
# On execution, it sends to the output the file name connected to the input (if any)
# This example does not process the input file.

from Mistika.classes import Cconnector

## The Initialization Function
#
#  This constructor creates 2 nodes. one for the input, and one for the output. Both Nodes are optional.
#  @param self The Cpython Node pointer.
def init(self):
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("output",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.bypassSupported=True
    return True

## The Validation function
#
#  This function checks if the the node is ready to be processed.
#  @param self The Cpython Node pointer. 
#  @return Always True, To indicate the node is always ready 
def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    return True

## The Process function
#  In this example, the process function copies the contents of the input connector into the output connector (sending the input to the output without further processing)
#  @param self The Cpython Node pointer.      
#  @return Always True, To indicate the process has always been successful 
def process(self):
    input=self.getFirstConnectorByName("input")
    output=self.getFirstConnectorByName("output")
    output.clearUniversalPaths()
    if self.bypassEnabled:
        return True
    output.setUniversalPaths(input.getUniversalPaths())
    return True