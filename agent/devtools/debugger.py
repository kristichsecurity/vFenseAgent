import os
import shutil
import subprocess


dir_name = 'debug_data'


def write_to_file(file_name, output):
    file_path = os.path.join(dir_name, file_name)

    _file = open(file_path, 'w')
    _file.write(output)
    _file.close()


def write_to_updates_file(output):
    write_to_file('update_data', output)


def write_to_installed_file(output):
    write_to_file('installed_data', output)


def list_updates():
    """List packages available for update.

    Calls 'yum list updates' and parses the output.

    Returns:

        - A list containing YumUpdate instances.

    """

    # Tested with yum version 3.2.29
    cmd = ['yum', 'info', 'updates', '-v']

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    output, stderr = process.communicate()

    write_to_updates_file(output)


def get_installed_applications():
    """Gets installed RPM-based applications.

    Returns:

        - A list of Applications.

    """

    # Get the data in a nice, easy, parsable format.
    query_format = "'%{NAME}****%{VERSION}-%{RELEASE}****%{INSTALLTIME}****%{BUILDTIME}****%{SIZE}****%{VENDOR}****%{URL}****%{DESCRIPTION}'"

    all_output = []

    process = subprocess.Popen(
        ['rpm', '-qa'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    output, _stderr = process.communicate()
    installed_list = output.splitlines()

    for app in installed_list:

        rpm_query = \
            ['rpm', '-q', app, '--queryformat', query_format]

        process = subprocess.Popen(
            rpm_query, stdout=subprocess.PIPE
        )

        output, _stderr = process.communicate()
        all_output.append(output)

    output = '\n'.join(all_output)

    write_to_installed_file(output)


def zip_it_up(dir_path, zip_name):
    cmd = ['/usr/bin/zip', '-r', zip_name, dir_path]
    subprocess.call(cmd)


def get_cache_data():
    zip_it_up('/var/cache/yum', 'cache_data')


def get_repo_data():
    zip_it_up('/etc/yum.repos.d', os.path.join(dir_name, 'repo_data'))


if __name__ == '__main__':
    os.mkdir(dir_name)

    list_updates()
    get_installed_applications()
    get_cache_data()
    get_repo_data()

    zip_it_up(dir_name, dir_name)
    shutil.rmtree(dir_name)
