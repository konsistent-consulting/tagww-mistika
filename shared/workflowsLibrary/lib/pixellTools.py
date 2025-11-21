import requests
import os

class PixellTools:
    def __init__(self, node):
        self.m_node = node

    API_URL1 = "https://api.aipixell.com/"
    API_URL = "https://api-v3.aipixell.com/"
    ##############################################################################################################
    def getUserCredits(self, apiKey):
        url = f"{self.API_URL}api/credits"
        headers = {
            'Authorization': apiKey
        }
        response = requests.get(url, headers=headers)
        return response.json()
    
    def creditCheck(self, apiKey, width, height, frames, model, pixellYn, deinterlaceYn, addGrainYn, slowMotionYn, colorEnhancementYn, bestQuality, advancedSettings):
        url = f"{self.API_URL}api/request/credit/check"
        headers = {
            'Authorization': apiKey
        }
        payload = {
            "width": width,
            "height": height,
            "frames": frames,
            "model": model,
            "pixellYn": int(pixellYn),
            "deinterlaceYn": int(deinterlaceYn),
            "addGrainYn": int(addGrainYn),
            "slowMotionYn": int(slowMotionYn),
            "colorEnhancementYn": int(colorEnhancementYn),
            "bestQuality": int(bestQuality==2 and not advancedSettings)
        }
        
        response = requests.post(url, json=payload, headers=headers)
        return response.json()
    
    def uploadFile(self, apiKey, filePath, contentType):
        url = f"{self.API_URL}api/upload/file/{contentType}"
        headers = {
            'Authorization': apiKey,
            "PMS-UPLOAD-FILE-NAME": (os.path.basename(filePath)),  # Codifica el nombre del archivo
            "PMS-UPLOAD-FILE-SIZE": str(os.path.getsize(filePath))
        }
        #files = {'file': open(filePath, 'rb')}
        with open(filePath, "rb") as files:       
            response = requests.post(url, headers=headers, data=files)
        return response.json()
    
    def getFileStatus(self, apiKey, runId):
        url = f"{self.API_URL}api/request/detail/{runId}"
        headers = {
            'Authorization': apiKey
        }
        response = requests.get(url, headers=headers)
        return response.json()
    
    def getWorkList(self, contentType, apiKey, start_date=None, end_date=None, order="asc", page=1, size=10, status=None):
        url = f"{self.API_URL}api/work/list/{contentType}"       
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "order": order,
            "page": page,
            "size": size
        }        
        if status:
            params["status"] = status
        
        headers = {
            "Authorization": apiKey
        }      
        response = requests.get(url, headers=headers, params=params)
        return response.json()

    def requestTaskProcessing(self, contentType, pixellYn, model, fileId, apiKey, deinterlaceYn, addGrainYn, addGrain, colorEnhancementYn, **kwargs):
        url = f"{self.API_URL}api/request/{contentType}"

        headers = {
            "Authorization": apiKey,
            "Content-Type": "application/json"
        }

        data = {
            "pixellYn": pixellYn,
            "model": model,
            "fileId": fileId,
            "deinterlaceYn": deinterlaceYn,
            "addGrainYn": addGrainYn,
            "addGrain": addGrain,
            "colorEnhancementYn": colorEnhancementYn
        }

        if contentType == "video":
            data.update({
                "slowMotionYn": kwargs.get("slowMotionYn"),
                "slowMotion": kwargs.get("slowMotion"),
                "resizeYn": kwargs.get("resizeYn"),
                "resizeCode": kwargs.get("resizeCode"),
                "targetFrameRate": kwargs.get("targetFrameRate", 'FR001'),
                "aspectRatio": kwargs.get("aspectRatio", 'AR001'),
                "codec": kwargs.get("codec"),
                "container": kwargs.get("container"),
                "audioCodec": kwargs.get("audioCodec"),
                "audioBitRate": kwargs.get("audioBitRate", 'AB001'),
                "quality": kwargs.get("quality"),
                "advancedSettingYn": kwargs.get("advancedSettingYn"),
                "profile": kwargs.get("profile"),
                "bitRateType": kwargs.get("bitRateType"),
                "targetBitRate": kwargs.get("targetBitRate"),
                "maxBitRate": kwargs.get("maxBitRate"),
                "twoPass": kwargs.get("twoPass"),
            })

        response = requests.post(url, headers=headers, json=data)
        return response.json()  
    
    def getDownloadLink(self, apiKey, runId):
        url = f"{self.API_URL}api/done/download?runId={runId}"

        headers = {
            "Authorization": apiKey,
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers)
        return response.json()
    
    def getEncoderOptions(self, apiKey = "DF3567E519442B6A9E811B5BEAB39C5E"):
        url = f"{self.API_URL}api/work/encoder/options"

        headers = {
            "Authorization": apiKey,
            "Content-Type": "application/json"
        }
        # Realizar la solicitud GET
        response = requests.get(url, headers=headers)
        return response.json()
    
    def obtener_nombre_archivo(self,respuesta, url):
    # Intentar obtener el nombre del archivo desde el encabezado Content-Disposition
        if 'Content-Disposition' in respuesta.headers:
            content_disposition = respuesta.headers['Content-Disposition']
            # Buscar el nombre del archivo
            if 'filename=' in content_disposition:
                nombre_archivo = content_disposition.split('filename=')[1].strip('"')
                return nombre_archivo

        return os.path.basename(url)

    def descargar_archivo(self, url, localPath):
        try:
            respuesta = requests.get(url, stream=True)
            if respuesta.status_code == 200:
                nombre_archivo = self.obtener_nombre_archivo(respuesta, url)
                
                # Crear la ruta completa donde se descargará el archivo
                ruta_completa = os.path.join(localPath, nombre_archivo)

                # if os.path.exists(ruta_completa):
                #     print(f"El archivo '{nombre_archivo}' ya existe en el directorio {localPath}. No se sobreescribira.")
                #     return

                # Abrir el archivo en la ruta completa
                with open(ruta_completa, 'wb') as archivo:
                    for chunk in respuesta.iter_content(chunk_size=1024):
                        if chunk:
                            archivo.write(chunk)
                print(f"Archivo descargado como {ruta_completa}")
                return ruta_completa
            else:
                print(f"Error al descargar el archivo. Codigo de estado: {respuesta.status_code}")
        except Exception as e:
            print(f"Ha ocurrido un error: {e}")

    def register_user(self, email, client_secret):
        url = f"{self.API_URL}api/auth/sgo/regist"
        payload = {
            "email": email,
            "clientSecret": client_secret
        }
        HEADERS = {
        'Content-Type': 'application/json'
        }   
        
        response = requests.post(url, json=payload, headers=HEADERS)
        return response.json()

    # 2. Obtener API key de un usuario registrado
    def get_user_api_key(self, email, client_secret):
        url = f"{self.API_URL}api/auth/sgo/key"
        payload = {
            "email": email,
            "clientSecret": client_secret
        }
        HEADERS = {
        'Content-Type': 'application/json'
        }
        
        response = requests.post(url, json=payload, headers=HEADERS)
        return response.json()
    
    def getWorkDoneList(self, contentType, apiKey, start_date=None, end_date=None, order="asc", page=1, size=10):
        url = f"{self.API_URL}api/done/list"       
        params = {
            "startDate": start_date,
            "endDate": end_date,
            "order": order,
            "page": page,
            "size": size
        }
        
        headers = {
            "Authorization": apiKey
        }      
        response = requests.get(url, headers=headers, params=params)
        return response.json()