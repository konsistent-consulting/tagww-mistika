from Mistika.classes import Cconnector
from Mistika.Qt import QColor
from wfShotGrid import CwfShotGrid

def onPropertyUpdated(self,name):
    print ("onPropertyUpdated",name)
    param=None
    prop=None 
    try:
        if name=="credentialsType":
            t=int(self.credentialsType)
            self.setPropertyVisible("scriptName",t==CwfShotGrid.CREDENTIALS_TYPES_API)
            self.setPropertyVisible("apiKey",t==CwfShotGrid.CREDENTIALS_TYPES_API)
            self.setPropertyVisible("user",t==CwfShotGrid.CREDENTIALS_TYPES_USERPWD)
            self.setPropertyVisible("pwd",t==CwfShotGrid.CREDENTIALS_TYPES_USERPWD)
        elif name=="table":
            print (self.table)
            isAsset=self.table=="Asset"
            isSeq=self.table=="Sequence"
            isShot=self.table=="Shot"
            isVersion=self.table=="Version"
            self.setPropertyVisible("asset",isAsset)
            self.setPropertyVisible("sequence",isSeq or isShot)
            self.setPropertyVisible("shot",isShot or isVersion)
            self.setPropertyVisible("taskTemplate",isShot)
            self.setPropertyVisible("version",isVersion)
            self.setPropertyVisible("task",isVersion)
            self.setPropertyVisible("taskTemplateList",isShot)
        elif name=="projectList":
            if self.projectList!=CwfShotGrid.CUSTOM_VALUE:
                self.project=self.projectList
                self.projectList=CwfShotGrid.CUSTOM_VALUE
        elif name=="taskTemplateList":
            if self.taskTemplateList!=CwfShotGrid.CUSTOM_VALUE:
                self.taskTemplate=self.taskTemplateList         
    except AttributeError:
        pass
                
