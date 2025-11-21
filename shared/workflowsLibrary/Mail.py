from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from baseItemTools import totalNumberOfUPs

mailModulesLoaded=False
try:
    import sys
    import smtplib
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
    self.addProperty("login")
    self.addProperty("onlySendIfInput")
    self.addProperty("onePerFile",False)
    self.addEncryptedProperty("pwd")
    self.addProperty("smtpServer","")
    self.addProperty("port",587)
    self.addProperty("mailFrom")
    self.addProperty("to") #comma separated list
    self.addProperty("replyTo")
    self.addProperty("subject","Mistika Workflows Mail Node Processed")
    self.addProperty("bodyType","plain")
    self.addProperty("body",_WF_MAIL_DEFAULT_MSG)    
    self.bypassSupported=True
    self.setAcceptConnectors(True,"input")
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    return True
    
def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    if not mailModulesLoaded:
        res=self.critical("mail:modules","Modules not loaded. Check your sys.path or install them")
#    if self.login=="":
#        res=self.critical("mail:loginEmpty","'Login' can not be empty") and res
    to=str(self.to).strip()
    if to=="":
        res=self.critical("mail:toEmpty","'To' can not be empty") and res
#    else:
#        list=to.split(',')
#        for item in list:
#            item=item.strip()
#            if re.match('^([a-zA-Z0-9_\-\.]+)@([a-zA-Z0-9_\-\.]+)\.([a-zA-Z]{2,20})$',item) == None:
#                res=self.critical("mail:invalidTo","Invalid email address: "+item+". Use ',' to separate multiple mail addresses.") and res

    return res
    
def process(self):
    res=True
    def sendMail(up=None):
        try:
            s = smtplib.SMTP(self.smtpServer,int(self.port))
        except Exception as e:
            return self.critical("process:smtp","smtp Error: {}".format(e))
        try:
            s.starttls()
        except smtplib.SMTPException as e:
             self.warning("process:tls","TLS not supported by server")
        try:
            s.ehlo()
            if self.login!="":
                s.login(self.login,self.pwd)
            msg = MIMEMultipart()
            subject=self.evaluate(str(self.subject))
            evaluatedTo=self.evaluate(str(self.to))
            body=self.evaluate(str(self.body))
            if up!=None:
                subject=up.evaluateTokensString(subject)
                evaluatedTo=up.evaluateTokensString(evaluatedTo)
                body=up.evaluateTokensString(body)
            msg['Subject']=subject
            f=self.mailFrom.strip()
            msg['From']=f if len(f)>0 else self.login
            msg['To']=evaluatedTo
            r=self.replyTo.strip()
            if len(r) > 0:
                msg['Reply-To']=r
            msg.attach(MIMEText(body,self.bodyType))
            s.sendmail(self.login,evaluatedTo.split(","),msg.as_string())
            s.quit()
            return True
        except Exception as e:
            return self.critical("process:smtp","smtp Error: {}".format(e))
            
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
                done=sendMail(up)
                if not done:
                    self.addFailedUP(up)
                res=done and res
                current+=1
                self.progressUpdated(current*100)
    else:
        res=sendMail()
    
    self.progressUpdated(self.complexity())
    return res