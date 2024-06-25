"""
This imports all known autolaunch auth handlers. At some point, it should be
rewritten to automatically discover all handlers installed here, so that
adding a handler is as easy as adding a file. But for now, it is a small
enough number, we do it manually.
"""
from .polyauth import PolyauthAuthHandlerClass

auth_handlers = {PolyauthAuthHandlerClass.getHint(): PolyauthAuthHandlerClass,
                }

