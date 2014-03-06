import datetime

from utils import settings


class Application():

    def __init__(self):

        self.name = ""
        self.version = ""
        self.description = ""
        self.support_url = ""
        self.vendor_severity = ""
        self.file_size = ""
        self.file_data = []
        self.dependencies = []

        self.vendor_id = ""
        self.vendor_name = ""

        self.install_date = ""
        self.release_date = ""

        self.status = ""

        self.repo = ""

        # TODO: Implement on all handlers
        self.reboot_required = "no"
        self.uninstallable = "yes"

        # Properties not applicable to *nix.
        self.kb = ""

    def __repr__(self):
        return "Application(name=%s, version=%s)" % (
            self.name, self.version)

    def __eq__(self, obj):
        """ Compare with other objects by comparing internals. """
        return self.__dict__ == obj.__dict__

    def __ne__(self, obj):
        return not(self.__eq__(obj))

    def __hash__(self):
        """
        Needs to be defined in order to use set logic in sets with
        instances of this class.
        """
        return hash(self.__repr__())

    def to_dict(self):
        """
        Returns a dictionary of the applications' attributes.
        """

        root = {"name": self.name,
                "vendor_name": self.vendor_name,
                "description": self.description,
                "version": self.version,
                "file_data": self.file_data,
                "dependencies": self.dependencies,
                "support_url": self.support_url,
                "vendor_severity": self.vendor_severity,
                "kb": self.kb,
                "repo": self.repo,
                #"vendor_id" : self.vendor_id, TODO: figure out if this guy is needed
                "install_date": self.install_date,
                "release_date": self.release_date,
                "status": self.status,
                "reboot_required": self.reboot_required,
                "uninstallable": self.uninstallable}

        return root


class CreateApplication():

    @staticmethod
    def create(name, version, description, file_data, dependencies,
               support_url, vendor_severity, file_size, vendor_id,
               vendor_name, install_date, release_date,
               installed, repo, reboot_required, uninstallable):

        """ Creates a new Application instance based on the parameters. """
        application = Application()

        application.name = name
        application.version = version
        application.description = description
        application.file_data = file_data
        application.dependencies = dependencies
        application.support_url = support_url
        application.vendor_severity = vendor_severity
        application.file_size = file_size
        application.vendor_id = vendor_id
        application.vendor_name = vendor_name
        application.install_date = \
            CreateApplication._get_date_for_app(install_date)
        application.release_date = \
            CreateApplication._get_date_for_app(release_date)
        application.status = CreateApplication.set_installed(installed)
        application.repo = repo
        application.reboot_required = reboot_required
        application.uninstallable = uninstallable

        return application

    @staticmethod
    def null_application():
        return Application()

    @staticmethod
    def set_installed(installed):
        if installed == 'installed':
            return 'installed'
        elif installed == 'true':
            return 'installed'
        elif installed is True:
            return 'installed'
        else:
            return 'available'

    @staticmethod
    def _get_date_for_app(date_obj):
        """
        Takes a date object, e.g. a string or a datetime object, and returns
        the date in the specified format.
        """

        if date_obj is not None and isinstance(date_obj, datetime.datetime):
            return int(date_obj.date().strftime(settings.DATE_FORMAT))

        elif isinstance(date_obj, float):
            # Assume epoch integer has been given
            return date_obj

        elif isinstance(date_obj, int):
            # Assume epoch integer has been given
            return date_obj

        elif isinstance(date_obj, basestring):

            try:
                date = datetime.datetime.strptime(date_obj, '%Y-%m-%d')

                return int(date.date().strftime(settings.DATE_FORMAT))

            except Exception:
                pass

            try:
                date = datetime.datetime.strptime(date_obj, '%m/%d/%Y')

                return int(date.date().strftime(settings.DATE_FORMAT))

            except Exception:
                pass

            try:
                # epoch string
                date = datetime.datetime.fromtimestamp(float(date_obj))

                return int(date.date().strftime(settings.DATE_FORMAT))

            except Exception:
                pass

        return 0.0
