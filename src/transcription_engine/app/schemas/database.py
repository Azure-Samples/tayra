"""
This module contains the schema definitions for the database management of this application.
"""

from typing import Optional
from .models import ManagerItem


class ManagerModel(ManagerItem):
    _rid: Optional[str] = None
    _self: Optional[str] = None
    _etag: Optional[str] = None
    _attachments: Optional[str] = None
    _ts: Optional[str] = None


database_schema = {
    "Manager Table": ManagerModel.model_json_schema()
}
