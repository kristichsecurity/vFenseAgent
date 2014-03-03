from os import path
from subprocess import Popen, PIPE

_client_crt_file = 'client.crt'
_client_key_file = 'client.key'
_server_crt_file = 'server.crt'

_client_certs_dir = '/opt/TopPatch/agent/certs/'

ClientCert = _client_certs_dir + _client_crt_file
ServerCert = _client_certs_dir + _server_crt_file
ClientKey = _client_certs_dir + _client_key_file


def generate_csr():

    openssl_command = "openssl req -nodes -days 1000 "\
                      "-subj '/CN=TopPatch Client/O=TopPatch/OU=Remediation " \
                      "Vault/C=US/ST=NY/L=NYC' "\
                      "-newkey rsa:2048 -keyout %s" % ClientKey

    process = Popen(openssl_command, stdout=PIPE, stderr=PIPE, shell=True)
    return process.stdout.read()


def save_certificate(crt_pem):
    f = open(ClientCert, 'w')
    f.write(crt_pem)
    f.close()


def does_certificate_exist(file_path):

    if path.exists(file_path):
        return True

    return False
