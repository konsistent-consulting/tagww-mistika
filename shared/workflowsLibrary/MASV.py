from Mistika.classes import Cconnector, CuniversalPath, CnameConvention
from Mistika.Qt import QColor
import requests
import os
import json
import time
import re


def init(self):
    self.setClassName("MASV")
    self.color = QColor(0x03d6b3)

    self.addConnector("files", Cconnector.CONNECTOR_TYPE_INPUT, Cconnector.MODE_REQUIRED)
    self.addConnector("links", Cconnector.CONNECTOR_TYPE_OUTPUT, Cconnector.MODE_OPTIONAL)

    self.addEncryptedProperty("apiKey")
    self.addProperty("teamID")
    self.addProperty("baseAPIUrl", "https://api.massive.app/v1")
    self.addProperty("packageName")
    self.addProperty("description")
    self.addProperty("recipients")
    self.addProperty("PackageLink")

    self.addProperty("_chunkList", ['50 Mb$$$50', '100 Mb$$$100', '150 Mb$$$150', '200 Mb$$$200'])
    self.addProperty("chunksize", 100)

    self.addProperty("recipients_list")

    self.bypassSupported = True
    self.setSupportedTypes(self.NODETYPE_OUTPUT)


def isReady(self):
    def getValidEmails(email_string):
        result = True
        if not email_string.strip():
            return [], result

        email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        emails = [email.strip() for email in email_string.split(",")]
        valid_emails = [email for email in emails if re.match(email_pattern, email)]
        if len(valid_emails) != len(emails):
            result = False
            errEmails = [elem for elem in emails if elem not in valid_emails]
            strErrEmails = ",".join(errEmails)
            self.info("massiveIO:isReady:recipients",
                      f"Some email address {'is' if len(errEmails) == 1 else 'are'} not valid ({strErrEmails}). Removed from recipient notification.")
        return valid_emails, result

    if self.bypassSupported and self.bypassEnabled:
        return True

    res = True
    if not self.apiKey.strip():
        self.critical("massiveIO:isReady:apiKey", "API Key cannot be empty.")
        res = False
    if not self.teamID.strip():
        self.critical("massiveIO:isReady:teamID", "Team ID cannot be empty.")
        res = False
    if not self.baseAPIUrl.strip():
        self.critical("massiveIO:isReady:baseAPIUrl", "Base API URL cannot be empty.")
        res = False
    if not self.packageName.strip():
        self.critical("massiveIO:isReady:packageName", "Package Name cannot be empty.")
        res = False
    if self.chunksize <= 0:
        self.critical("massiveIO:isReady:chunksize", "Chunksize must be an integer greater than zero.")
        res = False

    self.recipients_list, res = getValidEmails(self.recipients)
    if not self.recipients_list:
        self.info("massiveIO:isReady:recipients", "No valid email found. Upload without recipient notification.")

    return res


