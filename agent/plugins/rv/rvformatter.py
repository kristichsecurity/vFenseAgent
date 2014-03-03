import json

from utils import settings
from serveroperation.sofoperation import OperationKey


def _base_json_object(operation):
    root = {}
    root[OperationKey.Operation] = operation.type
    root[OperationKey.OperationId] = operation.id
    root[OperationKey.AgentId] = settings.AgentId
    root[OperationKey.Plugin] = operation.plugin

    return root


def applications(operation):
    root = _base_json_object(operation)
    temp_updates = []

    if operation.applications:

        for app in operation.applications:
            temp = {}

            temp["name"] = app.name
            temp["vendor_id"] = app.vendor_id
            temp['version'] = app.version
            temp["description"] = app.description
            temp["file_data"] = app.file_data
            temp["file_size"] = app.file_size
            temp["support_url"] = app.support_url
            temp["vendor_severity"] = app.vendor_severity
            temp["kb"] = app.kb
            temp["repo"] = app.repo
            temp["install_date"] = app.install_date
            temp["release_date"] = app.release_date
            temp["installed"] = app.installed
            temp["vendor_name"] = app.vendor_name

            temp_updates.append(temp)

    root[OperationKey.Data] = temp_updates

    return json.dumps(root)


def operation_results(operation):

    root = _base_json_object(operation)

    root["data"] = operation.data

    if operation.error != '':
        root["error"] = operation.error

    return json.dumps(root)
