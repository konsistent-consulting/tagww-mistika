
# this simple example creates a couple of properties that can be accessed form a different workflow
# in order to accesss any of theses properties from a diferrent workflow node/property, use the following python code in the desired property :
# =__import__('Mistika').workflows.getWorkflow('Config').getNode('pyGlobalCOnfig').watchers
# where 'Config' is the workflow Name were this node is created and "watchers" the name of the property from this node to use

from Mistika.Qt import QColor
def init(self):
    self.color=QColor(225,225,210)
    self.addProperty("watchers") 
    self.addProperty("deliveries")
    return True

def isReady(self):
    res=True
    if self.watchers=="":
        res=self.critical("config:watchers","'Watchers' folder can not be empty") and res
    if self.deliveries=="":
        res=self.critical("config:deliveries","'Deliveries' folder can not be empty") and res
    return res

def process(self):
    return True
