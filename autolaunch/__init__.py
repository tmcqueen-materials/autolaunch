"""
    A full autolaunch implementation that allows one-click Jupyter servers to automatically pull in data and analysis notebook(s)
    to analyze data. Handles fusion of multiple disparate data sources with separate authentications as required, by leveraging
    URLFS as the file backend.

    TODO:
    1. Due to (re)writing of files on disk on the server, these endpoints are currently *not thread-safe*, and *will fail
       catastrophically* if multiple endpoints are handling requests in parallel. In current usage, this is not a problem,
       but this should be rectified at some point.
    2. Right now, the number of files added in a single call is limited by the maximum length of a GET request (typically ~8 kB).
       Adding the OTS ("one-time storage") callback can remove this limitation.
    3. Right now, the only auth provider supported is polyauth (as used on data.paradim.org). An oauth2 implementation should
       be added, to enable accessing most data from most places (since most places support oauth2).
    4. Right now, secrets are stored local to the jupyter server, but otherwise unprotected. They should be stored in a
       device-bound session as that becomes more widely supported.
    5. There are a couple of configuration parameters (notebook source directory, names of key files) that should be
       stored in extension settings and adjustable in the usual way for a jupyter extension.
    6. Right now the glue logic for refreshing authentication tokens is handled within notebooks. This extension should
       proactively watch for IO errors on URLFS and automatically kick off authentication refreshes when needed.

"""

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
        RefreshAuthHandler,
        RefreshAuthCallbackHandler,
    )

    web_app = app.web_app
    handlers = [
        (url_path_join(web_app.settings['base_url'], 'autolaunch'), AutoLaunchHandler),
        (url_path_join(web_app.settings['base_url'], 'autolaunch', 'refresh-auth'), RefreshAuthHandler),
        (url_path_join(web_app.settings['base_url'], 'autolaunch', 'refresh-auth', 'callback'), RefreshAuthCallbackHandler),
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

