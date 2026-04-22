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


# ---- 关联关系 ----

class RelationCreate(BaseModel):
    source_doc_id: int
    target_doc_id: int
    relation_type: str  # 'main'/'sub'/'related'
    match_key: Optional[str] = None
    match_value: Optional[str] = None


class RelationResponse(BaseModel):
    id: int
    source_doc_id: int
    target_doc_id: int
    relation_type: str
    match_key: Optional[str] = None
    match_value: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RelatedDocumentResponse(BaseModel):
    """关联文档响应，包含文档详情和关系信息"""
    relation_id: int
    relation_type: str
    match_key: Optional[str] = None
    match_value: Optional[str] = None
    doc_id: int
    file_name: str
    status: Optional[str] = None
    page_count: Optional[int] = None

    class Config:
        from_attributes = True


class BatchUploadResponse(BaseModel):
    """批量上传响应"""
    doc_ids: List[int]
    status: str
    message: Optional[str] = None


class MainSubRelationConfig(BaseModel):
    """主/子图纸关系配置（基于关键字）"""
    main_key: str  # 关键字名称
    main_value: str  # 主图纸的关键字值
    sub_key: Optional[str] = None  # 子图纸的关键字名称（默认同main_key）
    sub_value_pattern: Optional[str] = None  # 子图纸值的匹配模式（如 "A-*"）
