from .base import BaseStrategy
from .dbcache import DBCache
from .favicon import FaviconStrategy
from .github import HeuristicStrategy
from .iconlib import IconLib
from .registry import RegistryStrategy

__all__ = [
    "BaseStrategy",
    "DBCache",
    "FaviconStrategy",
    "HeuristicStrategy",
    "IconLib",
    "RegistryStrategy",
]
