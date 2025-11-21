from Mistika.Qt import QColor
from Mistika.classes import Cconnector,CbaseItem,CuniversalPath,CnameConvention
from zeep import Client, Settings
from zeep.helpers import serialize_object
import time
import os

def init(self):      
    self.setClassName("Pulsar")
    self.color=QColor(0xee7f1d)
    self.addConnector("in",Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("reports",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL) 
    self.addConnector("passed",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.addConnector("failed",Cconnector.CONNECTOR_TYPE_OUTPUT,Cconnector.MODE_OPTIONAL)
    self.setAcceptConnectors(True,"in_%") 
    self.addProperty("ip", "127.0.0.1")
    self.addProperty("port", "8093")
    self.addProperty("templateType", "0")
    self.addProperty("templateId", "")
    self.addProperty("_templateList")
    if self._templateList=="":
        try:
            client = Client(wsdl="http://"+self.ip.strip()+":"+self.port.strip()+"/pulsar?wsdl", settings=Settings(strict=False, xml_huge_tree=True))
            SGetTemplateListReq = client.get_type("ns0:SGetTemplateListReq")
            CSGetTemplateListReq = client.get_type("ns0:CSGetTemplateListReq")
            response = client.service.GetTemplateList(SGetTemplateListReq(CSGetTemplateListReq("",int(self.templateType))))
            self._templateList = response["TemplatesList"]
        except Exception as e:
            self._templateList = ["Error: Not Connected"]
            return print("pulsar:controller", "Error: Pulsar Controller not running, wrong Ip, or wrong port: {}".format(e))
    self.templateId = self._templateList[0]
    self.addProperty("failedWhen", "Error")
    self.addProperty("dstPath")
    self.setDropToProperty("dstPath")
    self.setDropSupportedTypes(1)
    self.bypassSupported=True
    return True

def isReady(self):
    res = True
    if self.bypassSupported and self.bypassEnabled:
        return True
    if self.templateId == "":
        res = self.critical("pulsar:path", "Pulsar Controller not running, wrong Ip, or wrong port") and res
    return res

def process(self):
    def postJob(client, f, dstPath, templateId):
        try:
            SPostJobReq = client.get_type("ns0:SPostJobReq")
            CSPostJobReq = client.get_type("ns0:CSPostJobReq")
            CSFolderAccessInfo = client.get_type("ns0:CSFolderAccessInfo")
            CSAutheticationInfo = client.get_type("ns0:CSAutheticationInfo")
            CSReportLanguageInfo = client.get_type("ns0:CSReportLanguageInfo")
            CSDecryptionKeyInfo = client.get_type("ns0:CSDecryptionKeyInfo")
            CSHDRMetaDataFileInfo = client.get_type("ns0:CSHDRMetaDataFileInfo")
            CSAudioStemInfo = client.get_type("ns0:CSAudioStemInfo")
            CSReferenceFileInfo = client.get_type("ns0:CSReferenceFileInfo")

            response = client.service.PostJob(
                SPostJobReq(
                    CSPostJobReq(
                        CSFolderAccessInfo(eAccessProtocol = 0, strFilePath=f, sAutheticationInfo=CSAutheticationInfo(0, "", "", "")),
                        strFtpMirrorPath="",
                        strUserID="",
                        strUserNote="",
                        strTemplateName=templateId,
                        eFolderType=0,
                        eTemplateType=0,
                        strCustomReportPath=dstPath,
                        strTemplateUpdateData="",
                        sDefaultReportLanguage=CSReportLanguageInfo(strISOCode="", strTag=""),
                        sDecryptionInfo=CSDecryptionKeyInfo(strDecryptionKey=""),
                        nIsHighPriorityJob=0,
                        sHDRMetaDataFileInfo=CSHDRMetaDataFileInfo("","",""),
                        sAudioStemInfo=CSAudioStemInfo(),
                        bStandAloneStemJob=0,
                        sReferenceFileInfo=CSReferenceFileInfo("","","",0)
                                )
                            )
                         )
            print(response)
            return serialize_object(response)
        except Exception as e:
            return {'error': str(e)}
        
    def query_jobs_status(client, job_id):
        try:
            # Obtener los tipos necesarios del WSDL
            SQueryJobsStatusReq = client.get_type("ns0:SQueryJobsStatusReq")
            CSQueryJobsStatusReq = client.get_type("ns0:CSQueryJobsStatusReq")
            CSQueryInfo = client.get_type("ns0:CSQueryInfo")
    
            auth_info = CSQueryInfo(0x002,0, job_id, 0,0,0,0,0,0,0,0)

            query_req = SQueryJobsStatusReq(
                CSQueryJobsStatusReq(
                sQueryInfo=auth_info
            ))
            response = client.service.QueryJobsStatus(QueryReq=query_req)

            #print(response)
            return serialize_object(response)
        except Exception as e:
            return {'error': str(e)}
        
    ######################################################################################################################
    if self.bypassEnabled:
      return True
    inputs=self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT,Cconnector.CONNECTOR_SPECIALTYPE_NORMAL)
    outCorrect = self.getFirstConnectorByName("passed")
    outCorrect.clearUniversalPaths()
    outFailed = self.getFirstConnectorByName("failed")
    outFailed.clearUniversalPaths()
    outReports = self.getFirstConnectorByName("reports")
    outReports.clearUniversalPaths()
    res = True

    templateId = self.templateId.strip()
    dstPath = self.dstPath.strip()
    ip = self.ip.strip()
    port = self.port.strip()

    try:
        client = Client(wsdl="http://"+ip+":"+port+"/pulsar?wsdl", settings=Settings(strict=False, xml_huge_tree=True))
    except Exception as e:
        return self.critical("pulsar:controller", "Error: Pulsar Controller not running, wrong Ip, or wrong port: {}".format(e))

    for c in inputs:
        for up in c.getUniversalPaths():
            if self.isCancelled():
                return False
            #self.setPropertiesFromUP(up)
            #mfid = up.getMediaFileInfoData()
            f = up.getFilePath()
            
            dstPathTokens=up.getStringOverride(dstPath)
            jobResponse = postJob(client, f, dstPathTokens, templateId)
            if jobResponse["eRetCode"] == 6:
                return self.critical("Pulsar:jobFailed", "Error: Template does not exist")
            jobId = jobResponse["strJobId"]

            status = -1
            while status not in [4, 5 ,6]:
                statusResponse= query_jobs_status(client, jobId)
                status = statusResponse["listJobstatus"][0]["eJobStatus"]
                print(status)
                time.sleep(2)
            
            print(statusResponse)
            reportPath = statusResponse["listJobstatus"][0]["strReportPath"]
            print(reportPath)
            
            if status == 4:
                archivos = []
                for archivo in os.listdir(reportPath):
                    path_completo = os.path.join(reportPath, archivo).replace("\\", "/")
                    if os.path.isfile(path_completo) and not archivo.endswith(".html") and archivo != "Template_info.xml":

                        archivos.append(path_completo)
                print(archivos)
                upn = CuniversalPath()
                upList= upn.buildUPfromFileList(archivos, CnameConvention("[path][baseName][.ext]"), reportPath.replace("\\", "/"))
                outReports.setUniversalPaths(upList)

                up.setPrivateData("PulsarReports", archivos)
                error_mapping = {
                    "Info": "nNumberOfInfos",
                    "Warning": "nNumberOfWarnings",
                    "Error": "nNumberOfErrors",
                    "Critical": "nNumberOfCriticals"
                }
                selectedErrorKey = error_mapping[self.failedWhen]
                error_types = ["nNumberOfInfos", "nNumberOfWarnings", "nNumberOfErrors", "nNumberOfCriticals"]
                selectedIndex = error_types.index(selectedErrorKey)
                statusR = statusResponse["listJobstatus"][0]
                if any(statusR[error] > 0 for error in error_types[selectedIndex:]):
                    outFailed.addUniversalPath(up)
                else:
                    outCorrect.addUniversalPath(up)    
            else:
                self.addFailedUP(up)
                res = self.critical("Pulsar:jobFailed", "Error: the job failed or was aborted") and res
        #-------------------------------------------------------------------------------------------------------------------
    return res

def  onPropertyUpdated(self,name):
    try:
        if self._templateList and self.ip and self.port and (name=="templateType" or name=="ip" or name=="port"):
            try:
                ip=self.ip.strip()
                port=self.port.strip()
                client = Client(wsdl="http://"+ip+":"+port+"/pulsar?wsdl", settings=Settings(strict=False, xml_huge_tree=True))
                SGetTemplateListReq = client.get_type("ns0:SGetTemplateListReq")
                CSGetTemplateListReq = client.get_type("ns0:CSGetTemplateListReq")
                response = client.service.GetTemplateList(SGetTemplateListReq(CSGetTemplateListReq("",int(self.templateType))))
                self._templateList = response["TemplatesList"]
            except Exception as e:
                self._templateList = ["Error: Not Connected"]
                return print("pulsar:controller", "Error: Pulsar Controller not running, wrong Ip, or wrong port: {}".format(e))
            self.rebuild()
    except AttributeError:
        pass