def init(self):
    def addGroup(name):
        self.addProperty("{}List".format(name),CwfShotGrid.CUSTOM_VALUE)
        self.addProperty("_{}List".format(name),CwfShotGrid.CUSTOM_LIST)
        self.addProperty(name)

    self.setClassName("ShotGrid Create")
    self.addProperty("credentialsType",CwfShotGrid.CREDENTIALS_TYPES_API)
    self.addProperty("restSrv","https://sgoengineering.shotgrid.autodesk.com")
    self.addProperty("scriptName")
    self.addEncryptedProperty("apiKey")
    self.addProperty("user")
    self.addEncryptedProperty("pwd")
    
    self.addProperty("table","Shot")
    addGroup("project")
    self.addProperty("asset")
    self.addProperty("sequence")
    self.addProperty("shot")
    addGroup("taskTemplate")
    self.addProperty("version")
    self.addProperty("task")
    self.addProperty("status",'act')
    self.addProperty("_statusList",["Active$$$act"])
    self.addProperty("upload",CwfShotGrid.UPLOAD_NONE)
    self.addConnector("files",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("created",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"files_%") 
    self.color=QColor(0x38a6cc)
    self.bypassSupported=True
    self.addActionToContextMenu("Reload Tables")
    #if the node is part of a workflow, initialize the projects list
    onPropertyUpdated(self,"credentialsType")
    onPropertyUpdated(self,"table")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res=True
    sg=CwfShotGrid(self)
    res=sg.isReady() and res
    if self.project.strip() == "":
        res=self.critical("SgotGrid:isReady:project","Project can not be empty")
    return res
 
def process(self):            
    def getRelatedName(table,up):
        print ("getRelatedName",table)
        if table=='Project':
            return ['name',up.getStringOverride(self.project.strip())]
        elif table=='Asset':
            return ['code',up.getStringOverride(self.asset.strip())]
        elif table=='Sequence':
            return ['code',up.getStringOverride(self.sequence.strip())]
        elif table=='Shot':
            return ['code',up.getStringOverride(self.shot.strip())]
        elif table=='Version':
            return ['code',up.getStringOverride(self.version.strip())]
        elif table=='Task':
            return ['content',up.getStringOverride(self.task.strip())] 
        return None    
        
    def getRelatedData(table,name,up,sg):
        data=None
        project=up.getStringOverride(self.project.strip())
        if table=='Project':
            data = { 'name': name}
        elif table=='Asset':
            prj=sg.findOne('Project',[['name',"is",project]],['id','name'])
            if not prj:
                return self.critical("SgotGrid:getRelatedData:project","Unable to find project {}".format(project))
            data = { 'project': {'type': 'Project','id': prj['id']},'code': name}
        elif table=='Sequence':
            prj=sg.findOne('Project',[['name',"is",project]],['id','name'])
            if not prj:
                return self.critical("SgotGrid:getRelatedData:project","Unable to find project {}".format(project))
            data = { 'project': {'type': 'Project','id': prj['id']},'code': name}
        elif table=='Shot':
            prj=sg.findOne('Project',[['name',"is",project]],['id','name'])
            if not prj:
                return self.critical("SgotGrid:getRelatedData:project","Unable to find project {}".format(project))
            data = { 'project': {'type': 'Project','id': prj['id']},'code': name}
            seqName=up.getStringOverride(self.sequence.strip())
            if (seqName!=""):
                sequence=sg.findOne('Sequence',[['project', 'is', {"type": "Project", 'id': prj['id']}],['code',"is",seqName]],['id','code'])
                if not sequence:
                    return self.critical("SgotGrid:getRelatedData:sequence","Unable to find sequence {}".format(project))
                data['sg_sequence']={'type': 'Sequence','id': sequence['id']}
            templateName=up.getStringOverride(self.taskTemplate.strip())
            if (templateName!=""):
                template=sg.findOne('TaskTemplate',[['code',"is",templateName]],['id','code'])
                if not template:
                    return self.critical("SgotGrid:getRelatedData:template","Unable to find template {}".format(templateName))
                data['task_template']={'type': 'TaskTemplate','id': template['id']}
        elif table=='Version':
            prj=sg.findOne('Project',[['name',"is",project]],['id','name'])
            if not prj:
                return self.critical("SgotGrid:getRelatedData:project","Unable to find project {}".format(project))
            data = { 'project': {'type': 'Project','id': prj['id']},'code': name}
            shotName=up.getStringOverride(self.shot.strip())
            if (shotName!=""):
                shot=sg.findOne('Shot',[['project', 'is', {"type": "Project", 'id': prj['id']}],['code',"is",shotName]],['id','code'])
                if not shot:
                    return self.critical("SgotGrid:getRelatedData:shot","Unable to find shot {}".format(shotName))
                data['entity']={'type': 'Shot', 'id': shot['id']}
            taskName=up.getStringOverride(self.task.strip())
            if (taskName!=""):            
                taskFilters = [['project', 'is', {"type": "Project", 'id': prj['id']}],
                        ['entity', 'is',{'type':'Shot', 'id': shot['id']}],
                        ['content', 'is', taskName]]
                task=sg.findOne('Task',taskFilters,['id','code'])                 
                if not task:
                    return self.critical("SgotGrid:getRelatedData:task","Unable to find task {}".format(taskName))
                data['sg_task']={'type': 'Task', 'id': task['id']}                        
        print ("getRelatedData",data)
        return data
        
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    out=self.getFirstConnectorByName("created")
    out.clearUniversalPaths()
    if self.bypassEnabled:
        return True    
    sg=CwfShotGrid(self)
    sg.connect() 
    prj=self.project.strip()
    seq=self.sequence.strip()
    template=self.taskTemplate.strip()
    table=self.table.strip()
    isVersion=table=="Version"
    upload=int(self.upload)
    res=True
    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            self.info("SgotGrid:process:input","Processing {}".format(up.getFileName()))
            print ("table",table)
            [name,value]=getRelatedName(table,up)
            print ("getRelatedName result",name,value)
            record=None
            data=getRelatedData(table,value,up,sg)
            error=False
            if data:
                record=sg.findOne(table,sg.createToFilter(data))#[[name,"is",value]],["id",name])
                if record:
                    self.warning("SgotGrid:process:alreadyExist","{} {} not created. It already exists".format(table,value))
                else:
                    if self.status:
                        data['sg_status_list']=self.status
                    record=sg.create(table,data)
                if record:
                    print ("record",record)
                    data=up.getPrivateData(sg.PRIVATE_DATA)
                    if not data:
                        data={}
                    data[table]={'id':record['id']}
                    up.setPrivateData(sg.PRIVATE_DATA,data)
                    out.addUniversalPath(up)
                    print ("upload",upload)
                    if upload:
                        if not sg.uploadFile(upload,table,record['id'],up.getFilePath(),up.getFileName()):
                            error=True
                else:
                    error=True
            else:
                error=True
            if error:
                self.addFailedUP(up)
            res=res and not error
    return res
    
def menuAction(self,name):
    print ("menuAction",name)
    if name=="Reload Tables":
        sg=CwfShotGrid(self)
        try:
            sg.connect()
            self._projectList=CwfShotGrid.CUSTOM_LIST+sg.getList('Project',[["sg_status", "is", "Active"],["is_demo", "is_not", True]],['is_demo','sg_status','id','name'],'name')
            self.projectList=CwfShotGrid.CUSTOM_VALUE
            list=CwfShotGrid.CUSTOM_LIST+sg.getList('TaskTemplate',[],['id','code'],'code')
            self._taskTemplateList=list
            self.taskTemplateList=CwfShotGrid.CUSTOM_VALUE
            
            list=sg.find("Status",[],['id','code','name'])
            statusList=[]
            for item in list:
                statusList.append(item['name']+"$$$"+item['code'])
            self._statusList=statusList;
            print ("list",self._statusList)
            
        except Exception as e:
            print (e)
            pass  