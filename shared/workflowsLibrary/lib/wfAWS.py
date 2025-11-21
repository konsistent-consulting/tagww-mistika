# v 1.1 progress callback added
# v 1.0 initial implementation

import threading
import logging
import boto3
from botocore.exceptions import ClientError, ParamValidationError
import os
import warnings


class wfAWSprogressPercentage:
    def __init__(self, node, size):
        self.m_size = size/1000
        self.m_current = 0
        self.m_node = node
        node.setComplexity(self.m_size if self.m_size>0 else 100)
        self.m_lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self.m_lock:
            self.m_current += bytes_amount/1000
            percentage = round((self.m_current / float(self.m_size)) * 100)if self.m_size>0 else 100
            self.m_node.progressUpdated(percentage)


class wfAWS:
    def __init__(self, node):
        self.m_node = node
        self.m_key = None
        self.m_secret = None
        self.m_bucket = None
        self.m_s3 = None

    def connect(self, key, secret, url = None):
        self.m_key = key
        self.m_secret = secret
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.m_s3 = boto3.client('s3', endpoint_url= url, aws_access_key_id=self.m_key, aws_secret_access_key=self.m_secret)
        except ClientError as e:
            self.m_node.critical("wfAWS:connect:error", "{}".format(e))
            return False
        except ValueError as e:
            self.m_node.critical("wfAWS:connect:error", "{}".format(e))
            return False
        return True

    def checkIfBucketExists(self, bucket):
        self.m_bucket = bucket
        # try:
        #     with warnings.catch_warnings():
        #         warnings.simplefilter("ignore")
        #         buckets = self.m_s3.list_buckets()["Buckets"]
        #     b = next((item for item in buckets if item["Name"] == self.m_bucket), None)
        #     if not b:
        #         #self.m_s3.create_bucket(Bucket=self.m_bucket)
        #         self.m_node.critical("wfAWS:bucketDoesNoExist", "bucket {} does not exist".format(bucket))
        #         return False
        # except ClientError as e:
        #     self.m_node.critical("wfAWS:checkIfBucketExists:error", "{}".format(e))
        #     return False
        return True
    
    def addMetadataToUp(self, upList, metadataList):
        for i, up in enumerate(upList):
            up.readMetadataFromFile()               
            mfid=up.getMediaFileInfoData()
            mfid.setToken("s3metadata", metadataList[i])
            up.setMediaFileInfoData(mfid)

    def uploadFile(self, filePath, objectName=None, metadata = None):
        #print ("uploadFile", "Path: ",filePath, "Name: ", objectName)
        if objectName is None:
            objectName = os.path.basename(filePath)

        sz = os.path.getsize(filePath)

        progressCB = wfAWSprogressPercentage(self.m_node, sz)

        # Upload the file
        try:
            #print ("PATH:", filePath)
            if metadata == None:
                response = self.m_s3.upload_file(filePath, self.m_bucket, objectName, Callback= progressCB)
            else:
                response = self.m_s3.upload_file(filePath, self.m_bucket, objectName, Callback= progressCB, ExtraArgs = {'Metadata': metadata})
        except (boto3.exceptions.S3UploadFailedError, ClientError, ParamValidationError) as e:
            self.m_node.critical("wfAWS:uploadFile:error", "{}".format(e))
            #logging.error(e)
            return False
        return True

    def downloadFile(self, localFilePath, objectName=None):
        #print ("downloadFile", localFilePath, objectName)
        if objectName is None:
            objectName = os.path.basename(localFilePath)
        
        try: 
            headObject = self.m_s3.head_object(Bucket= self.m_bucket, Key=objectName)
            sz = headObject["ContentLength"]
            progress = wfAWSprogressPercentage(self.m_node, sz)
            metadata = headObject["Metadata"]
        # Download the file
            #print ("localFilePath:",localFilePath)
            response = self.m_s3.download_file(self.m_bucket, objectName, localFilePath, Callback=progress)
        except (self.m_s3.exceptions.NoSuchBucket, ClientError, ParamValidationError) as e:
            self.m_node.critical("wfAWS:downloadFile:error", "{}".format(e))
            #logging.error(e)
            return {}
        return metadata

    def includeObject(self, prefix, file):
        return prefix.endswith("/") or file == prefix or file[len(prefix)] == "/" or prefix == ""

    def downloadPath(self, prefix, localPath, deleteAfterDownload, newFilesOnly):
        fileList = []
        metadataList = []
        try:
            try:
                list=self.m_s3.list_objects(Bucket = self.m_bucket, Prefix = prefix)
            except (self.m_s3.exceptions.NoSuchBucket, ClientError, ParamValidationError) as e:
                self.m_node.critical("wfAWS:downloadFile:error", "{}".format(e))
                return False, fileList, metadataList
            if "Contents" in list:
                for bucketObject in list["Contents"]:
                    file = bucketObject["Key"]
                    if self.includeObject(prefix, file):
                        if not file.endswith("/"):
                            if not prefix.endswith("/"):
                                localFilePath = os.path.join(localPath, file)
                            else:
                                localFilePath = os.path.join(localPath, os.path.relpath(file, prefix))
                            
                            dirLocalPath = os.path.dirname(localFilePath)

                            if not os.path.exists(dirLocalPath):
                                os.makedirs(dirLocalPath)

                            if newFilesOnly:
                                try:
                                    fileInfo = os.stat(localFilePath)
                                    self.m_node.warning("wfAWS:downloadFile:fileExist", "{} already exists".format(localFilePath))
                                    continue
                                except FileNotFoundError:
                                    pass
                            fileList.append(localFilePath)
                            metadataList.append(self.downloadFile(localFilePath, file))

                        if deleteAfterDownload and not ((file==prefix and file.endswith("/"))or file == prefix + "/"):
                            self.m_s3.delete_object(Bucket = self.m_bucket, Key = file)
                    else:
                        self.m_node.critical("wafAWS:downloadPath:error", "objectPrefix has to match the name of a Dir or a File")
                        return False, fileList, metadataList
            else:
                self.m_node.critical("wfAWS:downloadPath:error", "No objects with prefix '{prefixMsg}' in bucket".format(prefixMsg=prefix))
                return False, fileList, metadataList

        except KeyError as e:
            self.m_node.critical("wfAWS:downloadPath:error", "No objects with prefix '{prefixMsg}' in bucket {error}".format(error = e, prefixMsg = prefix))
            #logging.error(e)
            return False, fileList, metadataList
        return True, fileList, metadataList