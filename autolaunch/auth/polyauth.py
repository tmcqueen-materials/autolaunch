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
        try:
            self._params_setter(auth_token)
        except:
            # legacy call with no refresh handling
            self.token = auth_token

    def getAuthUUID(self):
        return self.uuid

    def getAuthHeaders(self):
        return ["X-Auth-Access-Token: " + self.token]

    def getRefreshInfo(self):
        if not (self.refresh_endpoint is None or self.refresh_endpoint_params is None):
            return {"initial_redirect": {"method": "POST", "endpoint": self.refresh_endpoint, "params": self.refresh_endpoint_params} }
        else:
            return None

    def _params_setter(self, auth_token):
        params = json.loads(urlsafe_b64decode(auth_token + '=' * ((4 - len(auth_token)) % 4)))
        self.token = params['token']
        self.refresh_endpoint = None
        self.refresh_endpoint_params = None
        if 'refresh_endpoint' in params:
            self.refresh_endpoint = params['refresh_endpoint']
        if 'refresh_endpoint_params' in params:
            self.refresh_endpoint_params = params['refresh_endpoint_params'] # as dictionary

    @staticmethod
    def getHint():
        return PolyauthAuthHandlerClass.hint
