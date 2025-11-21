import mimetypes
import http.client
import httplib2
import random
import time
from Mistika.classes import Cconnector
from Mistika.Qt import QColor

from apiclient.errors import HttpError
from apiclient.http import MediaFileUpload
from googleAuth import GoogleAuth
import json
            
class YouTubeTools:
    def __init__(self, node):
        self.m_node = node

    # Explicitly tell the underlying HTTP transport library not to retry, since
    # we are handling retry logic ourselves.
    httplib2.RETRIES = 1
    # Maximum number of times to retry before giving up.
    MAX_RETRIES = 5
    # Always retry when these exceptions are raised.
    RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
        http.client.IncompleteRead, http.client.ImproperConnectionState,
        http.client.CannotSendRequest, http.client.CannotSendHeader,
        http.client.ResponseNotReady, http.client.BadStatusLine)
    # Always retry when an apiclient.errors.HttpError with one of these status
    # codes is raised.
    RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
        
    def initialize_upload(self, youtube, f, title, description, category, keywords, privacyStatus):
        tags = None
        if keywords:
            tags = keywords.split(",")

        body=dict(
            snippet=dict(title=title, description=description, tags=tags, categoryId=category),
            status=dict(privacyStatus=privacyStatus)
        )

        # Call the API's videos.insert method to create and upload the video.
        insert_request = youtube.videos().insert(
            part=",".join(list(body.keys())),
            body=body,
            media_body=MediaFileUpload(f, chunksize= -1, resumable=True)
        )

        self.resumable_upload(insert_request)

    # This method implements an exponential backoff strategy to resume a failed upload.
    def resumable_upload(self, insert_request):
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                self.m_node.info("youtube:uploading", "Uploading file...")
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        self.m_node.info("youtube:uploaded", "Video id '%s' was successfully uploaded." % response['id'])
                    else:
                        return self.m_node.critical("youtube:uploadFailed", "The upload failed with an unexpected response: %s" % response)
            except HttpError as e:
                if e.resp.status in self.RETRIABLE_STATUS_CODES:
                    error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status, e.content)
                else:
                    raise
            except self.RETRIABLE_EXCEPTIONS as e:
                error = "A retriable error occurred: %s" % e

                if error is not None:
                    self.m_node.warning("youtube:error", error) 
                    retry += 1
                    if retry > self.MAX_RETRIES:
                        return self.m_node.critical("youtube:cnoRetriesLeft", "No longer attempting to retry.")

                    max_sleep = 2 ** retry
                    sleep_seconds = random.random() * max_sleep
                    self.m_node.warning("youtube:clientId", "Sleeping %f seconds and then retrying..." % sleep_seconds)
                    time.sleep(sleep_seconds)
    
    def checkIfFileIsVideo(self, file):      
        return str(mimetypes.guess_type(file)[0]).startswith('video')

def init(self):
    self.color = QColor(0xAA1512)
    self.addConnector("in", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_OPTIONAL)
    self.addConnector("out", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)
    self.addProperty("TermsOfServices", "<a href=\"https://www.youtube.com/t/terms\">'YouTube's Terms of Services'</a>")
    self.addProperty("clientId")
    self.addEncryptedProperty("clientSecret")
    self.addProperty("title", "Example title")
    self.addProperty("description", "Example description")
    self.addProperty("category", "1")
    self.addProperty("keywords", "keyword1, keyword2, etc")
    self.addProperty("privacyStatus", "public")
    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)
    self.setComplexity(100)
    self.setAcceptConnectors(True, "in")
    self.addProperty("credentialsString", "")  
    self.addProperty("_credentialsDict", {})
    self.addActionToContextMenu("Authenticate")
    return True

def isReady(self):
    if self.bypassSupported and self.bypassEnabled:
        return True
    res = True
    if not self.clientId.strip():
        res = self.critical("youtube:clientId", "'clientId' can not be empty") and res
    if not self.clientSecret.strip():
        res = self.critical("youtube:clientSecret", "'clientSecret' can not be empty") and res
    if not self.title.strip():
        res = self.critical("youtube:title", "'title' can not be empty") and res
    if not self.description.strip():
        res = self.critical("youtube:description", "'description' can not be empty") and res
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

    title = self.title.strip()
    description = self.description.strip()
    category = self.category
    keywords = self.keywords.strip()
    privacyStatus = self.privacyStatus
    
    YouTube = YouTubeTools(self)
    
    self._credentialsDict = {} if not self.credentialsString else json.loads(self.credentialsString)
    goo = GoogleAuth(self, "https://www.googleapis.com/auth/youtube.upload", "youtube", "v3", self._credentialsDict)
    drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
    self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId)

    if drive == "TimeOut": 
        return self.critical("youtube:process:authCanceled", "Authentication timeout")
    elif drive == None:
        return False
    if self.credentialsString == None or self.credentialsString == "{}": 
        return self.critical("youtube:process:authCanceled", "Authentication was rejected") 

    for c in inputs:
        for up in c.getUniversalPaths():
            files = up.getAllFiles()
            for f in files:
                if self.isCancelled():
                    return False
                if YouTube.checkIfFileIsVideo(f):
                    try:
                        YouTube.initialize_upload(drive, f, title, description, category, keywords, privacyStatus)
                    except HttpError as e:
                        res = self.critical("YouTube:process:uploaderror","An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
                else: self.warning("YouTube:process:notvideo","'{}' is not a video file".format(f))
            out.addUniversalPath(up)
    return res

def onPropertyUpdated(self, name):
    a = 1

def menuAction(self,name):
    print ("menuAction",name)
    if name=="Authenticate":
        self.credentialsString = ""
        self._credentialsDict = {}
        goo = GoogleAuth(self, "https://www.googleapis.com/auth/youtube.upload", "youtube", "v3", self._credentialsDict)
        drive = goo.get_authenticated_service(self.clientId.strip(), self.clientSecret.strip(), 60)
        self.credentialsString = goo.updateCredentials(self._credentialsDict, self.clientId)

        if drive == "TimeOut": 
            return self.critical("GoogleDriveIn:process:authCanceled", "Authentication timeout")
        if self.credentialsString == None or self.credentialsString == "{}": 
            return self.critical("GoogleDriveIn:process:authCanceled", "Authentication was rejected") 