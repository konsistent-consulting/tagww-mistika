import threading
import os
import dropbox

class dbxToolsProgressPercentage:
    def __init__(self, node, size):
        self.m_size = size
        self.m_current = 0
        self.m_node = node
        node.setComplexity(self.m_size if self.m_size>0 else 100)
        self.m_lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self.m_lock:
            self.m_current += bytes_amount
            percentage = round((self.m_current / float(self.m_size)) * 100)if self.m_size>0 else 100
            self.m_node.progressUpdated(percentage)
            
class dbxTools:
    def __init__(self, node):
        self.m_node = node
        self.m_accesToken = None
        self.m_dbx = None

    def connect(self, accessToken):
        self.m_accesToken = accessToken
        try:
            self.m_dbx = dropbox.Dropbox(self.m_accesToken)
            #self.m_dbx = dropbox.DropboxTeam(self.m_accesToken).as_user("alvar.de.diego.lopez@gmail.com")
            dropbox
            
        except dropbox.exceptions.AuthError as e:
            self.m_node.critical("wfDropbox:connect:error", "Invalid access token")
            return False
        except Exception as e:
            self.m_node.critical("wfDropbox:connect:exception", "Connection error{}".format(e))
            return False
        return True
    
    def uploadFile(self, file_path, target_path, chunk_size=4 * 1024 * 1024,):
        f = open(file_path, "rb")
        file_size = os.path.getsize(file_path)
        progress = dbxToolsProgressPercentage(self.m_node, file_size)
        
        try:
            if file_size <= chunk_size:
                self.m_dbx.files_upload(f.read(), target_path)
                progress(file_size)
            else:                
                upload_session_start_result = self.m_dbx.files_upload_session_start(
                    f.read(chunk_size)
                )
                progress(chunk_size)
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=upload_session_start_result.session_id,
                    offset=f.tell(),
                )
                commit = dropbox.files.CommitInfo(path=target_path)
                while f.tell() < file_size:
                    if (file_size - f.tell()) <= chunk_size:
                        self.m_dbx.files_upload_session_finish(
                            f.read(chunk_size), cursor, commit
                        )
                    else:
                        self.m_dbx.files_upload_session_append(
                            f.read(chunk_size),
                            cursor.session_id,
                            cursor.offset,
                        )
                        cursor.offset = f.tell()
                    progress(chunk_size)
        except dropbox.exceptions.BadInputError as e:
            self.m_node.critical("wfDropbox:upload:tokenScope", "{}".format(e))
            return False
        except Exception as e:
            self.m_node.critical("wfDropbox:upload:exception", "{}".format(e))
            return False
        return True

    def downloadFile(self, target_path, file_path):   
        try:    
            self.m_dbx.files_download_to_file(target_path, file_path)
        except Exception as e:
            self.m_node.critical("wfDropbox:downloadFile:error", "{}".format(e))
            return False
        return True  
    
    def downloadPath(self, dropboxPath, localPath, deleteAfterDownload):
        fileList, res, size = [], True, 100  
        
        progress = dbxToolsProgressPercentage(self.m_node, size)
        try:
            if dropboxPath == "" or isinstance(self.m_dbx.files_get_metadata(dropboxPath), dropbox.files.FolderMetadata):
                list = self.m_dbx.files_list_folder(dropboxPath, recursive= True)
                cont = 0               
                for dropboxFile in list.entries:
                    if isinstance(dropboxFile, dropbox.files.FileMetadata):                         
                        res = self.processFileAndMakeDirs(localPath, dropboxPath, dropboxFile.path_display, fileList, deleteAfterDownload)
                        progress(size/(len(list.entries)-cont)) 
                    else:
                        cont += 1
            else:
                res = self.processFileAndMakeDirs(localPath, dropboxPath, dropboxPath, fileList, deleteAfterDownload)  
                progress(size)                                           
                        
        except Exception as e:                           
            if "not_found" in str(e):
                self.m_node.critical("wfDropbox:downloadPath:notFound", "'{}' is not a File or a Directory".format(dropboxPath))
                return False, fileList
            else:
                self.m_node.critical("wfDropbox:downloadPath:error", "{}".format(e))               
                return False, fileList
        return res, fileList
    
    def processFileAndMakeDirs(self, localPath, dropboxPath, file, fileList, deleteAfterDownload):         
        localFullPath = localPath + "/" + file
        dirLocalPath = os.path.dirname(localFullPath)

        if not os.path.exists(dirLocalPath):
            os.makedirs(dirLocalPath)
        
        res = self.downloadFile(localFullPath, file)
            
        fileList.append(localFullPath)
        
        if dropboxPath.endswith("/"):
            dropboxPath = dropboxPath[:-1]
            
        if deleteAfterDownload:
            self.m_dbx.files_delete(file)
        return res     
