import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PdfDocument, PdfContent, KeyConfig, KeyData
from app.models.schemas import (
    ParseResponse, ContentResponse,
    KeyConfigCreate, KeyConfigUpdate, KeyConfigResponse,
    KeyDataResponse
)
from app.services.pdf_parser import parser_service

router = APIRouter(prefix="/api/v1", tags=["pdf"])


# ==================== PDF处理 ====================

def process_pdf_task(file_path: str, doc_id: int, db_url: str):
    """后台任务：处理PDF文件"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
        if not doc:
            return

        doc.status = "processing"
        db.commit()

        # 逐页判定类型
        page_types = parser_service.classify_pages(file_path)

        # 加载用户定义的关键字配置
        key_configs_db = db.query(KeyConfig).filter(KeyConfig.enabled == True).all()
        key_configs = [{"key_name": k.key_name, "aliases": k.aliases or []} for k in key_configs_db]

        # 解析PDF（传入用户关键字）
        result = parser_service.parse_pdf(file_path, page_types=page_types, key_configs=key_configs if key_configs else None)

        # 保存文本内容
        for content in result["contents"]:
            pdf_content = PdfContent(
                doc_id=doc_id,
                page_num=content["page_num"],
                content_type=content["content_type"],
                content_text=content["content_text"],
                confidence=content.get("confidence", 100)
            )
            db.add(pdf_content)

        # 保存表格数据
        for table in result["tables"]:
            pdf_content = PdfContent(
                doc_id=doc_id,
                page_num=table["page_num"],
                content_type="table",
                table_data={
                    "headers": table["headers"],
                    "rows": table["rows"],
                    "table_index": table["table_index"]
                },
                bbox=list(table["bbox"]) if table.get("bbox") else None
            )
            db.add(pdf_content)

        # 保存关键信息到 key_data 表
        for kv in result.get("key_values", []):
            key_data = KeyData(
                doc_id=doc_id,
                key_name=kv["key"],
                key_value=kv.get("value", ""),
                source=kv.get("source", ""),
                page_num=kv.get("page"),
                confidence=kv.get("confidence")
            )
            db.add(key_data)

        # 更新文档状态
        doc.status = "completed"
        doc.page_count = result["page_count"]
        doc.parse_time = __import__('datetime').datetime.now()
        db.commit()

    except Exception as e:
        doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
        if doc:
            doc.status = "failed"
            doc.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=ParseResponse)
async def upload_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")

    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    doc = PdfDocument(
        file_name=file.filename,
        file_path=file_path,
        file_size=file_size,
        status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    from app.config import settings
    background_tasks.add_task(
        process_pdf_task,
        file_path,
        doc.id,
        settings.DATABASE_URL
    )

    return ParseResponse(
        doc_id=doc.id,
        status="pending",
        page_count=0,
        tables_count=0,
        message="文件已上传，正在后台解析"
    )


@router.get("/status/{doc_id}", response_model=ParseResponse)
async def get_parse_status(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    tables_count = db.query(PdfContent).filter(
        PdfContent.doc_id == doc_id,
        PdfContent.content_type == "table"
    ).count()

    return ParseResponse(
        doc_id=doc.id,
        status=doc.status,
        page_count=doc.page_count or 0,
        tables_count=tables_count,
        message=doc.error_message
    )


@router.get("/content/{doc_id}", response_model=List[ContentResponse])
async def get_content(
    doc_id: int,
    content_type: str = None,
    page: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(PdfContent).filter(PdfContent.doc_id == doc_id)

    if content_type:
        query = query.filter(PdfContent.content_type == content_type)
    if page:
        query = query.filter(PdfContent.page_num == page)

    contents = query.all()
    return [ContentResponse(
        id=c.id,
        doc_id=c.doc_id,
        page_num=c.page_num,
        content_type=c.content_type,
        content_text=c.content_text,
        table_data=c.table_data,
        confidence=c.confidence,
        created_at=c.created_at
    ) for c in contents]


@router.get("/key-values/{doc_id}")
async def get_key_values(doc_id: int, db: Session = Depends(get_db)):
    """获取文档的关键信息提取结果（从key_data表）"""
    doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    rows = db.query(KeyData).filter(KeyData.doc_id == doc_id).all()

    # 按key_name分组
    grouped = {}
    for r in rows:
        grouped.setdefault(r.key_name, []).append({
            "value": r.key_value,
            "source": r.source,
            "page": r.page_num,
            "confidence": r.confidence
        })

    return {
        "doc_id": doc_id,
        "file_name": doc.file_name,
        "key_values": grouped
    }


@router.delete("/document/{doc_id}")
async def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    db.query(KeyData).filter(KeyData.doc_id == doc_id).delete()
    db.query(PdfContent).filter(PdfContent.doc_id == doc_id).delete()
    db.delete(doc)
    db.commit()

    return {"message": "删除成功"}


@router.post("/reparse/{doc_id}")
async def reparse_document(doc_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """重新解析已有文档"""
    doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 清除旧数据
    db.query(KeyData).filter(KeyData.doc_id == doc_id).delete()
    db.query(PdfContent).filter(PdfContent.doc_id == doc_id).delete()
    doc.status = "pending"
    db.commit()

    from app.config import settings
    background_tasks.add_task(
        process_pdf_task,
        doc.file_path,
        doc.id,
        settings.DATABASE_URL
    )
    return {"message": "正在重新解析", "doc_id": doc_id}


# ==================== 关键字配置管理 ====================

@router.get("/keys", response_model=List[KeyConfigResponse])
async def list_keys(db: Session = Depends(get_db)):
    """获取所有关键字配置"""
    return db.query(KeyConfig).order_by(KeyConfig.id).all()


@router.post("/keys", response_model=KeyConfigResponse)
async def create_key(config: KeyConfigCreate, db: Session = Depends(get_db)):
    """新增关键字"""
    existing = db.query(KeyConfig).filter(KeyConfig.key_name == config.key_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"关键字 '{config.key_name}' 已存在")

    key_config = KeyConfig(
        key_name=config.key_name,
        aliases=config.aliases,
        description=config.description
    )
    db.add(key_config)
    db.commit()
    db.refresh(key_config)
    return key_config


@router.put("/keys/{key_id}", response_model=KeyConfigResponse)
async def update_key(key_id: int, config: KeyConfigUpdate, db: Session = Depends(get_db)):
    """更新关键字"""
    key_config = db.query(KeyConfig).filter(KeyConfig.id == key_id).first()
    if not key_config:
        raise HTTPException(status_code=404, detail="关键字不存在")

    if config.key_name is not None:
        key_config.key_name = config.key_name
    if config.aliases is not None:
        key_config.aliases = config.aliases
    if config.description is not None:
        key_config.description = config.description
    if config.enabled is not None:
        key_config.enabled = config.enabled

    db.commit()
    db.refresh(key_config)
    return key_config


@router.delete("/keys/{key_id}")
async def delete_key(key_id: int, db: Session = Depends(get_db)):
    """删除关键字"""
    key_config = db.query(KeyConfig).filter(KeyConfig.id == key_id).first()
    if not key_config:
        raise HTTPException(status_code=404, detail="关键字不存在")

    db.delete(key_config)
    db.commit()
    return {"message": "删除成功"}
