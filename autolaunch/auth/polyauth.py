from .base import AuthBaseHandlerClass

import json
from base64 import urlsafe_b64decode
from secrets import token_hex

class PolyauthAuthHandlerClass(AuthBaseHandlerClass):
    hint = "polyauth"
    token = None
    refresh_endpoint = None
    refresh_endpoint_params = None

    def __init__(self, auth_token, refresh_info=None, handler=None):
        self.uuid = token_hex(16)
        if refresh_info is None:
            params = json.loads(urlsafe_b64decode(auth_token + '=' * ((4 - len(auth_token)) % 4)))
            self.token = params['token']
            self.refresh_endpoint = None
            self.refresh_endpoint_params = None
            if 'refresh_endpoint' in params:
                self.refresh_endpoint = params['refresh_endpoint']
            if 'refresh_endpoint_params' in params:
                self.refresh_endpoint_params = params['refresh_endpoint_params'] # as dictionary
        else:
            self.token = auth_token
            self.refresh_endpoint = refresh_info['initial_redirect']['endpoint']
            self.refresh_endpoint_params = refresh_info['initial_redirect']['params']

    def getAuthUUID(self):
        return self.uuid

    def getAuthHeaders(self):
        if self.token and len(self.token) > 0:
            return ["X-Auth-Access-Token: " + self.token]
        else:
            return []

    def getRefreshInfo(self):
        if not (self.refresh_endpoint is None or self.refresh_endpoint_params is None):
            return {"initial_redirect": {"method": "POST", "endpoint": self.refresh_endpoint, "params": self.refresh_endpoint_params} }
        else:
            return None

    @staticmethod
    def getHint():
        return PolyauthAuthHandlerClass.hint
