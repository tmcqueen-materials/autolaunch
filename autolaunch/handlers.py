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

from ._compat import get_base_handler
JupyterHandler = get_base_handler()

class AutoLaunchHandler(JupyterHandler):
    analysis_notebooks_src = '/autolaunch/notebooks' # TODO: should be learned by inference, but for now, hard-coded
    """
    The /autolaunch endpoint.
    """
    @web.authenticated
    async def get(self):
        await self._handle_autolaunch()

    # TODO: Asymmetrically encrypt auth_token from javascript front-end to prevent token stealing
    # from its presence in the URL (since we must use GET instead of POST in JupyterHub user-redirect).
    async def _handle_autolaunch(self):
        token = self.get_argument('auth_token', '')
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
                files.append(os.path.join(mountdir,f.split('\t')[1][1:]))

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

        with open(os.path.join(configdir,'remote.config'),"a") as f:
            f.write(idxfile)
            if len(token) > 0:
                f.write("\t")
                f.write("X-Auth-Access-Token: " + token)
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
    The /autolaunch-refreshauth endpoint.
    """
    @web.authenticated
    async def get(self):
        await self._handle_refreshauth()

    # TODO: Asymmetrically encrypt auth_token from javascript front-end to prevent token stealing
    # from its presence in the URL (since we must use GET instead of POST in JupyterHub user-redirect).
    async def _handle_refreshauth(self):
        token = self.get_argument('auth_token', '')

        basedir = os.path.expanduser(self.settings['server_root_dir'])
        mountdir = os.path.join(basedir,'remote')
        configdir = os.path.join(basedir,'.remote-config')

#       TODO: update auth tokens in remote.config
#        with open(os.path.join(configdir,'remote.config'),"a") as f:
#            f.write(idxfile)
#            if len(token) > 0:
#                f.write("\t")
#                f.write("X-Auth-Access-Token: " + token)
#            f.write("\n")

        # reload urlfs (multiple should not be found, but in case user also used it separately from us,
        # reload all instances)
        for pid in map(int,subprocess.check_output(["pidof","mount.urlfs"]).split()):
            os.kill(pid,SIGUSR1)

        # TODO: flesh out
        return_url = self.base_url

        return self.redirect(return_url)

