from tornado import web
from base64 import urlsafe_b64decode
from shutil import copyfile

import subprocess

import json
import os

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
        notebook = self.get_argument('notebook','lab')

        basedir = os.path.expanduser(self.settings['server_root_dir'])
        mountdir = os.path.join(basedir,'remote')
        analysis_subpath = 'analysis'
        analysisdir = os.path.join(basedir,analysis_subpath)

        with open(os.path.join(basedir,'token.config'),"w") as f:
            f.write(os.path.join(basedir,'token.index'))
            f.write("\n")
            if len(token) > 0:
                f.write("X-Auth-Access-Token: " + token + "\n")
        with open(os.path.join(basedir,"token.index"),"w") as f:
            for fil in files:
                f.write(fil + "\n")
        os.mkdir(mountdir)
        subprocess.run(["/urlfs/src/mount.urlfs", os.path.join(basedir,'token.config'), mountdir])

        analysis_hint = self.get_argument('analysis_hint','')
        if not (analysis_hint in self.analysis_notebooks):
            analysis_hint = 'Default'
            # Try to figure out which type of analysis notebook we need to copy over
            if len(list(Path(mountdir).glob("*.raw"))) > 0:
                analysis_hint = "XRD-Plot"
            elif len(list(Path(mountdir).glob("*.dat"))) > 0:
                fil = list(Path(mountdir).glob("*.dat"))[0]
                with open(fil, "r") as f:
                    for nv in f:
                        if 'MPMS3' in nv:
                            analysis_hint = 'MPMS-CW'
                            break
                        elif 'PPMS ACMS' in nv:
                            analysis_hint = 'PPMS-CW'
                            break

        nb = self.analysis_notebooks[analysis_hint]
        os.mkdir(analysisdir)
        if len(nb) > 0:
            copyfile(os.path.join(self.analysis_notebooks_src,nb), os.path.join(analysisdir,nb))
            os.chmod(os.path.join(analysisdir,nb), 0o444)
            return_url = self.base_url + 'lab/tree/' + analysis_subpath + '/' + nb
        else:
            return_url = self.base_url + 'lab/'

        if self.get_argument("get_return_url", False):
            self.write({'return_url': return_url})
            await self.flush()
        else:
            return self.redirect(return_url)
