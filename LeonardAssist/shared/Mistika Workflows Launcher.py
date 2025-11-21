## Mistika Workflows Launcher v1.0_20250310

import os
import sys
import platform
import xml.etree.ElementTree as ET
import json
from datetime import datetime
import subprocess

try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import Qt, QStandardPaths, QOperatingSystemVersion
    from PySide6.QtGui import QColor, QIcon
except:
    print("PySide6 module not found\nYou may be able of install it just by typing 'pip install pyside6' in your cmd/terminal shell\nThen try again running this script")
    sys.exit()


################################################################################################



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.filePath = ""
        self.myMWF=""
        self.mwfsWorkPath=""
        self.jsonWorkPath=""
        self.currentState = []
        currentDateTime = datetime.now()
        self.DateID = currentDateTime.strftime("%Y%m%d-%H%M%S")
        self.MWFPath=""

        MainWindow.getOSPaths(self)
        MainWindow.getLastPaths(self)
        MainWindow.setInitialGeometry(self)
        MainWindow.setInitialState(self)
        MainWindow.clearUI(self)


    def getLastPaths(self):
        if os.path.isfile(self.LocalCfg):
            try:
                with open(self.LocalCfg, "r") as js:
                    lastPaths = json.load(js)
            except:
                print(f'Could not read last file paths in config file {self.LocalCfg}')
            for k,v in lastPaths.items():
                if lastPaths[k] == "":
                    lastPaths[k]=QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
            self.homeDir = lastPaths['OpenFileDialog']
            self.WatcherPath = lastPaths['WatchFolder']
        else:
            self.homeDir = self.WatcherPath = QStandardPaths.writableLocation(QStandardPaths.HomeLocation)
        return

    def checkOSPaths(self,EXEPath):
        if not os.path.isfile(EXEPath):
            MainWindow.showInfo(self, "Warning", "No Mistika Workflows binary found\nOnly WatchFolder mode may work")
            return False
        return True

    def getOSPaths(self):
        typeOS=platform.system()
        if typeOS=='Windows':
            sysRoot = (os.path.dirname(os.environ.get("SYSTEMROOT"))).replace('\\','/')
            SGOinstallInfo=f'{sysRoot}ProgramData/SGO/installation.xml'
            try:
                installInfo=ET.parse(SGOinstallInfo)
                SGOApps = ((installInfo.find("./paths/app")).text).replace('/', '\\')
                SGOAppData= ((installInfo.find("./paths/env")).text).replace('/', '\\')
            except:
                MainWindow.showInfo(self, "Info", "No SGO installation.xml file found\nTrying with default paths...")
                SGOApps = "C:\\Program Files\\SGO Apps"
                SGOAppData = f'{self.homeDir}\\SGO AppData'
            self.MWFPath = f'{SGOApps}\\Mistika Workflows'
            self.LocalCfg = f'{SGOAppData}\\LeonardAssist\\shared\\LeonardAssist.cfg'
            self.tmpDir= f'{SGOAppData}\\LeonardAssist\\shared\\LeonardAssistFiles\\'
            self.styleFile = f'{SGOAppData}\\LeonardAssist\\shared\\Mistika Workflows Launcher.qss'
            self.EXEPath=f'{self.MWFPath}\\bin\\workflows.exe'

        if typeOS=='Linux':
            homeFolder= os.path.expanduser("~")
            self.MWFPath=f'{homeFolder}/SGO Apps/Mistika Workflows'
            self.LocalCfg = f'{homeFolder}/SGO AppData/LeonardAssist/shared/LeonardAssist.cfg'
            self.tmpDir = f'{homeFolder}/SGO AppData/LeonardAssist/shared/LeonardAssistFiles/'
            self.styleFile = f'{homeFolder}/SGO AppData/LeonardAssist/shared/Mistika Workflows Launcher.qss'
            self.EXEPath=f'{self.MWFPath}/bin/workflows'

        if typeOS=='Darwin':
            homeFolder = os.path.expanduser("~")
            self.MWFPath=f'/Applications/SGO Apps/Mistika Workflows.app/Contents'
            self.LocalCfg = f'{homeFolder}/SGO AppData/LeonardAssist/shared/LeonardAssist.cfg'
            self.tmpDir = f'{homeFolder}/SGO AppData/LeonardAssist/shared/LeonardAssistFiles/'
            self.styleFile = f'{homeFolder}/SGO AppData/LeonardAssist/shared/Mistika Workflows Launcher.qss'
            self.EXEPath = f'{self.MWFPath}/MacOS/workflows'
        self.BinaryExists=MainWindow.checkOSPaths(self, self.EXEPath)
        if not self.BinaryExists:
            self.currentState=[False,False,True,True,"",""]
        return

    def setInitialGeometry(self):
        self.setWindowTitle('SGO Mistika Workflows Launcher v1.0')
        self.setWindowIcon(QIcon(f'{self.MWFPath}/icons/workflows.png'))
        self.setGeometry(100,100,1050,350) # (x_pos, y_pos, width, height)
        return

    def setInitialState(self):
        self.currentState=[False,False,True,self.WatcherPath,""]  #checkbox1,checkbox2,checkbox3,self.WatcherPath,self.OpenFilePath
        return

    def getCurrentState(self):
        check1 = bool(self.checkbox1.isChecked())
        check2 = bool(self.checkbox2.isChecked())
        check3 = bool(self.checkbox3.isChecked())
        currentWatcherPath=self.WatcherPath
        openFilePath=self.homeDir
        return [check1,check2,check3,currentWatcherPath,openFilePath]

    def clearUI(self):
        centralWidget=QWidget()
        self.setCentralWidget(centralWidget)
        self.layout = QVBoxLayout(centralWidget)

        TopbarLayout = QHBoxLayout()
        self.openFileButton = QPushButton('Open Workflow')
        self.openFileButton.clicked.connect(self.openFileDialog)
        TopbarLayout.addWidget(self.openFileButton)
        self.refreshButton = QPushButton('Reload Workflow')
        self.refreshButton.clicked.connect(self.refreshAction)
        TopbarLayout.addWidget(self.refreshButton)
        self.layout.addLayout(TopbarLayout)

        BottombarLayout1 = QHBoxLayout()
        global checkbox1
        self.checkbox1 = QCheckBox("Launch Mistika Workflows")
        self.checkbox1.setChecked(self.currentState[0])
        BottombarLayout1.addWidget(self.checkbox1)
        self.layout.addLayout(BottombarLayout1)

        BottombarLayout2 = QHBoxLayout()
        global checkbox2
        self.checkbox2 = QCheckBox("Silent Mode --- no GUI")
        self.checkbox2.setChecked(self.currentState[1])
        BottombarLayout2.addWidget(self.checkbox2)
        self.layout.addLayout(BottombarLayout2)

        BottombarLayout3 = QHBoxLayout()
        global checkbox3
        self.checkbox3 = QCheckBox("Use Watch Folder")
        self.checkbox3.setChecked(self.currentState[2])
        self.saveFilePathField=QLineEdit()
        self.saveFilePathField.setText(self.currentState[3])
        self.saveFilePathField.setReadOnly(True)
        self.saveButton=QPushButton("Select Folder...")
        self.saveButton.clicked.connect(self.saveFilePathClicked)
        BottombarLayout3.addWidget(self.checkbox3)
        BottombarLayout3.addWidget(self.saveButton)
        BottombarLayout3.addWidget(self.saveFilePathField)
        self.layout.addLayout(BottombarLayout3)

        ButtonLayout=QHBoxLayout()
        ButtonLayout.addStretch()
        self.cancelButton=QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.cancelButtonClicked)
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.okButtonClicked)
        ButtonLayout.addWidget(self.cancelButton)
        ButtonLayout.addWidget(self.okButton)
        self.layout.addLayout(ButtonLayout)

        self.tabWidget = QTabWidget()
        self.layout.addWidget(self.tabWidget)
        self.setLayout(self.layout)
        self.applyStyle()
        return

    def buildUI(self,mwfs):
        for mwf in mwfs.keys():
            tab = QWidget()
            tabLayout = QVBoxLayout(tab)
            tableWidget = QTableWidget()
            tableWidget.setColumnCount(4)
            tableWidget.setHorizontalHeaderLabels(["Node", "type", "Enabled", "path"])
            tableWidget.verticalHeader().setVisible(False)
            tabLayout.addWidget(tableWidget)
            self.tabWidget.addTab(tab,mwf)
            tableWidget.setColumnWidth(0, 150)
            tableWidget.setColumnWidth(1, 75)
            tableWidget.setColumnWidth(2, 75)
            tableWidget.setColumnWidth(3, 1000)
            nNodes=len(mwfs.get(mwf))
            tableWidget.setRowCount(nNodes)
            for row, node in enumerate(mwfs.get(mwf)):
                nodeName=QTableWidgetItem(node['nodeName'])
                nodeName.setTextAlignment(Qt.AlignHCenter)
                nodeType=QTableWidgetItem(node['nodeType'])
                nodeType.setTextAlignment(Qt.AlignHCenter)
                enabledBool = True if node['bypassEnabled'] == 'false' else False
                bypass=QTableWidgetItem(str(enabledBool))
                bypass.setTextAlignment(Qt.AlignHCenter)
                bypass.setForeground(QColor("green")) if enabledBool else bypass.setForeground(QColor("red"))
                path=QTableWidgetItem(node['path'])
                tableWidget.setItem(row, 0, nodeName)
                tableWidget.setItem(row, 1, nodeType)
                tableWidget.setItem(row, 2, bypass)
                tableWidget.setItem(row, 3, path)
                tableWidget.setRowHeight(row,10)
        self.applyStyle()
        return

    def applyStyle(self):
        try:
            with open(self.styleFile,"r") as f:
                style=f.read()
                self.setStyleSheet(style)
        except:
            MainWindow.showInfo(self, "Info", "No style file found\nPlease check your Mistika Workflows installation paths")
        return

    def processMWF(self,mwfFile):
        n=len(mwfFile.split('/'))
        self.myMWF=mwfFile.split('/')[n-1][:-4]
        tree = ET.parse(mwfFile)
        mwfTree = tree.getroot()
        tags = ['path', 'url']
        mwfs = {}
        workflows = tree.findall("./workflow")
        for workflow in workflows:
            workflowName = workflow.get("name")
            nodes = workflow.findall("./nodes/node")
            mwfNodes = []
            for node in nodes:
                nodeAttributes = {}
                nodeAttributes['nodeType'] = node.get("type")
                properties = node.find("properties")
                for prop in properties:
                    if prop.tag == 'objectName':
                        nodeAttributes['nodeName'] = prop.text
                    if prop.tag == 'bypassEnabled':
                        nodeAttributes['bypassEnabled'] = prop.text
                    for tag in tags:
                        if prop.tag.lower().__contains__(tag):
                            if prop.text =='false':
                                prop.text='n/a'
                            nodeAttributes['path']= prop.text
                try:
                    nodeAttributes['path']
                except:
                    nodeAttributes['path']='n/a'
                mwfNodes.append(nodeAttributes)
                mwfs[workflowName]=mwfNodes
        # print(json.dumps(mwfs, sort_keys=True, indent=3))
        return mwfs

    def processJson(self):
        resolve = app.GetResolve()
        projectManager = resolve.GetProjectManager()
        currentProject = projectManager.GetCurrentProject()
        currentTimeline = currentProject.GetCurrentTimeline()
        self.myTimeline= currentTimeline.GetName()
        pid = str(os.getpid())
        tmpPath=self.tmpDir
        if not os.path.isdir(tmpPath):
            os.mkdir((tmpPath))
        csvFilePath = (tmpPath + self.myMWF + '-' + self.myTimeline + '-' + pid + '.csv').replace('\\', '/')
        aleFilePath = (tmpPath + self.myMWF + '-' + self.myTimeline + '-' + pid + '.ale').replace('\\', '/')
        jsonFilePath = (tmpPath + self.myMWF + '-' + self.myTimeline + '-' + pid + '.json').replace('\\', '/')
        self.mwfFilePath = (tmpPath + self.myMWF + '-' + self.myTimeline + '-' + pid + '.mwf').replace('\\', '/')
        self.jsonWorkPath=jsonFilePath
        currentTimeline.Export(csvFilePath, resolve.EXPORT_TEXT_CSV)
        currentTimeline.Export(aleFilePath, resolve.EXPORT_ALE_CDL)
        prjData = {}
        prjData['project'] = currentProject.GetName()
        prjData['timeline'] = currentTimeline.GetName()
        prjData['fps'] = currentTimeline.GetSetting('timelineFrameRate')
        prjData['RecIn'] = currentTimeline.GetStartFrame()
        prjData['RecOut'] = currentTimeline.GetEndFrame()
        prjData['csvFilePath'] = csvFilePath if os.path.isfile(csvFilePath) else None
        prjData['aleFilePath'] = aleFilePath if os.path.isfile(aleFilePath) else None
        prjData['markers'] = currentTimeline.GetMarkers()

        for i in range(1, currentTimeline.GetTrackCount("video") + 1):
            EventsList = []
            timelineItems = currentTimeline.GetItemListInTrack("video", i)
            if len(timelineItems) == 0:
                EventsList = None
                continue
            for n, item in enumerate(timelineItems):
                if item.GetMediaPoolItem() != None:
                    editEvent = {}
                    editEvent['EventNr'] = str(n + 1).zfill(3)
                    editEvent['Clip Name'] = item.GetName()
                    editEvent['FrameRecIn'] = item.GetStart()
                    editEvent['FrameRecOut'] = item.GetEnd()
                    editEvent['duration'] = item.GetDuration()
                    editEvent['File Path'] = (item.GetMediaPoolItem().GetClipProperty('File Path')).replace('\\', '/')
                    editEvent['Id'] = item.GetMediaPoolItem().GetMediaId()
                    EventsList.append(editEvent)
                else:
                    # if not self.checkbox4.isChecked():
                    #     MainWindow.showInfo(self, "Warning", item.GetName()+" not found in MediaPool")
                    continue
            prjData['VideoTrack ' + str(i)] = EventsList
        # print (json.dumps(prjData, sort_keys=False, indent=3))
        return prjData

    def getmwfFile(self,filePath,jsonData):
        mwfsWorkPath = filePath
        jsonTmpPath = self.jsonWorkPath
        (mwfsWorkPath).replace('/', '\\')
        try:
            with open(jsonTmpPath, 'w') as f:
                f.write(json.dumps(jsonData, sort_keys=False, indent=3))
            f.close()
            with open (mwfsWorkPath,'r') as f:
                mwfContent=f.read()
            f.close()
            mwfModif=mwfContent.replace("JSONFILE-FROMDVR-WORKFLOWSLAUNCHER",jsonTmpPath)
            with open (self.mwfFilePath,'w') as f:
                f.write(mwfModif)
            f.close()
        except:
            return False
        return self.mwfFilePath

    def openFileDialog(self):
        fileDialog = QFileDialog(self)
        fileDialog.setDirectory(self.homeDir)
        mwfFile = fileDialog.getOpenFileName(self, "Select your .mwf file", "", "Mistika Workflows files (*.mwf);;All Files (*)")
        if mwfFile != ('', ''):
            self.filePath = mwfFile[0]
            mwfs = MainWindow.processMWF(self,mwfFile[0])
            self.homeDir = os.path.dirname(mwfFile[0])
            self.currentState=MainWindow.getCurrentState(self)
            MainWindow.clearUI(self)
            MainWindow.buildUI(self,mwfs)
            return
        else:
            return

    def refreshAction(self):
        if os.path.exists(self.filePath):
            nTabs=self.tabWidget.count()
            for i in reversed(range(0,nTabs)):
                self.tabWidget.removeTab(i)
            mwfs = MainWindow.processMWF(self,self.filePath)
            MainWindow.buildUI(self,mwfs)
        return

    def saveLastPaths(self):
        lastPaths={}
        lastPaths['OpenFileDialog']=self.homeDir
        lastPaths['WatchFolder']=self.WatcherPath
        try:
            with open(self.LocalCfg, 'w') as f:
                f.write(json.dumps(lastPaths, sort_keys=False, indent=3))
            f.close()
        except:
            print ('Could not save last file paths in config file '+ self.LocalCfg)
        return

    def okButtonClicked(self):
        jsonData = MainWindow.processJson(self)
        # print(json.dumps(jsonData, sort_keys=False, indent=3))
        if self.checkbox2.isChecked() and not self.checkbox1.isChecked():
            self.checkbox1.setChecked(True)
        if not self.checkbox1.isChecked() and not self.checkbox3.isChecked():
            MainWindow.showInfo(self,"Warning","Please select Launch Mistika Workflows or Use Watch Folder")
            return
        if self.checkbox1.isChecked():
            if not self.filePath:
                MainWindow.showInfo(self,"Info","No Workflows .mwf file has been loaded")
                return
            else:
                self.mwfFilePath=MainWindow.getmwfFile(self,self.filePath,jsonData)
            if self.checkbox2.isChecked():
                execline = f'"{self.EXEPath}" -r  "{self.mwfFilePath}"'
            else:
                execline = f'"{self.EXEPath}" -A  "{self.mwfFilePath}"'
                print(execline)
            subprocess.Popen(execline,shell=True)
            MainWindow.showInfo(self, "Info", "Workflow " + self.myMWF +".mwf" + " launched")

        if self.checkbox3.isChecked():
            if not self.WatcherPath:
                MainWindow.showInfo(self,"Info","No Watch Folder has been selected")
                return
            jsonID=self.myMWF+'-'+self.myTimeline+'_'+self.DateID
            jsonfilePath=self.WatcherPath+jsonID+'.json'
            try:
                with open(jsonfilePath, 'w') as f:
                    f.write(json.dumps(jsonData, sort_keys=False, indent=3))
                f.close()
                MainWindow.showInfo(self, "Info", "json File "+ jsonID+ " sent to Watch Folder")
            except:
                MainWindow.showInfo(self,"Warning","Couldn't write json File in Watcher Folder")
        MainWindow.saveLastPaths(self)
        return

    def cancelButtonClicked(self):
        MainWindow.saveLastPaths(self)
        QApplication.instance().quit()
        return

    def saveFilePathClicked(self):
        savefilePath=QFileDialog(self)
        savefilePath.setDirectory(self.WatcherPath)
        userfilePath = savefilePath.getExistingDirectory(self, "Select Watcher Folder")
        if userfilePath:
            self.saveFilePathField.setText(userfilePath)
            self.WatcherPath=userfilePath+'/'
            self.checkbox3.setChecked(True)
        return

    def showInfo(self, flag, message):
        infoMessage = message
        if flag == "Info":
            QMessageBox.information(self, "Info", infoMessage, QMessageBox.Ok)
        elif flag == 'Warning':
            QMessageBox.warning(self, "Warning", infoMessage, QMessageBox.Ok)
        return

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()



