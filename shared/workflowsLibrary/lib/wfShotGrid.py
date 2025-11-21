import os
from shotgun_api3 import Shotgun

class CwfShotGrid:
    CREDENTIALS_TYPES_UNKNOWN=0
    CREDENTIALS_TYPES_API=1
    CREDENTIALS_TYPES_USERPWD=2
    CUSTOM_VALUE="Custom"
    CUSTOM_LIST=[CUSTOM_VALUE]
    PRIVATE_DATA="ShotGrid"
    UPLOAD_NONE=0
    UPLOAD_FILE=1
    UPLOAD_THUMBNAIL=2
    
    def __init__(self, node):
        self.m_node = node
        self.m_sg=None
        self.m_projects=None
        self.m_templates=None     
        
    def connect(self):
        try:
            if self.credentialsType()==self.CREDENTIALS_TYPES_API:
                self.m_sg=Shotgun(self.url(),script_name=self.scriptName(),api_key=self.apiKey())
                self.m_sg.connect()
            elif self.credentialsType()==self.CREDENTIALS_TYPES_USERPWD:
                self.m_sg=ShotGrid(lf.url(),login=self.user(),password=self.pwd())
                self.m_sg.connect()
            else:
                self.m_sg=None
                return False
        except Exception as e:
            return self.m_node.critical("CwfShotGrid:connect:Exception",e)            
        return True
                    
    def getList(self,table,filter,fields,name):
        print ("getList",table,filter,fields,name)
        res=self.m_sg.find(table,filter,fields)
        list=[item[name] for item in res]
        print (list)
        return list           

    def find(self,table,filter,fields):
        result=None
        if not self.m_sg:
            return self.m_node.critical("CwfShotGrid:filter:disconnected","Not Connected to ShotGrid")
        try:            
            result=self.m_sg.find(table,filter,fields)
        except Exception as e:
            self.m_node.critical("CwfShotGrid:find:Exception","{},{},{},{}".format(e,table,filter,fields))
            return None
        print (table,result)
        return result
            
    def uploadFile(self,uploadType,table,id,filePath,name,):
        res=None
        fp=os.path.normpath(filePath)
        print (filePath,fp)
        if not self.m_sg:
            return self.m_node.critical("CwfShotGrid:uploadFile:disconnected","Not Connected to ShotGrid")
        try:
            print ("uploadFile",uploadType,table,id,fp,name)
            res=None
            if uploadType==self.UPLOAD_FILE:
                if table=="Version":
                    res=self.m_sg.upload(table,id,fp,display_name=name,field_name="sg_uploaded_movie")
                else:
                    res=self.m_sg.upload(table,id,fp,display_name=name)
            elif uploadType==self.UPLOAD_THUMBNAIL:
                res=self.m_sg.upload_thumbnail(table,id,fp)
            if not res:                
                self.m_node.critical("CwfShotGrid:uploadFile:notUploaded","Unable to upload file: {},{},{},{},{}".format(uploadType,table,id,fp,name))
            print ("uploadFile",res)
        except Exception as e:
            self.m_node.critical("CwfShotGrid:uploadFile:Exception","{},{},{},{},{},{}".format(e,table,id,filePath,name))
            return None
        return res
          
    def url(self):
        return self.m_node.url;
          
    def credentialsType(self):
        return int(self.m_node.credentialsType);
        
    def scriptName(self):
        return self.m_node.scriptName;
    def apiKey(self):
        return self.m_node.apiKey;
    def user(self):
        return self.m_node.user;
    def pwd(self):
        return self.m_node.pwd;
        
    def isReady(self):
        res=True
        if self.credentialsType()==CwfShotGrid.CREDENTIALS_TYPES_API:
            if self.apiKey().strip()=="":
                res=self.m_node.critical("CwfShotGrid:isReady:apiKey","apiKey can not be empty") and res
            if self.scriptName().strip()=="":
                res=self.m_node.critical("CwfShotGrid:isReady:scriptName","scriptName can not be empty") and res
        elif self.credentialsType()==CwfShotGrid.CREDENTIALS_TYPES_USERPWD:
            if self.user().strip()=="":
                res=self.m_node.critical("CwfShotGrid:isReady:user","user can not be empty") and res
            if self.pwd().strip()=="":
                res=self.m_node.critical("CwfShotGrid:isReady:pwd","pwd can not be empty") and res     
        return res
    
    def findOne(self,table,filter,fields=None):
        result=None
        try:           
            print ("findOne",table,filter,fields)
            result = self.m_sg.find_one(table,filter,fields)
            print ("found",result)
        except Exception as e:
            self.m_node.critical("CwfShotGrid:findOne:Exception","{},{},{},{}".format(e,table,filter,fields))
        return result
    
    def create(self,table,data):
        result=None
        try:           
            print ("creating",table,data)
            result = self.m_sg.create(table, data)
            print ("created",result)
        except Exception as e:
            self.m_node.critical("CwfShotGrid:create:Exception","{},{},{}".format(e,table,data))
            return None
        return result
    @staticmethod
    def getValue(source,param,up):
        param=param.strip()
        if source=="From Token":
            mfid=up.getMediaFileInfoData()
            v=mfid.getToken(param)    
            return v
        else:
            return param
                
    def createToFilter(self,data):
        res=[]
        for key in data:
            item=[key,'is',data[key]]
            res.append(item)
        return res
        
        