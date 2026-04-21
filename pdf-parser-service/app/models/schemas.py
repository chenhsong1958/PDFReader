from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime


class ParseResponse(BaseModel):
    doc_id: int
    status: str
    page_count: int
    tables_count: int
    message: Optional[str] = None


class TableData(BaseModel):
    page_num: int
    table_index: int
    headers: List[str]
    rows: List[List[Any]]
    bbox: Optional[List[float]] = None


class ContentResponse(BaseModel):
    id: int
    doc_id: int
    page_num: int
    content_type: str
    content_text: Optional[str] = None
    table_data: Optional[Dict[str, Any]] = None
    confidence: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- 关键字配置 ----

class KeyConfigCreate(BaseModel):
    key_name: str
    aliases: Optional[List[str]] = []
    description: Optional[str] = None

class KeyConfigUpdate(BaseModel):
    key_name: Optional[str] = None
    aliases: Optional[List[str]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None

class KeyConfigResponse(BaseModel):
    id: int
    key_name: str
    aliases: Optional[List[str]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ---- 关键字提取结果 ----

class KeyDataResponse(BaseModel):
    id: int
    doc_id: int
    key_name: str
    key_value: Optional[str] = None
    source: Optional[str] = None
    page_num: Optional[int] = None
    confidence: Optional[int] = None

    class Config:
        from_attributes = True
