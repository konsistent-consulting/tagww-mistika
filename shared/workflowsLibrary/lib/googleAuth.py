import threading
import time
import Mistika
from apiclient.discovery import build
from oauth2client import _helpers
from oauth2client import client
import webbrowser
import socket
from oauth2client.client import AccessTokenCredentials
from six.moves import BaseHTTPServer
from six.moves import http_client
from six.moves import urllib
import warnings
import json

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
            b'<body><h1>The authentication flow has completed.</h1>')
        self.wfile.write(
            b'<p>Go back to Mistika Workflows</p>')
        self.wfile.write(b'</body></html>')

    def log_message(self, format, *args):
        """This is a log message"""

class GoogleAuth:
    def __init__(self, node, scope, apiServiceName, apiVersion, credentialsDict):
        self.m_node = node
        self.UPLOAD_SCOPE = scope
        self.API_SERVICE_NAME = apiServiceName
        self.API_VERSION = apiVersion
        self.credentials_dict = credentialsDict

    TIMER_INTERVALS = 2

    def checkIfCredentialsExist(self, clientId, channelSlot=""):
        return (clientId + str(channelSlot)) in self.credentials_dict

    def get_authenticated_service(self, clientId, clientSecret, timeOut, channelSlot=""):
        credentials_key = clientId + str(channelSlot)
        credentials = self.credentials_dict.get(credentials_key)
        if credentials is not None:
            #credentials = AccessTokenCredentials(credentials.get("access_token"), 'user-agent-value')
            credentials = client.GoogleCredentials(None, clientId, clientSecret,credentials.get("refresh_token"),None,"https://accounts.google.com/o/oauth2/token",'sms-proxy')

        if credentials is None or credentials.invalid:
            flow = client.OAuth2WebServerFlow(clientId, clientSecret, self.UPLOAD_SCOPE, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
            self.m_node.info("googleAuth:info", "Opening browser to visit authentication site")

            returnList = [True]
            authThread = threading.Thread(target=self.thread_run_flow, args=(flow, credentials_key, returnList, self.m_node))
            authThread.start()

            timeOutTimer = 0
            while returnList[0] == True:
                timeOutTimer += self.TIMER_INTERVALS
                time.sleep(self.TIMER_INTERVALS)
                if timeOutTimer >= timeOut:
                    return "TimeOut"
                if returnList[0] is None:
                    return None

            credentials = returnList[0]
        try:
            return build(self.API_SERVICE_NAME, self.API_VERSION, credentials=credentials)
        except PermissionError as e:
            self.m_node.critical("googleAuth:info", "Error: {}".format(e))

    def thread_run_flow(self, flow, credentials_key, returnList, node):
        try:
            returnList[0] = self.run_flow(flow, credentials_key, node)
        except SystemExit:
            returnList[0] = None

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

    def run_flow(self, flow, credentials_key, node, http=None):
        success = False
        port_number = 0
        for port in [8080, 8090]:
            port_number = port
            try:
                httpd = ClientRedirectServer(("localhost", port), ClientRedirectHandler)
            except socket.error:
                pass
            else:
                success = True
                break

        if not success:
            node.info("error", "Failed to start a local webserver")

        oauth_callback = 'http://{host}:{port}/'.format(host="localhost", port=port_number)
        flow.redirect_uri = oauth_callback
        authorize_url = flow.step1_get_authorize_url()

        webbrowser.open(authorize_url, new=1, autoraise=True)
        code = None
        httpd.handle_request()
        if 'error' in httpd.query_params:
            return node.critical("googleAuth:error", 'Authentication request was rejected.')
        if 'code' in httpd.query_params:
            code = httpd.query_params['code']
        else:
            return node.critical("googleAuth:error", 'Failed to find "code" in the query parameters of the redirect.')

        try:
            credential = flow.step2_exchange(code, http=http)
        except client.FlowExchangeError as e:
            return node.critical("googleAuth:error", 'Authentication has failed: {0}'.format(e))

        self.credentials_dict[credentials_key] = credential
        self.m_node._credentialsDict = self.credentials_dict
        return credential
