from .base import AnalysisBaseHandlerClass
from shutil import copyfile
from io import BytesIO
import os

class PPMSMTHandlerClass(AnalysisBaseHandlerClass):
    nb = "PPMS-CW.ipynb"
    def copyTemplate(self, dest, srcbasedir):
        src = os.path.join(basedir,"PPMS")
        if not os.path.isfile(os.path.join(dest,self.nb)):
            # copy analysis book if not already copied
            copyfile(os.path.join(src,self.nb), os.path.join(dest,self.nb))
            os.chmod(os.path.join(dest,self.nb), 0o644)
        pass

    def getAnalysisFileName(self):
        return self.nb

    def getHint(self):
        return "PPMS-MT"

    def checkIsDataType(self, data, filename=None):
        i = 0
        with BytesIO(data) as f:
            for nv in f:
                i += 1
                if b'PPMS ACMS' in nv:
                    return True
                if i >= 100: # only check first 100 lines
                    return False
        return False

PPMSMTHandler = PPMSMTHandlerClass()

