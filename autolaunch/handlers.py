from tornado import web
from base64 import urlsafe_b64decode
from shutil import copyfile

import subprocess

import json
import os
from signal import SIGUSR1

from ._compat import get_base_handler

from pathlib import Path

JupyterHandler = get_base_handler()

class AutoLaunchHandler(JupyterHandler):
    analysis_notebooks_src = '/autolaunch/notebooks'
    analysis_notebooks = {
        "Default": "",
        "PPMS-CW": "PPMS-CW.ipynb",
        "MPMS-CW": "MPMS-CW.ipynb",
        "XRD-Plot": "",
    }
    """
    The /autolaunch endpoint.
    """
    @web.authenticated
    async def get(self):
        await self._handle_autolaunch()

    # TODO: Asymmetrically encrypt auth_token from javascript front-end to prevent token stealing
    # from its presence in the URL.
    async def _handle_autolaunch(self):
        token = self.get_argument('auth_token', '')
        files = self.get_argument('files', '')
        files = json.loads(urlsafe_b64decode(files + '=' * ((4 - len(files)) % 4)))

        basedir = os.path.expanduser(self.settings['server_root_dir'])
        mountdir = os.path.join(basedir,'remote')
        analysis_subpath = 'analysis'
        analysisdir = os.path.join(basedir,analysis_subpath)
        configdir = os.path.join(basedir,'.remote-config')

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
            for fil in files:
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
        if not (analysis_hint in self.analysis_notebooks):
            analysis_hint = 'Default'
            # Try to figure out which type of analysis notebook we need to copy over
            if len(list(Path(mountdir).glob("*.raw"))) > 0:
                analysis_hint = "XRD-Plot"
            elif len(list(Path(mountdir).glob("*.dat"))) > 0:
                fil = list(Path(mountdir).glob("*.dat"))[0]
                with open(fil, "rb") as f:
                    for nv in f:
                        if b'MPMS3' in nv:
                            analysis_hint = 'MPMS-CW'
                            break
                        elif b'PPMS ACMS' in nv:
                            analysis_hint = 'PPMS-CW'
                            break

        nb = self.analysis_notebooks[analysis_hint]
        if len(nb) > 0:
            if not os.path.isfile(os.path.join(analysisdir,nb)):
                # copy analysis book if not already copied
                copyfile(os.path.join(self.analysis_notebooks_src,nb), os.path.join(analysisdir,nb))
                os.chmod(os.path.join(analysisdir,nb), 0o644)
            return_url = self.base_url + 'lab/tree/' + analysis_subpath + '/' + nb
        else:
            return_url = self.base_url + 'lab/'

        return self.redirect(return_url)
