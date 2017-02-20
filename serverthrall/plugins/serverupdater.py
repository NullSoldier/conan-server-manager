from .thrallplugin import ThrallPlugin
from serverthrall import settings
from serverthrall import acf
import subprocess
import os


class ServerUpdater(ThrallPlugin):

    NO_INSTALLED_VERSION = ''

    def __init__(self, config):
        super(ServerUpdater, self).__init__(config)
        self.config.set_default('installed_version', self.NO_INSTALLED_VERSION)

    def ready(self, steamcmd, server, thrall):
        super(ServerUpdater, self).ready(steamcmd, server, thrall)
        self.installed_version = self.config.get('installed_version')

        if self.installed_version == self.NO_INSTALLED_VERSION:
            self.detect_existing_version()

        self.logger.info('Autoupdater running, currently known buildid is %s', self.installed_version)

    def detect_existing_version(self):
        buildid = self.get_installed_build_id()

        self.installed_version = buildid
        self.config.set('installed_version', buildid)

        if buildid != self.NO_INSTALLED_VERSION:
            self.logger.info('Conan server already installed with buildid %s' % buildid)

    def get_installed_build_id(self):
        appmanifest_path = os.path.join(
            self.thrall.config.get('conan_server_directory'),
            'steamapps/appmanifest_%s.acf' % settings.CONAN_APP_ID)

        if not os.path.exists(appmanifest_path):
            return self.NO_INSTALLED_VERSION

        with open(appmanifest_path, 'rb') as f:
            data = acf.load(f)

        return data['AppState']['buildid']

    def get_available_build_id(self):
        app_info = None
        try:
            app_info = self.steamcmd.get_app_info(settings.CONAN_APP_ID)
        except subprocess.CalledProcessError as ex:
            return None, ex

        build_id = (app_info
            [settings.CONAN_APP_ID]
            ['depots']
            ['branches']
            [settings.RELEASE_BRANCH]
            ['buildid'])

        return build_id, None

    def is_update_available(self):
        available_build_id, exc = self.get_available_build_id()

        if available_build_id is None:
            self.logger.error('Failed to check for update: %s' % exc)
            return False, None, None

        if self.installed_version == self.NO_INSTALLED_VERSION:
            return True, None, available_build_id

        current = int(self.installed_version)
        latest = int(available_build_id)
        return latest > current, current, latest

    def update_server(self, target_build_id):
        self.server.install_or_update()
        self.installed_version = target_build_id
        self.config.set('installed_version', target_build_id)

    def tick(self):
        is_available, current, target = self.is_update_available()

        if is_available:
            self.logger.info('An update is available from build %s to %s' % (current, target))
            self.server.close()
            self.update_server(target)
            self.server.start()