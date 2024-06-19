from jupyter_server.utils import url_path_join
from tornado.web import StaticFileHandler
import os


def _jupyter_server_extension_points():
    return [{
        'module': 'autolaunch',
    }]


def _load_jupyter_server_extension(app):
    """
    Note that as this function is used as a hook for both notebook and
    jupyter_server, the argument passed may be a NotebookApp or a ServerApp.
    """
    # identify base handler by app class
    from ._compat import get_base_handler

    get_base_handler(app)

    # need base class before importing handler
    from .handlers import (
        AutoLaunchHandler,
    )

    web_app = app.web_app
    handlers = [
        (url_path_join(web_app.settings['base_url'], 'autolaunch'), AutoLaunchHandler),
    ]
    # FIXME: See note on how to stop relying on settings to pass information:
    #        https://github.com/jupyterhub/nbgitpuller/pull/242#pullrequestreview-854968180
    #
    web_app.settings['nbapp'] = app
    web_app.add_handlers('.*', handlers)


# For compatibility with both notebook and jupyter_server, we define
# _jupyter_server_extension_paths alongside _jupyter_server_extension_points.
#
# "..._paths" is used by notebook and still supported by jupyter_server as of
# jupyter_server 1.13.3, but was renamed to "..._points" in jupyter_server
# 1.0.0.
#
_jupyter_server_extension_paths = _jupyter_server_extension_points

# For compatibility with both notebook and jupyter_server, we define both
# load_jupyter_server_extension alongside _load_jupyter_server_extension.
#
# "load..." is used by notebook and "_load..." is used by jupyter_server.
#
load_jupyter_server_extension = _load_jupyter_server_extension

