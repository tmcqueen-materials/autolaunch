"""Abstract base class for analysis handlers
"""
from abc import ABC, abstractmethod

class AuthBaseHandlerClass(ABC):
    @abstractmethod
    def __init__(self, auth_token, refresh_info=None, handler=None):
        pass
    @abstractmethod
    def getAuthUUID(self):
        pass
    @abstractmethod
    def getAuthHeaders(self):
        pass
    @abstractmethod
    def getRefreshInfo(self):
        pass
    @staticmethod
    @abstractmethod
    def getHint():
        pass

