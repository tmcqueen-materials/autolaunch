from tornado import web
from base64 import urlsafe_b64decode
from shutil import copyfile
from pathlib import Path
from signal import SIGUSR1
import subprocess
import json
import os

from io import BytesIO

from .analysis import analysis_handlers
from .auth import auth_handlers

from ._compat import get_base_handler
JupyterHandler = get_base_handler()

class AutoLaunchHandler(JupyterHandler):
    analysis_notebooks_src = '/autolaunch/notebooks' # TODO: should be learned by inference, but for now, hard-coded
    """
    The /autolaunch endpoint.
    """
    @web.authenticated
    async def get(self):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        await self._handle_autolaunch()

    async def _handle_autolaunch(self):
        """
        Because /user-redirect/autolaunch is required to be a GET endpoint, there are fairly small limits on the size of
        the parameters passed. Further, most GET parameters are logged to various logging files, meaning that any
        secrets passed to this call may no longer be secrets.

        We deal with the former by allowing for us to be given a "callback" location at which we can send a POST request
        to retrieve the actual parameters to this call. We deal with the latter by calling the secrets containing blob "auth_token"
        (even if it is not actually a token) so that jupyter server masks it in log files.

        Parameters to this call should be either (TODO: OTS not yet implemented):
        ots_callback_url	URL to send a POST request to, to obtain our actual parameters. base64 encoded
	ots_callback_hdrs	(Optional) If provided, headers to send along with the POST request
        *OR*
        auth_token		Auth token data in format expected by chosen auth handler
	auth_token_hint		(Optional) select auth handler. Default: polyauth
	files			List of files/directory structure to present inside notebook, in URLFS index file format
        """
        token_hint = self.get_argument('auth_token_hint', 'polyauth') # default is polyauth. Maybe change to oauth2 at some point?
        if not (token_hint in auth_handlers):
            return self.send_error()

        authhandler = auth_handlers[token_hint](self.get_argument('auth_token', ''))
        token_hdrs = authhandler.getAuthHeaders()
        files_urlfs = self.get_argument('files', '')
        files_urlfs = json.loads(urlsafe_b64decode(files_urlfs + '=' * ((4 - len(files_urlfs)) % 4)))

        basedir = os.path.expanduser(self.settings['server_root_dir'])
        mountdir = os.path.join(basedir,'remote')
        analysis_subpath = 'analysis'
        analysisdir = os.path.join(basedir,analysis_subpath)
        configdir = os.path.join(basedir,'.remote-config')

        # Get files as will appear to us, not as needed by urlfs
        files = []
        for f in files_urlfs:
            if f.split('\t')[0] == 'F':
                files.append(os.path.join(mountdir,f.split('\t')[1][1:])) # [1:] needed to remove first slash in front of all URLFS names

        # Ensure that requisite directories exist
        if not os.path.isdir(analysisdir):
            os.mkdir(analysisdir)
        if not os.path.isdir(configdir):
            os.mkdir(configdir)

        # Find first available new index file
        i = 0
        while os.path.isfile(os.path.join(configdir,"remote."+str(i))):
            i = i + 1
        idxfile = os.path.join(configdir,"remote."+str(i))

        # Add necessary refresh info to file in case we need to refresh this token later
        with open(os.path.join(configdir,'token-refresh.config'),"a") as f:
            f.write(idxfile)
            f.write('\t')
            f.write(authhandler.getAuthUUID())
            f.write('\t')
            f.write(token_hint)
            f.write('\t')
            f.write(json.dumps(authhandler.getRefreshInfo()))
            f.write('\n')

        # Add index file to that known to URLFS
        with open(os.path.join(configdir,'remote.config'),"a") as f:
            f.write(idxfile)
            if len(token_hdrs) > 0:
                for h in token_hdrs:
                    f.write("\t" + h)
            f.write("\n")

        with open(idxfile,"w") as f:
            for fil in files_urlfs:
                f.write(fil + "\n")

        # mount urlfs if not already mounted
        if not os.path.ismount(mountdir):
            # mount
            os.mkdir(mountdir)
            subprocess.run(["/urlfs/src/mount.urlfs", os.path.join(configdir,'remote.config'), mountdir])
        else:
            # reload urlfs (multiple should not be found, but in case user also used it separately from us,
            # reload all instances)
            for pid in map(int,subprocess.check_output(["pidof","mount.urlfs"]).split()):
                os.kill(pid,SIGUSR1)

        analysis_hint = self.get_argument('analysis_hint','')
        if not (analysis_hint in analysis_handlers):
            # Try to figure out which type of analysis notebook we need to copy over
            for fil in files:
                # once we have figured out one, we are done. If working with multiple file types,
                # autolaunch is called multiple times, once for each file type.
                if len(analysis_hint) > 0:
                    break
                # read only first part of file for ID purposes. 64k should be enough for anyone
                pdat = ''
                with open(fil, "rb") as f:
                    pdat = f.read(65536)
                # iterate over analysis handlers to find a suitable one
                for ah in analysis_handlers:
                    if analysis_handlers[ah].checkIsDataType(pdat, fil):
                        analysis_hint = ah
                        break

        if analysis_hint in analysis_handlers:
            analysis_handlers[analysis_hint].copyTemplate(analysisdir, self.analysis_notebooks_src)
            return_url = self.base_url + 'lab/tree/' + analysis_subpath + '/' + analysis_handlers[analysis_hint].getAnalysisFileName()
        else:
            return_url = self.base_url + 'lab/'

        return self.redirect(return_url)

