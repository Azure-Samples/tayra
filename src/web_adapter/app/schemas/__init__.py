"""
A package that holds response schemas and models.
"""

__all__ = [
    "BodyMessage",
    "RESPONSES",
    "UploadJobParams"
]
__author__ = "LATAM AI GBB TEAM"


from .endpoints import UploadJobParams
from .responses import RESPONSES, BodyMessage
