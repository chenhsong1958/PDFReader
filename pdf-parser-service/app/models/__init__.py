from datetime import datetime
from sqlalchemy import Column, BigInteger, Integer, String, Text, DateTime, JSON, Boolean
from app.database import Base


class PdfDocument(Base):
    __tablename__ = "pdf_document"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(BigInteger)
    page_count = Column(Integer)
    upload_time = Column(DateTime, default=datetime.now)
    parse_time = Column(DateTime)
    status = Column(String(50), default="pending")
    error_message = Column(Text)


class PdfContent(Base):
    __tablename__ = "pdf_content"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    doc_id = Column(BigInteger, nullable=False, index=True)
    page_num = Column(Integer)
    content_type = Column(String(50))
    content_text = Column(Text)
    table_data = Column(JSON)
    bbox = Column(JSON)
    confidence = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)


class KeyConfig(Base):
    """关键字配置表 — 用户自定义需要提取的关键字"""
    __tablename__ = "key_config"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    key_name = Column(String(100), nullable=False, unique=True, comment="关键字名称，如：物料编码")
    aliases = Column(JSON, comment="别名列表，如：['物料号','零件编号','Item No']")
    description = Column(String(255), comment="说明")
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class KeyData(Base):
    """提取结果表 — 按关键字分类存储提取值"""
    __tablename__ = "key_data"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    doc_id = Column(BigInteger, nullable=False, index=True)
    key_name = Column(String(100), nullable=False, index=True, comment="对应key_config.key_name")
    key_value = Column(Text, comment="提取到的值")
    source = Column(String(20), comment="text 或 table")
    page_num = Column(Integer, comment="所在页码")
    confidence = Column(Integer, comment="置信度")
    created_at = Column(DateTime, default=datetime.now)


class PdfDocumentRelation(Base):
    """图纸关联关系表"""
    __tablename__ = "pdf_document_relation"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source_doc_id = Column(BigInteger, nullable=False, index=True, comment="源图纸ID")
    target_doc_id = Column(BigInteger, nullable=False, index=True, comment="目标图纸ID")
    relation_type = Column(String(20), nullable=False, comment="关联类型: main/sub/related")
    match_key = Column(String(100), comment="匹配的关键字")
    match_value = Column(String(500), comment="匹配的关键字值")
    created_at = Column(DateTime, default=datetime.now)
