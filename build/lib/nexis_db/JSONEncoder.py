import collections
import json
from datetime import datetime


def get_public_members(obj):
    """
    Retrieves a list of member-like objects (members or properties) that are
    publically exposed.

    :param obj: The object to probe.
    :return:    A list of strings.
    """
    # Get public members
    members = set(filter(lambda member: not member.startswith("_"),
                         obj.__dict__))
    # Also fetch properties
    type_dict = type(obj).__dict__
    members |= set(
        filter(lambda member: isinstance(type_dict[member], property)
               and not member.startswith("_"), type_dict))

    return members


class JSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if hasattr(obj, "__json__"):
            return obj.__json__()
        elif isinstance(obj, collections.Iterable):
            return list(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__getitem__") and hasattr(obj, "keys"):
            return dict(obj)
        elif hasattr(obj, "__dict__"):
            return {member: getattr(obj, member)
                    for member in get_public_members(obj)}

        return json.JSONEncoder.default(self, obj)
