import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PdfDocument, PdfContent, KeyConfig, KeyData
from app.models.schemas import (
    ParseResponse, ContentResponse,
    KeyConfigCreate, KeyConfigUpdate, KeyConfigResponse,
    KeyDataResponse,
    RelationCreate, RelationResponse, RelatedDocumentResponse, BatchUploadResponse,
    MainSubRelationConfig
)
from app.services.pdf_parser import parser_service
from app.services.relation_service import relation_service

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

        # 解析完成后，与现有文档进行关联检测
        try:
            all_completed_docs = db.query(PdfDocument).filter(
                PdfDocument.status == "completed",
                PdfDocument.id != doc_id
            ).all()

            if all_completed_docs:
                existing_ids = [d.id for d in all_completed_docs]
                relation_service.detect_relations(db, [doc_id] + existing_ids)
        except Exception as rel_e:
            # 关联检测失败不影响主流程
            print(f"关联检测失败: {str(rel_e)}")

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


# ==================== 批量上传 ====================

@router.post("/upload/batch", response_model=BatchUploadResponse)
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    relations: str = Form(default=None),
    db: Session = Depends(get_db)
):
    """
    批量上传PDF文件，支持指定基于关键字的主/子图纸关系

    relations: JSON字符串，格式:
    {
        "main_key": "图号",
        "main_value": "A-100",
        "sub_key": "图号",
        "sub_value_pattern": "A-100-*"
    }
    """
    import json

    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)

    doc_ids = []
    relation_info = None

    if relations:
        try:
            relation_info = MainSubRelationConfig.model_validate(json.loads(relations))
        except (json.JSONDecodeError, ValueError):
            relation_info = None

    # 逐个处理文件
    for file in files:
        if not file.filename.lower().endswith('.pdf'):
            continue

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
        doc_ids.append(doc.id)

        from app.config import settings
        background_tasks.add_task(
            process_pdf_task,
            file_path,
            doc.id,
            settings.DATABASE_URL
        )

    # 解析完成后自动按关键字设置主/子关系并检测其他关联
    if relation_info and doc_ids:
        background_tasks.add_task(
            _set_relations_after_parse,
            relation_info.model_dump(),
            doc_ids
        )

    return BatchUploadResponse(
        doc_ids=doc_ids,
        status="pending",
        message=f"已上传 {len(doc_ids)} 个文件，正在后台解析"
    )


def _set_relations_after_parse(relation_info: dict, all_doc_ids: List[int]):
    """解析完成后按关键字设置主/子关系并执行自动关联检测"""
    import time
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    max_wait = 300  # 5分钟
    check_interval = 5
    waited = 0

    while waited < max_wait:
        db = SessionLocal()
        try:
            docs = db.query(PdfDocument).filter(PdfDocument.id.in_(all_doc_ids)).all()
            all_completed = all(d.status in ["completed", "failed"] for d in docs)

            if all_completed:
                # 按关键字检测主/子关系
                if relation_info:
                    completed_ids = [d.id for d in docs if d.status == "completed"]
                    if len(completed_ids) >= 2:
                        relation_service.detect_main_sub_by_keywords(
                            db,
                            completed_ids,
                            main_key=relation_info.get("main_key"),
                            main_value=relation_info.get("main_value"),
                            sub_key=relation_info.get("sub_key"),
                            sub_value_pattern=relation_info.get("sub_value_pattern")
                        )

                # 自动检测其他关联（基于相同关键字值）
                completed_ids = [d.id for d in docs if d.status == "completed"]
                if len(completed_ids) >= 2:
                    relation_service.detect_relations(db, completed_ids)
                break
        finally:
            db.close()

        time.sleep(check_interval)
        waited += check_interval


# ==================== 关联关系管理 ====================

@router.get("/documents/{doc_id}/relations", response_model=List[RelationResponse])
async def get_document_relations(doc_id: int, db: Session = Depends(get_db)):
    """获取文档的所有关联关系"""
    doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    relations = relation_service.get_document_relations(db, doc_id)
    return [RelationResponse(
        id=r.id,
        source_doc_id=r.source_doc_id,
        target_doc_id=r.target_doc_id,
        relation_type=r.relation_type,
        match_key=r.match_key,
        match_value=r.match_value,
        created_at=r.created_at
    ) for r in relations]


@router.get("/documents/{doc_id}/related", response_model=List[RelatedDocumentResponse])
async def get_related_documents(doc_id: int, db: Session = Depends(get_db)):
    """获取关联文档列表（含文档详情）"""
    doc = db.query(PdfDocument).filter(PdfDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return relation_service.get_related_documents(db, doc_id)


@router.post("/relations", response_model=RelationResponse)
async def create_relation(relation: RelationCreate, db: Session = Depends(get_db)):
    """手动创建关联关系"""
    # 验证文档存在
    source = db.query(PdfDocument).filter(PdfDocument.id == relation.source_doc_id).first()
    target = db.query(PdfDocument).filter(PdfDocument.id == relation.target_doc_id).first()

    if not source or not target:
        raise HTTPException(status_code=404, detail="文档不存在")

    new_relation = relation_service.create_relation(
        db,
        relation.source_doc_id,
        relation.target_doc_id,
        relation.relation_type,
        relation.match_key,
        relation.match_value
    )

    return RelationResponse(
        id=new_relation.id,
        source_doc_id=new_relation.source_doc_id,
        target_doc_id=new_relation.target_doc_id,
        relation_type=new_relation.relation_type,
        match_key=new_relation.match_key,
        match_value=new_relation.match_value,
        created_at=new_relation.created_at
    )


@router.delete("/relations/{relation_id}")
async def delete_relation(relation_id: int, db: Session = Depends(get_db)):
    """删除关联关系"""
    success = relation_service.delete_relation(db, relation_id)
    if not success:
        raise HTTPException(status_code=404, detail="关联关系不存在")
    return {"message": "删除成功"}


@router.post("/relations/auto-detect")
async def auto_detect_relations(db: Session = Depends(get_db)):
    """对所有文档执行自动关联检测"""
    new_relations = relation_service.auto_detect_all(db)
    return {
        "message": "自动检测完成",
        "new_relations_count": len(new_relations),
        "new_relations": new_relations
    }
