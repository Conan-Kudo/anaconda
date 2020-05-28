#
# Copyright (C) 2020 Red Hat, Inc.
#
# This copyrighted material is made available to anyone wishing to use,
# modify, copy, or redistribute it subject to the terms and conditions of
# the GNU General Public License v.2, or (at your option) any later version.
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY expressed or implied, including the implied warranties of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.  You should have received a copy of the
# GNU General Public License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.  Any Red Hat trademarks that are incorporated in the
# source code or documentation are not subject to the GNU General Public
# License and may only be used or replicated with the express permission of
# Red Hat, Inc.
#
import os.path

from pyanaconda.anaconda_loggers import get_module_logger
from pyanaconda.core.payload import parse_nfs_url
from pyanaconda.modules.common.errors.payload import SourceSetupError
from pyanaconda.modules.common.task import Task
from pyanaconda.modules.payloads.source.utils import find_and_mount_iso_image
from pyanaconda.payload.errors import PayloadSetupError
from pyanaconda.payload.image import verify_valid_installtree
from pyanaconda.payload.utils import mount, unmount

log = get_module_logger(__name__)

__all__ = ["SetUpNFSSourceTask"]


class SetUpNFSSourceTask(Task):
    """Task to set up the NFS source."""

    def __init__(self, device_mount, iso_mount, url):
        super().__init__()
        self._device_mount = device_mount
        self._iso_mount = iso_mount
        self._url = url

    @property
    def name(self):
        return "Set up NFS installation source"

    def run(self):
        """Set up the installation source."""
        log.debug("Setting up NFS source: %s", self._url)

        for mount_point in [self._device_mount, self._iso_mount]:
            if os.path.ismount(mount_point):
                raise SourceSetupError("The mount point {} is already in use.".format(
                    mount_point
                ))

        try:
            self._mount_nfs()
        except PayloadSetupError:
            raise SourceSetupError("Could not mount NFS url '{}'".format(self._url))

        iso_name = find_and_mount_iso_image(self._device_mount, self._iso_mount)

        if iso_name:
            log.debug("Using the ISO '%s' mounted at '%s'.", iso_name, self._iso_mount)
            return self._iso_mount

        if verify_valid_installtree(self._device_mount):
            log.debug("Using the directory at '%s'.", self._device_mount)
            return self._device_mount

        # nothing found unmount the existing device
        unmount(self._device_mount)
        raise SourceSetupError(
            "Nothing useful found for NFS source at {}".format(self._url))

    def _mount_nfs(self):
        options, host, path = parse_nfs_url(self._url)

        if not options:
            options = "nolock"
        elif "nolock" not in options:
            options += ",nolock"

        mount("{}:{}".format(host, path), self._device_mount, fstype="nfs", options=options)
