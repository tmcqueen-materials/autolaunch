"""
This imports all known data analysis handlers. At some point, it should be
rewritten to automatically discover all handlers installed here, so that
adding a handler is as easy as adding a file. But for now, it is a small
enough number, we do it manually.
"""
from .MPMS import MPMSMTHandler
from .PPMS import PPMSMTHandler

analysis_handlers = {MPMSMTHandler.getHint(): MPMSMTHandler,
                     PPMSMTHandler.getHint(): PPMSMTHandler,
                   }
