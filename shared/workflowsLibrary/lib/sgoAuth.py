import time
from oauth2client import _helpers
from oauth2client import client
import webbrowser
import socket
from six.moves import BaseHTTPServer
from six.moves import http_client
from six.moves import urllib
import select  # Importar select para manejar tiempos de espera
import json
import ssl

class ClientRedirectServer(BaseHTTPServer.HTTPServer):
    query_params = {}

class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(http_client.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        parts = urllib.parse.urlparse(self.path)
        query = _helpers.parse_unique_urlencoded(parts.query)
        self.server.query_params = query
        self.wfile.write(
            b'<html><head><title>Authentication Status</title></head>')
        self.wfile.write(
            b'<body><h1>The authentication flow is completed.</h1>')
        self.wfile.write(
            b'<p>Go back to Mistika Workflows</p>')
        self.wfile.write(b'</body></html>')

    def log_message(self, format, *args):
        """This is a log message"""

class sgoAuth:
    def __init__(self, node):
        self.m_node = node

    SOCKET_TIMEOUT = 10  # Tiempo de espera del socket para manejar solicitudes HTTP

    def checkIfCredentialsExist(self, clientId, channelSlot=""):
        return (clientId + str(channelSlot)) in self.credentials_dict

    def get_authenticated_service(self, timeOut = 60):    
        flow = client.OAuth2WebServerFlow("nKB6rh6UJg76YMIHZF2MDWrx9uC9OGG8", auth_uri="https://sgo.eu.auth0.com/authorize", scope="openid profile email offline_access", redirect_uri='urn:ietf:wg:oauth:2.0:oob')
        self.m_node.info("googleAuth:info", "Opening browser to visit authentication site")

        code = self.run_flow(flow, self.m_node, timeOut)
        return code

    def updateCredentials(self, _credentialsDict, clientId):
        credential_data = _credentialsDict.get(clientId)
        if credential_data is not None:
            if hasattr(credential_data, 'to_json') and callable(getattr(credential_data, 'to_json')):
                credentialsDict = "{\"" + clientId + "\" : " + credential_data.to_json() + "}"
            else:
                credentialsDict = "{\"" + clientId + "\" : " + json.dumps(credential_data) + "}"
        else:
            credentialsDict = "{}"
        return credentialsDict

    def run_flow(self, flow, node, timeOut, http=None):
        success = False
        port_number = 0
        for port in [8080, 8090]:
            port_number = port
            try:
                httpd = ClientRedirectServer(("localhost", port), ClientRedirectHandler)
                httpd.timeout = self.SOCKET_TIMEOUT  # Tiempo máximo para manejar una solicitud HTTP
            except socket.error:
                pass
            else:
                success = True
                break

        if not success:
            node.info("error", "Failed to start a local webserver")
            return None

        oauth_callback = 'http://{host}:{port}/'.format(host="localhost", port=port_number)
        flow.redirect_uri = oauth_callback

        params = {
            "client_id": flow.client_id,
            "redirect_uri": oauth_callback,
            "response_type": "code",
            "scope": flow.scope
        }
        authorize_url = f"{flow.auth_uri}?{urllib.parse.urlencode(params)}"
        ssl._create_default_https_context = ssl._create_stdlib_context
        webbrowser.open(authorize_url, new=1, autoraise=True)

        timeOutTimer = 0
        code = None

        while timeOutTimer < timeOut:
            #print(timeOutTimer, timeOut)
            # Usar select para esperar a que el socket tenga actividad
            ready_to_read, _, _ = select.select([httpd.fileno()], [], [], self.SOCKET_TIMEOUT)

            if ready_to_read:
                httpd.handle_request()  # Maneja una solicitud si está lista

                if 'error' in httpd.query_params:
                    node.critical("googleAuth:error", 'Authentication request was rejected.')
                    break
                if 'code' in httpd.query_params:
                    code = httpd.query_params['code']
                    break
            else:
                node.info("googleAuth:info", 'No authentication response received, waiting...')

            timeOutTimer += self.SOCKET_TIMEOUT

        if code is None:
            node.critical("googleAuth:error", 'Failed to find "code" in the query parameters of the redirect or timed out.')

        return code
