import Mistika
from Mistika import workflows
from Mistika.classes import CbaseItem,Cconnector
from Mistika import Qt
from Mistika.Qt import QWizard,QWizardPage,QLabel,QVBoxLayout,QHBoxLayout,QFormLayout,QFileDialog,QLineEdit,QPushButton,QPointF,QMessageBox,QComboBox
import wfWizards
from wfWizards import CbrowserPage,CtextPage,CbasePage,CwfWizard

class IntroPage(CbasePage):
    def __init__(self, parent=None):
        super().__init__("After Effects Integration Wizard - Step 1",
        "",
        "<b>Hello!</b>",
        "This wizard will help you set up the workflow to automatically generate unique videos\n"
                                "by applying AE templates and modifying dynamic elements\n\n"
                                "To get started, you'll need:\n",
        parent)   
        layout=self.layout()
        h=QHBoxLayout()  
        h.addLayout(CbasePage.buildVerticalLayout("csv.png","Containing all dynamic elements"))
        h.addLayout(CbasePage.buildVerticalLayout("ae.png","AEP Template to apply"))
        layout.addLayout(h)
        letsStart=QLabel("\nLet's Start!")
        layout.addWidget(letsStart)
         
class AEPpage(CbrowserPage):
    def __init__(self,varName,defValue=None,title=None,subtitle=None,pageTitle=None,label=None,parent=None):
        super().__init__(varName,defValue,"After Effects Project (*.aep)",title,subtitle,pageTitle,label,parent)
        self.m_tempList=[]
        self.m_compValue=QLineEdit()
        self.m_compValue.setText("")
        self.m_templateValue=QLineEdit()
        self.m_templateValue.setText("0")
        self.m_templateName=QLineEdit()
        layout=self.layout()
        self.m_node=workflows.createStandAloneNode("AfterEffectsFile")
        if defValue:
            self.m_node.url=defValue
        layout.addWidget(QLabel("Composition"))
        self.m_comp=QComboBox(self)
        self.m_comp.setEnabled(False)
        layout.addWidget(self.m_comp)
        self.m_template=QComboBox(self)
        self.m_template.setEnabled(False)
        layout.addWidget(QLabel("Render Template"))
        layout.addWidget(self.m_template)
        
        self.filePath.textChanged.connect(self.onFilePathChanged)
        self.m_comp.currentIndexChanged .connect(self.onCompChanged)
        self.m_template.currentIndexChanged .connect(self.onTemplateChanged)
        self.registerField("comp",self.m_compValue)
        self.registerField("template",self.m_templateValue)
        self.registerField("templateName",self.m_templateName)
        
        self.m_compValue.textChanged.connect(self.checkConditions)
        self.m_templateValue.textChanged.connect(self.checkConditions)
        
    def onFilePathChanged(self,fp):
        self.m_node.url=fp
        self.m_comp.setEnabled(True)
        self.m_template.setEnabled(True)
        compsList=[item for item in self.m_node._compositionList if item]        
        self.m_comp.clear()
        self.m_comp.addItems(compsList)
        self.onCompChanged(0)

    def onCompChanged(self,idx):
        comp=self.m_comp.itemText(idx)
        self.m_compValue.setText(comp)
        self.m_node.composition=comp
        self.m_tempList=[]
        labels=[]
        for item in self.m_node._renderTemplateList:
            s=item.split("$$$")
            if s[0]:
                self.m_tempList.append(s)
                labels.append(s[0])
                
        self.m_template.clear()
        self.m_template.addItems(labels)        
                
    def onTemplateChanged(self,idx):
        template=self.m_template.itemText(idx)
        for k,v in self.m_tempList:
            if k==template:
                self.m_templateValue.setText(v)
                self.m_templateName.setText(k)
                return
        self.m_templateValue.setText("") #not found

    def isComplete(self):
        try:
            cv=int(self.m_templateValue.text)
        except ValueError:
            return False
        return cv>0 and self.m_compValue.text

    def checkConditions(self):
        self.completeChanged.emit()        
 
class ConclusionPage(CbasePage):
    def __init__(self, parent=None):
        super().__init__("After Effects Integration Wizard - Step 6",
                        "",
                        "Almost there! Review your workflow configuration",
                        "Review your settings and click <b>\"Finish\"</b> to create your workflow with the specified parameters:\n\n",
                        parent)
        self.m_form=None          
#addition        

    def initializePage(self):
            wfName=self.field("wfName")
            csvFilePath=self.field("csvFilePath")
            aepFilePath=self.field("aepFilePath")
            comp=self.field("comp")
            template=self.field("templateName")
            outputPath=self.field("outputPath")
            layout=self.layout()        
            if self.m_form:
                layout.removeItem(self.m_form)
                self.m_form.deleteLater()
            self.m_form=QFormLayout()
            self.m_form.addRow(QLabel("Workflow Name:"),QLabel(wfName))
            self.m_form.addRow(QLabel("CSV Folder:"),QLabel(csvFilePath))
            self.m_form.addRow(QLabel("AEP File:"),QLabel(aepFilePath))
            self.m_form.addRow(QLabel("Composition:"),QLabel(comp))
            self.m_form.addRow(QLabel("Render Template:"),QLabel(template))
            self.m_form.addRow(QLabel("Final Destination Folder:"),QLabel(outputPath))
            layout.addLayout(self.m_form)
        
