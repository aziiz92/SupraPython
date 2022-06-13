import math
from datetime import datetime


def get_int_from_dict(fieldName, sourceDict):
    if fieldName in sourceDict:
        return int(sourceDict[fieldName])
    return None


def get_required_int_from_dict(fieldName, sourceDict):
    if fieldName in sourceDict:
        return int(sourceDict[fieldName])
    raise KeyError("Field " + fieldName + " is missing in dictionary")


def get_item_from_dict(fieldName, sourceDict):
    if fieldName in sourceDict:
        return sourceDict[fieldName]
    return None


def get_required_item_from_dict(fieldName, sourceDict):
    if fieldName in sourceDict:
        return sourceDict[fieldName]
    raise KeyError("Field " + fieldName + " is missing in dictionary")


def get_timestamp_from_dict(fieldName, sourceDict):
    if fieldName in sourceDict:
        return parse_timestamp(sourceDict[fieldName])
    return None


def get_required_timestamp_from_dict(fieldName, sourceDict):
    if fieldName in sourceDict:
        return parse_timestamp(sourceDict[fieldName])
    raise KeyError("Field " + fieldName + " is missing in dictionary")


def parse_timestamp(timestamp):
    if timestamp is not None:
        current_format = '%Y%m%dT%H%M%S'
        return datetime.strptime(timestamp, current_format)
    else:
        return None


def nan_to_none(value):
    if math.isnan(value):
        return None
    else:
        return value
