"""Explicit runtime selection. File mode never imports optional DB dependencies."""
import os
from functools import lru_cache

from models.hierarchy import HierarchyStatus
from services.hierarchy_loader import HierarchyDataError, HierarchyLoader
from services.hierarchy_repository import HierarchyConfigurationError, HierarchyUnavailableError


@lru_cache(maxsize=1)
def get_file_hierarchy_loader():
    try:
        return HierarchyLoader()
    except HierarchyDataError:
        loader = HierarchyLoader.__new__(HierarchyLoader)
        loader.available = False
        loader.status = HierarchyStatus.BOUNDARY_DATA_INVALID
        return loader


def select_hierarchy_reader():
    source = os.getenv("HIERARCHY_DATA_SOURCE", "file")
    if source == "file":
        return get_file_hierarchy_loader()
    if source != "postgis":
        raise HierarchyConfigurationError("HIERARCHY_DATA_SOURCE must be 'file' or 'postgis'.")
    try:
        from db.hierarchy_reader import PostGISHierarchyReader, get_postgis_engine
        engine = get_postgis_engine(os.getenv("DATABASE_URL", ""))
    except (ImportError, ValueError):
        raise HierarchyUnavailableError("PostGIS hierarchy is unavailable.") from None
    return PostGISHierarchyReader(engine)
