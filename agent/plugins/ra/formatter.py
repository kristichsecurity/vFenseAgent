import json

from utils import settings
from serveroperation.sofoperation import OperationKey
from ra.raoperation import RaKey


def _base_json_object(operation):
    root = {}
    root[OperationKey.Operation] = operation.type
    root[OperationKey.OperationId] = operation.id
    root[OperationKey.AgentId] = settings.AgentId
    root[OperationKey.Plugin] = operation.plugin

    if operation.error:
        root[OperationKey.Error] = operation.error

    return root


def rd_results(operation):
    root = _base_json_object(operation)

    data = {}

    data[RaKey.HostPort] = operation.host_port
    data[RaKey.Success] = operation.success

    root['data'] = data

    return json.dumps(root)


def rd_stop_results(operation):
    root = _base_json_object(operation)

    data = {}
    data[RaKey.Success] = operation.success

    root['data'] = data

    return json.dumps(root)
