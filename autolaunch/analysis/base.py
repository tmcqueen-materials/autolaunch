"""Abstract base class for analysis handlers
"""
from abc import ABC, abstractmethod

class AnalysisBaseHandlerClass(ABC):
    @abstractmethod
    def copyTemplate(self, dest, srcbasedir):
        pass

    @abstractmethod
    def getAnalysisFileName(self):
        pass

    @abstractmethod
    def getHint(self):
        pass

    @abstractmethod
    def checkIsDataType(self, data, filename=None):
        pass

