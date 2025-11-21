from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from googleAuth import GoogleAuth
import Mistika
import os
import base64
import json
from requests import HTTPError
from baseItemTools import totalNumberOfUPs

mailModulesLoaded=False
try:
    import re
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    mailModulesLoaded=True
except ImportError as e:
    print("Unable to import modules: "+e.message)
    print("check your sys.path ")
            
_WF_MAIL_DEFAULT_MSG="""Put Your Text Here
<?py
if self.onePerFile:
    print("Input file:")
    up=self._localDict['up']
    print (up.getFilePath())
else:
    print("List of input Files:")
    for c in self.getConnectors():
        for p in c.getUniversalPaths():
            print (p.getFilePath())
?>"""

def init(self):
    self.color=QColor(225,225,210)
    self.addConnector("input",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addProperty("clientId")
    self.addProperty("onlySendIfInput")
    self.addProperty("onePerFile",False)
    self.addEncryptedProperty("clientSecret")
    self.addProperty("to") #comma separated list
    self.addProperty("replyTo")
    self.addProperty("subject","Mistika Workflows Mail Node Processed")
    self.addProperty("bodyType","plain")
    self.addProperty("body",_WF_MAIL_DEFAULT_MSG)
    self.addProperty("credentialsString", "")  
    self.addProperty("_credentialsDict", {})
    self.bypassSupported=True
    self.setAcceptConnectors(True,"input")
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.addActionToContextMenu("Authenticate")
    return True
    
def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    if not mailModulesLoaded:
        res=self.critical("mail:modules","Modules not loaded. Check your sys.path or install them")
    if self.clientId == "":
       res = self.critical("Gmail:clientId", "'clientI' can not be empty") and res
    if self.clientSecret == "":
       res = self.critical("Gmail:clientSecret", "'clientSecret' can not be empty") and res
#    if self.login=="":
#        res=self.critical("mail:loginEmpty","'Login' can not be empty") and res
    to=str(self.to).strip()
    if to=="":
        res=self.critical("mail:toEmpty","'To' can not be empty") and res
    else:
        list=to.split(',')
        for item in list:
            item=item.strip()
            if re.match('^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,20})$',item) == None:
                res=self.critical("mail:invalidTo","Invalid email address: "+item+". Use ',' to separate multiple mail addresses.") and res

    return res
    
def process(self):
    res = True
    def sendMail(drive, up=None):
        msg = MIMEMultipart()
        subject=self.evaluate(str(self.subject))
        body=self.evaluate(str(self.body))
        if up!=None:
            subject=up.evaluateTokensString(subject)
            body=up.evaluateTokensString(body)
        msg['subject']=subject
        msg['to']=str(self.to)
        r=self.replyTo.strip()
        if len(r) > 0:
            msg['reply-to']=r
        body=self.evaluate(self.body)
        msg.attach(MIMEText(body,self.bodyType))
        create_message = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}
        try:
            msg = (drive.users().messages().send(userId="me", body=create_message).execute())
            print(F'sent message to {msg} Message Id: {msg["id"]}')
            return True
        except Exception as error:
            return self.critical("process:smtp","An error ocurred: {}".format(error))

    if self.bypassEnabled:
        return True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    hasInput = False
    for c in inputs:                                 
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            hasInput = True
    if not hasInput and self.onlySendIfInput: 
        return True  

    self._credentialsDict = {} if not self.credentialsString else json.loads(self.credentialsString)
    goo = GoogleAuth(self, "https://www.googleapis.com/auth/gmail.send", "gmail", "v1", self._credentialsDict)
    drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
    self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId.strip())

    if drive == "TimeOut": 
        return self.critical("GoogleMail:process:authCanceled", "Authentication timeout")
    elif drive == None:
        return False
    if self.credentialsString == None or self.credentialsString == "{}": 
        return self.critical("GoogleMail:process:authCanceled", "Authentication was rejected") 
    
    self.setComplexity(totalNumberOfUPs(self)*100)
    current=0
    self.progressUpdated(current)
    if self.onePerFile:
        for c in self.getConnectors():
            for up in c.getUniversalPaths():
                d={}
                d["up"]=up
                self._localDict=d
                self.setPropertiesFromUP(up)     
                done=sendMail(drive,up)
                if not done:
                    self.addFailedUP(up)
                res=done and res
                current+=1
                self.progressUpdated(current*100)
    else:
        res=sendMail(drive)
    
    self.progressUpdated(self.complexity())
    return res

def menuAction(self,name):
    print ("menuAction",name)
    if name=="Authenticate":
        self.credentialsString = ""
        self._credentialsDict = {}
        goo = GoogleAuth(self, "https://www.googleapis.com/auth/gmail.send", "gmail", "v1", self._credentialsDict)
        drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
        self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId.strip())

        if drive == "TimeOut": 
            return self.critical("GoogleMail:process:authCanceled", "Authentication timeout")
        if self.credentialsString == None or self.credentialsString == "{}": 
            return self.critical("GoogleMail:process:authCanceled", "Authentication was rejected") 
        