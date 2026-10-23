"""
Database Type Helpers for SQLite and PostgreSQL compatibility
"""
import uuid
from typing import Any, List, Optional
from sqlalchemy import JSON, String
from sqlalchemy.types import TypeDecorator
from pgvector.sqlalchemy import Vector


class VectorColumn(TypeDecorator):
    """
    Platform-independent Vector column:
    - Uses pgvector Vector(dim) on PostgreSQL
    - Uses JSON array on SQLite / fallback dialects
    """
    impl = JSON
    cache_ok = True

    def __init__(self, dim: int = 384, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dim = dim

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Vector(self.dim))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Optional[List[float]], dialect) -> Any:
        if value is None:
            return None
        return [float(x) for x in value]

    def process_result_value(self, value: Any, dialect) -> Optional[List[float]]:
        if value is None:
            return None
        if isinstance(value, list):
            return [float(x) for x in value]
        # In case driver returns numpy array or vector wrapper
        try:
            return [float(x) for x in value]
        except Exception:
            return value