def process(self):
    def createPackage(self, packageName, description):
        url = f"{self.baseAPIUrl}/teams/{self.teamID}/packages"
        headers = {
            "X-API-KEY": self.apiKey,
            "Content-Type": "application/json"
        }
        payload = {
            "name": packageName,
            "description": description,
            "password": "",
            "recipients": self.recipients_list
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["access_token"], data["id"]

    def uploadFile(self, packageId, filePath, accessToken):
        fileName = os.path.basename(filePath)
        url = f"{self.baseAPIUrl}/packages/{packageId}/files"
        headers = {
            "X-Package-Token": accessToken,
            "Content-Type": "application/json"
        }
        payload = {
            "kind": "file",
            "name": fileName,
            "path": ""
        }
        print("massiveIO:process:info", f"uploadFile Creating file: {url}  {payload}")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        print("massiveIO:process:info", f"uploadFile Created File - response: {response.text}")
        fileId = data["file"]["id"]

        blueprint = data.get("create_blueprint") or data.get("createBlueprint", {})
        uploadUrl = blueprint.get("url")
        method = blueprint.get("method")
        uploadHeaders = blueprint.get("headers", {})

        response = requests.request(method, uploadUrl, headers=uploadHeaders)
        response.raise_for_status()
        print("massiveIO:process:info", f"uploadFile Created Blueprint - response: {response.text}")

        uploadId = response.text.split("<UploadId>")[1].split("</UploadId>")[0].strip()

        fileSize = os.path.getsize(filePath)
        ("massiveIO:process:info", f"uploadFile Created Blueprint - fileSize: {fileSize}")
        self.chunksize = self.chunksize if isinstance(self.chunksize, int) else 100
        chunkSizeBytes = self.chunksize * 1024 * 1024
        print("massiveIO:process:info", f"uploadFile Created Blueprint - chunkSizeBytes: {chunkSizeBytes}")
        numChunks = max(1, (fileSize + chunkSizeBytes - 1) // chunkSizeBytes)
        print("massiveIO:process:info", f"uploadFile Created Blueprint - numChunks: {numChunks}")

        url = f"{self.baseAPIUrl}/packages/{packageId}/files/{fileId}?start=0&count={numChunks}"
        print("massiveIO:process:info", f"uploadFile url prepared: {url}")
        headers = {
            "X-Package-Token": accessToken,
            "Content-Type": "application/json"
        }
        payload = {"upload_id": uploadId}
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print("massiveIO:process:info", f"uploadFile UploadID - response: {response.text}")

        uploadTasks = [(item["url"], item["method"]) for item in response.json()]

        return uploadTasks, uploadId, fileId, fileSize

    def uploadToS3(self, uploadUrl, method, filePath, partNumber):
        chunkSizeBytes = self.chunksize * 1024 * 1024
        with open(filePath, "rb") as f:
            f.seek((partNumber - 1) * chunkSizeBytes)
            chunk = f.read(chunkSizeBytes)
            response = requests.request(method, uploadUrl, data=chunk)
        response.raise_for_status()
        print("massiveIO:process:info",
              f"uploadToS3 - filePath: {filePath} - partNumber: {partNumber} - response: {response.text}")

        return {"partNumber": str(partNumber), "etag": response.headers.get("ETag", "").strip('"')}

    def finalizeUpload(self, packageId, fileId, uploadId, etagList, accessToken, fileSize):
        url = f"{self.baseAPIUrl}/packages/{packageId}/files/{fileId}/finalize"
        headers = {
            "X-Package-Token": accessToken,
            "Content-Type": "application/json"
        }
        payload = {
            "size": fileSize,
            "file_extras": {"upload_id": uploadId},
            "chunk_extras": etagList
        }
        response = requests.post(url, headers=headers, json=payload)
        print("massiveIO:process:info", f"finalizeUpload - response: {response.text}")
        response.raise_for_status()

    def finalizePackage(self, packageId, accessToken):
        url = f"{self.baseAPIUrl}/packages/{packageId}/finalize"
        headers = {
            "X-Package-Token": accessToken,
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers)
        response.raise_for_status()

    def get_downloadLink(self, accessToken, packageId):
        try:
            headers = {
                "X-Package-Token": accessToken,
                "Content-Type": "application/json"
            }
            body = {
                "email": "",
                "password": ""
            }
            url = f"{self.baseAPIUrl}/packages/{packageId}/links"
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            downloadID = data.get("id")
            downloadSecret = data.get("download_secret")
            print("massiveIO:process:info", f"get_downloadLink - id: {downloadID} - secret: {downloadSecret}")

            if not downloadID or not downloadSecret:
                self.critical("massiveIO:get_downloadLink:error", "Missing download ID or secret in response.")
                return []

            url = ""
            if self.PackageLink:
                url = f"https://get.massive.io/{downloadID}?secret={downloadSecret}"

            return url

        except requests.RequestException as e:
            self.critical("massiveIO:get_downloadLink:exception", f"Exception while getting download links: {str(e)}")
            return []

    if self.bypassEnabled:
        return True

    output = self.getFirstConnectorByName("links")
    output.clearUniversalPaths()
    inputs = self.getConnectorsByType(Cconnector.CONNECTOR_TYPE_INPUT)
    filesToUpload = []

    try:
        accessToken = packageId = ""
        for connector in inputs:
            for up in connector.getUniversalPaths():
                packageName = self.evaluate(self.packageName).strip()
                strOpackageName = up.getStringOverride(packageName)
                description = self.evaluate(self.description).strip()
                strOdescription = up.getStringOverride(description)
                print(f"packageName: {strOpackageName}  -  description: {strOdescription}")

                filesToUpload = up.getAllFiles()
                print("FilesToUpload: {filesToUpload}")
                if not filesToUpload:
                    raise ValueError("No files found to upload.")
                for filePath in filesToUpload:
                    if not accessToken or not packageId:
                        accessToken, packageId = createPackage(self, strOpackageName, strOdescription)
                        print("massiveIO:process:info",
                              f"created Package - packageId: {packageId} - accessToken: {accessToken}")

                    fileName = os.path.basename(filePath)
                    print("massiveIO:process:info", f"File to be uploaded: {fileName}")
                    uploadTasks, uploadId, fileId, fileSize = uploadFile(self, packageId, filePath, accessToken)

                    print("massiveIO:process:def onPropertyUpdated(self, name):info",
                          f"uploadFile done {fileName} - fileId: {fileId} - fileSize: {fileSize}")

                    etagList = []
                    for partNumber, (uploadUrl, method) in enumerate(uploadTasks, start=1):
                        etagList.append(uploadToS3(self, uploadUrl, method, filePath, partNumber))

                    print("massiveIO:process:info", f"uploadToS3 done {fileName} - fileId: {fileId}")

                    finalizeUpload(self, packageId, fileId, uploadId, etagList, accessToken, fileSize)
                    print("massiveIO:process:info", f"finalizeUpload done {fileName} - fileId: {fileId}")

        # when upload files loop finished, close package
        if packageId and accessToken:
            finalizePackage(self, packageId, accessToken)
            downloadLink = get_downloadLink(self, accessToken, packageId)
            print("massiveIO:process:info", f"Download links JSON: {downloadLink}")
            nc = self.getWorkflow().getNameConvention()
            outUP = CuniversalPath(nc, strOpackageName)
            outUP.setPrivateData("packageLink", downloadLink)
            output.addUniversalPath(outUP)

        self.info("massiveIO:process:success", "File uploaded and package finalized successfully.")
        return True

    except Exception as e:
        self.critical(f"massiveIO:process:exception", f"Exception during upload: {str(e)}")
        return False
