import re
import Mistika
import argparse
from Mistika.classes import CbaseItem,Cconnector
from Mistika.Qt import QWizard,QWizardPage,QLabel,QVBoxLayout,QHBoxLayout,QFormLayout,QFileDialog,QLineEdit,QPushButton,QMessageBox,QPixmap,QSize

def addAndConnectNode(wf,name,nodeType,pos,fromNode=None,cout=None,cin=None):
    if isinstance(name,str):
        node=wf.addNode(name,nodeType)
    else:
        node=name
        wf.addExistingNode(node)
    node.pos=pos
    if fromNode and cin and cout:
        fromConnector=fromNode.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_OUTPUT,cout)
        toConnector=node.getFirstConnectorByType(Cconnector.CONNECTOR_TYPE_INPUT,cin)
        if fromConnector and toConnector:
            toConnector.link(fromConnector)
    return node 

class CbasePage(QWizardPage):
    def __init__(self,title=None,subtitle=None,pageTitle=None,label=None,parent=None):
        super().__init__(parent)
        self.setTitle(title if title else "")
        self.setSubTitle(subtitle if subtitle else "")
        m_layout=QVBoxLayout()
        if pageTitle:
            self.m_pageTitle=QLabel(pageTitle)
            self.m_pageTitle.objectName="pageTitle"
        if pageTitle:
            m_layout.addWidget(self.m_pageTitle)
        if label:
            m_layout.addWidget(QLabel(label))
        self.setLayout(m_layout)        

    # this function should create the nodes inside wf, starting at pos and connecting it to connector
    #it should return the connector to connect to the next workflow (None if there is no output connector)
    def createWorkflow(self,wf,pos,connector=None):
        return None
      
    @staticmethod      
    def buildVerticalLayout(image,text,imgPath=None):
        v=QVBoxLayout()
        h=QHBoxLayout()
        v.setAlignment(4) #Qt::AlignHCenter)
        pix=QLabel()
        if not imgPath:
            imgPath=Mistika.sgoPaths.pixmap()
        imgPath=imgPath.rstrip('/') + '/'
        sz=QSize(80,80)
        image=QPixmap(imgPath+image)
        pix.setPixmap(image)
        pix.scaledContents=True
        pix.setFixedSize(sz)            
        pix.setAlignment(4) #Qt::AlignHCenter)
        h.addStretch()
        h.addWidget(pix)
        h.addStretch()
        v.addLayout(h)
        text=QLabel(text)  
        text.setAlignment(4)      
        v.addWidget(text)
        return v  

class CtextPage(CbasePage):
    def __init__(self,varName,defValue=None,title=None,subtitle=None,pageTitle=None,label=None,parent=None):
        super().__init__(title,subtitle,pageTitle,label,parent)
#creation
        self.wfName=QLineEdit()
        self.wfName.setText(defValue)
#addition       
        layout=self.layout()
        layout.addWidget(self.wfName)
#registration        
        self.registerField(varName, self.wfName)
        
class CbrowserPage(CbasePage):
    def __init__(self,varName,defValue,dialogString,title=None,subtitle=None,pageTitle=None,label=None,parent=None):
        super().__init__(title,subtitle,pageTitle,label,parent)
#creation
        self.m_dialogString=dialogString
        self.filePath=QLineEdit()
        self.browseButton=QPushButton("...")
#addition
        layout=self.layout()
        h=QHBoxLayout()
        h.addWidget(self.filePath)
        h.addWidget(self.browseButton)
        layout.addLayout(h)
        self.browseButton.clicked.connect(self.browser)
#registration        
        self.registerField(varName, self.filePath)        
        
    def browser(self):
        title=re.sub(r'\(.*?\)', '',self.m_dialogString).strip()
        matches=re.findall(r'\((.*?)\)',self.m_dialogString)
        ext=matches[-1].strip() if matches else None
        if ext:
            filePath=QFileDialog.getOpenFileName(self,"Select {}".format(title), "",self.m_dialogString)
        else:
            filePath=QFileDialog.getExistingDirectory(self,"Select {}".format(title))
        
        if filePath:
            self.filePath.setText(filePath)
            
            

class CwfWizard(QWizard):
    def __init__(self,title,argsList=None,parent=None):
        super().__init__(parent)
        if argsList:
            self.loadArgs(argsList)
        self.setWindowTitle(title)
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setWindowFlags((self.windowFlags() & ~0x00010000) | 0x00040000) #Qt.WindowContextHelpButtonHint | WindowStaysOnTopHint

        
    def loadArgs(self,paramsList):         
        params=Mistika.Qt.QCoreApplication.arguments()
        self.m_paramsParser=argparse.ArgumentParser()
        for [prm,prmType,defValue] in paramsList:
            self.m_paramsParser.add_argument(prm,type=prmType,default=defValue) # i.e.: '--processJson',type=str,default=''
        self.m_namespace,self.m_args=self.m_paramsParser.parse_known_args(params)
        
    def getArg(self,name):
        if name in self.m_namespace:
            return getattr(self.m_namespace,name)
        else:
            return None
