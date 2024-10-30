"""
A package that holds response schemas and models.
"""

__all__ = [
    "BodyMessage",
    "RESPONSES",
    "SubCriteria",
    "Criteria",
    "ManagerInterface",
    "SpecialistInterface"
]
__author__ = "LATAM AI GBB TEAM"


from .endpoints import (
    ManagerInterface,
    SpecialistInterface,
    SubCriteria,
    Criteria,
)
from .responses import RESPONSES, BodyMessage
