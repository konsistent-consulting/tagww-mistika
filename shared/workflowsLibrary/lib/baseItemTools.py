# v 1.0 adding setPropertiesFromJson

import json
from Mistika.classes import Cconnector

def setPropertiesFromJson(node,jsonObject):
    res=True
    for key in jsonObject:
        list=key.split('.')
        if len(list)>1:
            if list[0]!=node.objectName:
                continue
            prop=list[1]
        else:
            prop=list[0]
        value=jsonObject[key]
        if (not node.setProperty(prop,value)):
            res=False
            node.warning("setPropertiesFromJson","Unable to set property {}".format(key))
    return res
        
def totalNumberOfUPs(node):
    total=0
    inputs=node.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    for c in inputs:
        total=total+len(c.getUniversalPaths())
    return total
                
def totalNumberOfFilesInUPs(node):
    total=0
    inputs=node.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    for c in inputs:
        ups=c.getUniversalPaths()
        for up in ups:
            total=total+len(up.getAllFiles())
    return total