class RefreshAuthHandler(JupyterHandler):
    """
    The /autolaunch/refresh-auth endpoint.

    Reached by a browser with the uuid of the auth token that needs a refresh. Usually spurred by
    javascript in a notebook or similar.

    We then return a page that redirects the user to the specific location to obtain new credentials. Once
    new credentials are obtained, we receive a callback at refresh-auth/callback with the new auth info.

    Note that this only handles cases where user actions is required for login. Obtaining new access tokens
    using an oauth2 refresh token, e.g., does not invoke this handler (but if a refresh_token was expired
    and the ouath2 flow needs to happen from scratch, this would be invoked).

    """
    @web.authenticated
    async def get(self):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        await self._handle_refresh_auth()

    @web.authenticated
    async def post(self):
        await self._handle_refresh_auth()

    async def _handle_refresh_auth(self):
        auth_uuid = self.get_argument('auth_uuid', '')

        # lookup refresh info from auth_uuid (and error if not found)
        basedir = os.path.expanduser(self.settings['server_root_dir'])
        configdir = os.path.join(basedir,'.remote-config')
        redirect_info = None
        with open(os.path.join(configdir, 'token-refresh.config'), "r") as f:
            for l in f:
                if l.split("\t")[1] == auth_uuid:
                    redirect_info = json.loads(l.split("\t")[3])['initial_redirect']
                    break

        if redirect_info is None:
            return self.send_error()

        return_page = "<html><head><script type=\"text/javascript\">function sf() {document.getElementById(\"redir\").submit();}</script></head>"
        return_page += "<body><form id=\"redir\" method=\"" + redirect_info['method'] + "\" action=\"" + redirect_info['endpoint'] + "\">"
        for p in redirect_info['params']:
            return_page += "<input type=\"hidden\" name=\"" + str(p) + "\" value=\"" + str(redirect_info['params'][p]) + "\"/>"
        return_page += "<input type=\"hidden\" name=\"state\" value=\"" + str(auth_uuid) + "\"/>"
        return_page += "<input type=\"hidden\" name=\"redirect_uri\" value=\"" + self.request.protocol + "://" + self.request.host + self.base_url + "autolaunch/refresh-auth/callback" + "\"/>"
        return_page += "<input type=\"submit\" value=\"Click to Continue\"/></form>"
        return_page += "<footer><script type=\"text/javascript\">sf();</script></footer>"
        return_page += "</html>"
        await self.finish(return_page)

class RefreshAuthCallbackHandler(JupyterHandler):
    """
    The /autolaunch/refresh-auth/callback endpoint.

    Reached by callback from earlier refresh-auth request with the new auth info.

    """
    @web.authenticated
    async def get(self):
        self.set_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        await self._handle_refresh_auth_callback()

    @web.authenticated
    async def post(self):
        await self._handle_refresh_auth_callback()

    async def _handle_refresh_auth_callback(self):
        auth_uuid = self.get_argument('state', '')
        auth_token = self.get_argument('code', '')

        # iteratively replace auth info with new info passed here
        basedir = os.path.expanduser(self.settings['server_root_dir'])
        configdir = os.path.join(basedir,'.remote-config')
        idxfiles = {}
        with open(os.path.join(configdir, 'token-refresh.config'), "r") as f:
            with open(os.path.join(configdir, 'token-refresh.config.new'), "w") as fw:
                for l in f:
                    lin = l.split("\t")
                    if lin[1] == auth_uuid:
                        ah = auth_handlers[lin[2]](auth_token,refresh_info=json.loads(lin[3]),handler=self)
                        idxfiles[lin[0]] = ah.getAuthHeaders()
                        fw.write(lin[0])
                        fw.write('\t')
                        fw.write(ah.getAuthUUID())
                        fw.write('\t')
                        fw.write(lin[2])
                        fw.write('\t')
                        fw.write(json.dumps(ah.getRefreshInfo()))
                        fw.write('\n')
                    else:
                        fw.write(l)
        with open(os.path.join(configdir, 'remote.config'), "r") as f:
            with open(os.path.join(configdir, 'remote.config.new'), "w") as fw:
                for l in f:
                    lin = l.split("\t")
                    if lin[0] in idxfiles:
                        fw.write(lin[0])
                        if len(idxfiles[lin[0]]) > 0:
                            for h in idxfiles[lin[0]]:
                                fw.write("\t" + h)
                        fw.write("\n")
                    else:
                        fw.write(l)
        os.replace(os.path.join(configdir, 'remote.config.new'), os.path.join(configdir, 'remote.config'))
        os.replace(os.path.join(configdir, 'token-refresh.config.new'), os.path.join(configdir, 'token-refresh.config'))

        # reload urlfs (multiple should not be found, but in case user also used it separately from us,
        # reload all instances)
        for pid in map(int,subprocess.check_output(["pidof","mount.urlfs"]).split()):
            os.kill(pid,SIGUSR1)

        if len(idxfiles) == 0:
            self.send_error()
        return_page = "<html><head><script type=\"text/javascript\">window.close();</script></head><body>Authentication refreshed. You can close this window.</body></html>"
        await self.finish(return_page)
