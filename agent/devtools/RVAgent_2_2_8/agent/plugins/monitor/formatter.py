import json

from utils import settings
from serveroperation.sofoperation import OperationKey
from monitor.monitoperation import MonitKey


def _base_json_object(operation):
    root = {}
    root[OperationKey.Operation] = operation.type
    root[OperationKey.OperationId] = operation.id
    root[OperationKey.AgentId] = settings.AgentId
    root[OperationKey.Plugin] = operation.plugin

    return root


def monitor_data(operation):
    root = _base_json_object(operation)

    data = {}

    data[MonitKey.Memory] = operation.memory
    data[MonitKey.Cpu] = operation.cpu
    data[MonitKey.FileSystem] = operation.file_system

    root['data'] = data

    return json.dumps(root)