class AEWizard(CwfWizard):
    def __init__(self, parent=None):
        super().__init__("Creating an After Effects workflow",[['--aepFile',str,''],['--csvFolder',str,'']],parent)
        self.addPage(IntroPage())
        self.addPage(CtextPage("wfName","AE Generator",
                                "After Effects Integration Wizard - Step 2",
                                "",
                                 "Name your workflow",
                                 "Choose a name for your workflow to easily identify it"))
        csvDefault=self.getArg("csvPath")
        self.addPage(CbrowserPage("csvFilePath*",csvDefault if csvDefault else "","CSV Folder",
                                 "After Effects Integration Wizard - Step 3",
                                 "",
                                 "Select CSV folder",
                                 "Specify the folder where your CSV files are or will be located\nEach line in these files will generate a unique video\n\nCSV Folder"))
        aepFile=self.getArg("aepFile")                                 
        self.m_aepPage=AEPpage("aepFilePath*",aepFile if aepFile else "",
                            "After Effects Integration Wizard - Step 4",
                            "",
                            "Select your Adobe After Effects AEP file",
                            "Choose the AEP template file that will be customized using the data from your CSV\n\nAfter Effects Project")
        self.addPage(self.m_aepPage)                  
        self.addPage(CbrowserPage("outputPath*","","Final Destination Folder",
                                 "After Effects Integration Wizard - Step 5",
                                 "",
                                 "Select your final destination folder",
                                 "Designate the folder where the completed unique videos will be saved\n\nFinal Destination Folder"))
        self.addPage(ConclusionPage())
        self.accepted.connect(self.processWizard)
        
    def helpFunction(self):
        url = QUrl("https://www.sgo.es")  
        QDesktopServices.openUrl(url)    
        
    def processWizard(self):        
        wfName=self.field("wfName")
        csvFilePath=self.field("csvFilePath")
        aepFilePath=self.field("aepFilePath")
        comp=self.field("comp")
        template=self.field("template")
        outputPath=self.field("outputPath")
        #creating wf
        wf=workflows.addWorkflow(wfName)
        watcher=wfWizards.addAndConnectNode(wf,"Watcher",CbaseItem.NODETYPE_INPUT,QPointF(-300,0))
        csv=wfWizards.addAndConnectNode(wf,"CSV To UPmdata",CbaseItem.NODETYPE_TASK,QPointF(0,0),watcher,"To","csv")
        aep=wfWizards.addAndConnectNode(wf,self.m_aepPage.m_node,CbaseItem.NODETYPE_TASK,QPointF(300,0),csv,"mdata","override")
        render=wfWizards.addAndConnectNode(wf,"After Effects Render",CbaseItem.NODETYPE_TASK,QPointF(600,0),aep,"rnd","in")
        #decoration
        wf.createBackDropBox(QPointF(-350,150),QPointF(-50,-150),QColor("#004020"),"Select the Folder to get CSVs from",8,False,False,QColor("#FFFFFF"))       
        wf.createBackDropBox(QPointF(280,150),QPointF(550,-150),QColor("#004020"),"Select your comp and output",8,False,False,QColor("#FFFFFF"))      
        wf.createBackDropBox(QPointF(580,150),QPointF(900,-150),QColor("#004020"),"Select Language and output File Path",8,False,False,QColor("#FFFFFF"))
        #properties
        watcher.url=csvFilePath.replace("\\","/")+"/"
        watcher.include="*.csv"
        aep.url=aepFilePath.replace("\\","/")
        aep.composition=comp
        aep.renderTemplate=int(template)
        aep.newRNDdirectory=Mistika.sgoPaths.tmp()+"/"
        render.url=outputPath.replace("\\","/")+"/"
        workflows.setCurrentWorkflow(wf)
#final notification
        msg = QMessageBox()
        msg.setWindowTitle("Workflow Creation Completed")
        msg.setText("Follow these two simple steps to initiate on your workflow<br><br>"
        "<b>Activate the Workflow</b><br>"
        "Add the workflow to the queue by clicking the <b>\"Add to Queue\"</b> button<br><br>"
        "<b>Start Processing</b><br>"
        "Begin copying CSV files into the Watcher Folder<br><br>"        
        "The workflow will automatically process each CSV file, creating a custom video for every line of data<br><br>"
        "<b>Need Help?</b><br>"
        "<a href=\"https://www.sgo.es/wizards/create-after-effects-workflow/\">Access Documentation</a>      <a href=\"https://support.sgo.es\">Contact Support</a>"
        )
        msg.setTextFormat(1) #Qt.RichText)
        msg.exec()
        Mistika.tasks.addWorkflow(wf)
wizard = AEWizard()
wizard.raise_()
wizard.activateWindow()
wizard.show()
