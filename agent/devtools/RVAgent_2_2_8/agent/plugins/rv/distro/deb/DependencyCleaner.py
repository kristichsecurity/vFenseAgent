import re

class DependencyCleaner():

    def strip_dependency(self, dependency):
        """Return the package name only out of dependency string."""

        if re.search(r'\(.*\)', dependency):

            # Strip away the version of the packages but do not
            # return a split list of the packages.
            if '|' in dependency:
                split_deps = dependency.split('|')

                cleaned_deps = []
                for dep in split_deps:
                    cleaned_deps.append(self.strip_dependency(dep))

                return ' | '.join(cleaned_deps)

            #May contain whitespace after splitting up
            return re.split(r'\(.*\)', dependency)[0].strip()
        
        #May contain whitespace
        return dependency.strip()

    def split_and_strip_dependency(self, dependency, strip_version=True):
        """Some dependencies might look like: (libpkg (<= 2.0) | libpkg3).
           This method should return: ['libpkg', 'libpkg3'] or
                                      ['libpkg (<= 2.0)', 'libpkg3'],
           depending on strip_version.
        """

        stripped_pkgs = []
        if '|' in dependency:
            separated_pkgs = dependency.split('|')

            if strip_version:
                for pkg in separated_pkgs:
                    stripped_pkgs.append(
                        self.strip_dependency(pkg)
                    )

            else:
                for pkg in separated_pkgs:
                    stripped_pkgs.append(pkg.strip())

        return stripped_pkgs

    def separate_dependency_string(self, dependencies):
        """Take dependencies as a string, split up the dependencies and
           if split_deps is True then strip version away.

        Example of a dependency string: 'libone, libtwo, libthree (>= 1.2)'
        """

        dep_list = dependencies.split(',')

        # May contain whitespace
        return [dep.strip() for dep in dep_list]

    def clean_app_dependencies(self, apps):
        """Strip away the version from a dependency string.
           Example: libc6 (>= 2.4) -> libc6

           Warning: Mutates the dependencies attribute for all apps
        """

        for app in apps:

            clean_deps = []
            for dep in app.dependencies:
                clean_deps.append(self.strip_dependency(dep))

            app.dependencies = clean_deps

