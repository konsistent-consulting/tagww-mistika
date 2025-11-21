import Mistika
from Mistika import workflows
from Mistika.classes import CbaseItem,Cconnector
from Mistika import Qt
from Mistika.Qt import QWizard,QWizardPage,QLabel,QVBoxLayout,QHBoxLayout,QFormLayout,QFileDialog,QLineEdit,QPushButton,QPointF,QMessageBox,QComboBox
import wfWizards
from wfWizards import CbrowserPage,CtextPage,CbasePage

class IntroPage(CbasePage):
    def __init__(self, parent=None):
        super().__init__("Mistika Boutique Integration Wizard - Step 1",
                         "",
                         "<b>Hello!</b>",
                         "This wizard will help you set up the workflow to automatically generate unique videos\n"
                                "by applying Mistika Boutique templates and modifying dynamic elements\n\n"
                                "To get started, you'll need:\n",
                                parent)   
        layout=self.layout()
        h=QHBoxLayout()  
        h.addLayout(CbasePage.buildVerticalLayout("csv.png","Containing all dynamic elements"))
        h.addLayout(CbasePage.buildVerticalLayout("bt.png","RND Template to apply"))
        layout.addLayout(h)
        letsStart=QLabel("\nLet's Start!")
        layout.addWidget(letsStart)
         
class ConclusionPage(CbasePage):
    def __init__(self, parent=None):
        super().__init__("Mistika Boutique Integration Wizard - Step 6",
                        "",
                        "Almost there! Review your workflow configuration",
                        "Review your settings and click <b>\"Finish\"</b> to create your workflow with the specified parameters:\n\n",
                        parent)
        self.m_form=None
        
#addition        

    def initializePage(self):
            wfName=self.field("wfName")
            csvFilePath=self.field("csvFilePath")
            rndFilePath=self.field("rndFilePath")
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
            self.m_form.addRow(QLabel("RND File:"),QLabel(rndFilePath))
            self.m_form.addRow(QLabel("Final Destination Folder:"),QLabel(outputPath))
            layout.addLayout(self.m_form)
        
class RNDwizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWizardStyle(QWizard.ClassicStyle)
        self.setWindowTitle("Creating a Mistika Boutique workflow")
        self.setWindowFlags(self.windowFlags() & ~0x00010000) #Qt.WindowContextHelpButtonHint
        self.addPage(IntroPage())
        self.addPage(CtextPage("wfName","AE Generator",
                                "Mistika Boutique Integration Wizard - Step 2",
                                "",
                                 "Name your workflow",
                                 "Choose a name for your workflow to easily identify it"))        
        self.addPage(CbrowserPage("csvFilePath*","","CSV Folder",
                                 "Mistika Boutique Integration Wizard - Step 3",
                                 "",
                                 "Select CSV folder",
                                 "Specify the folder where your CSV files are or will be located\nEach line in these files will generate a unique video\n\nCSV Folder"))

        self.m_rndPage=CbrowserPage("rndFilePath*","","Mistika RND File (*.rnd)",
                            "Mistika Boutique Integration Wizard - Step 4",
                            "",
                            "Select your Mistika Boutique  RND file",
                            "Choose the RND template file that will be customized using the data from your CSV\n\nMistika RND File") 
        self.addPage(self.m_rndPage)                  
        self.addPage(CbrowserPage("outputPath*","","Final Destination Folder",
                                 "Mistika Boutique Integration Wizard - Step 5",
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
        rndFilePath=self.field("rndFilePath")
        outputPath=self.field("outputPath")
        print("wfName:",wfName)
        print("csvFilePath:",csvFilePath)
        print("outputPath:",outputPath)
        #creating wf
        wf=workflows.addWorkflow(wfName)
        watcher=wfWizards.addAndConnectNode(wf,"Watcher",CbaseItem.NODETYPE_INPUT,QPointF(-300,0))
        csv=wfWizards.addAndConnectNode(wf,"CSV To UPmdata",CbaseItem.NODETYPE_TASK,QPointF(0,0),watcher,"To","csv")
        rnd=wfWizards.addAndConnectNode(wf,"RND File",CbaseItem.NODETYPE_TASK,QPointF(300,0),csv,"mdata","override")
        render=wfWizards.addAndConnectNode(wf,"Mistika Render",CbaseItem.NODETYPE_TASK,QPointF(600,0),rnd,"rnd","rnd")
        #decoration
        wf.createBackDropBox(QPointF(-350,150),QPointF(-50,-150),QColor("#004020"),"Select the Folder to get CSVs from",8,False,False,QColor("#FFFFFF"))       
        wf.createBackDropBox(QPointF(280,150),QPointF(550,-150),QColor("#004020"),"Select your RND File",8,False,False,QColor("#FFFFFF"))      
        wf.createBackDropBox(QPointF(580,150),QPointF(900,-150),QColor("#004020"),"Select your output File Path",8,False,False,QColor("#FFFFFF"))
        #properties
        watcher.url=csvFilePath.replace("\\","/")+"/"
        watcher.include="*.csv"
        rnd.url=rndFilePath.replace("\\","/")
        rnd.mediaConnectors=False
        rnd.newRNDdirectory=Mistika.sgoPaths.tmp()+"/"
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
        "<a href=\"https://www.sgo.es\">TUTORIAL</a> <a href=\"https://www.sgo.es\">DOCUMENTATION</a> <a href=\"https://www.sgo.es\">CONTACT SUPPORT</a>"
        )
        msg.setTextFormat(1) #Qt.RichText)
        msg.exec()
        Mistika.tasks.addWorkflow(wf)
wizard = RNDwizard()
wizard.show()
