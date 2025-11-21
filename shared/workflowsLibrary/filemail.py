from Mistika.classes import Cconnector
import Mistika
from Mistika.Qt import QColor
import re
import subprocess
import sys

class Tools:
    def __init__(self, node):
        self.m_node = node

    def getCliPath(self):
        if sys.platform == "win32":
            return Mistika.sgoPaths.apps() + "/bin/FilemailCli.exe"
        elif sys.platform == "darwin":
            return Mistika.sgoPaths.apps() + "/MacOS/FilemailCli"
        else:
            return Mistika.sgoPaths.apps() + "/bin/FilemailCli"

    def send(self, pattern, listaArgs, osSymbol, f):
        process = subprocess.run([self.getCliPath()] + listaArgs + [osSymbol+"files", f], capture_output=True)
        processOut = process.stderr
                    
        match = pattern.search(processOut)
        if match:
            error_message = match.group(1).decode('utf-8')
            return self.m_node.critical("filemail:error", "Error: {}".format(error_message))
        return True

def init(self):
    self.setClassName("Filemail") 
    self.color=QColor(0xff4167)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("username")
    self.addEncryptedProperty("password")
    self.addProperty("packFiles", False)
    self.addProperty("toMail")
    self.addProperty("subject")
    self.addProperty("message")
    self.addProperty("transferPassword")
    self.addProperty("notify", False)
    self.addProperty("confirmation", False)
    self.addProperty("days", 1)
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    return res

def process(self):
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    out = self.getFirstConnectorByName("out")
    out.clearUniversalPaths()

    if self.bypassEnabled:
        for c in inputs:
            for up in c.getUniversalPaths():
                out.addUniversalPath(up)
        return True
    res = True
    
    osSymbol = "--"
    if sys.platform == "win32":
        osSymbol = "/"

    tools = Tools(self)
    listaArgs = []
    if self.username: listaArgs += [osSymbol+"username", self.username]      
    if self.password: listaArgs += [osSymbol+"userpassword", self.password]  
    if self.toMail: listaArgs += [osSymbol+"to", self.toMail]
    if self.subject: listaArgs += [osSymbol+"subject", self.subject]
    if self.message: listaArgs += [osSymbol+"message", self.message]
    if self.transferPassword: listaArgs += [osSymbol+"transferpassword", self.transferPassword]
    if self.notify: listaArgs += [osSymbol+"notify", "true"] 
    else: listaArgs += [osSymbol+"notify", "false"] 
    if self.confirmation: listaArgs += [osSymbol+"confirmation", "true"]
    else: listaArgs += [osSymbol+"confirmation", "false"]
    listaArgs += [osSymbol+"days", str(self.days)]
    #print(listaArgs)

    pattern = re.compile(rb'"errormessage": "([^"]+)"')
    fileList = ""
    upList = []
    for c in inputs:
        for up in c.getUniversalPaths():
            files = up.getAllFiles()
            for f in files:
                if self.isCancelled():
                    return False      
                #enviar
                if sys.platform == "win32":
                    f = f.replace("/", "\\")
                if not self.packFiles:
                    sent = tools.send(pattern, listaArgs, osSymbol, f)
                    if not sent:
                        self.addFailedUP(up)
                    res = sent and res
                else:
                    fileList += "{},".format(f)
                    upList.append(up)
            out.addUniversalPath(up)

    if self.packFiles:
        fileList = fileList.strip(",")
        res = tools.send(pattern, listaArgs, osSymbol, fileList) and res
        if not res:
            for upp in upList:
                self.addFailedUP(upp)
    return res