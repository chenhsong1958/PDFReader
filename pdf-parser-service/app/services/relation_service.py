"""
图纸关联检测服务
"""
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import PdfDocument, KeyData, KeyConfig, PdfDocumentRelation


class RelationService:
    """图纸关联关系服务"""

    def detect_relations(self, db: Session, doc_ids: List[int], match_keys: List[str] = None) -> List[Dict]:
        """
        自动检测文档间的关联关系
        基于相同的关键字值建立 'related' 关系

        Args:
            db: 数据库会话
            doc_ids: 待检测的文档ID列表
            match_keys: 指定匹配的关键字列表，None则使用所有启用的key_config

        Returns:
            新建的关联关系列表
        """
        if len(doc_ids) < 2:
            return []

        # 1. 获取匹配关键字范围
        if match_keys is None:
            key_configs = db.query(KeyConfig).filter(KeyConfig.enabled == True).all()
            match_keys = [k.key_name for k in key_configs]

        if not match_keys:
            return []

        # 2. 查询所有文档的关键字值
        key_data_list = db.query(KeyData).filter(
            KeyData.doc_id.in_(doc_ids),
            KeyData.key_name.in_(match_keys)
        ).all()

        # 3. 按 (key_name, key_value) 分组
        value_groups: Dict[Tuple[str, str], List[int]] = {}
        for kd in key_data_list:
            if not kd.key_value:
                continue
            key = (kd.key_name, kd.key_value.strip())
            if key not in value_groups:
                value_groups[key] = []
            if kd.doc_id not in value_groups[key]:
                value_groups[key].append(kd.doc_id)

        # 4. 找出有相同值的文档对，建立关联
        new_relations = []
        for (key_name, key_value), doc_id_list in value_groups.items():
            if len(doc_id_list) < 2:
                continue

            # 两两建立关联
            for i in range(len(doc_id_list)):
                for j in range(i + 1, len(doc_id_list)):
                    source_id = doc_id_list[i]
                    target_id = doc_id_list[j]

                    # 检查是否已存在关联
                    existing = db.query(PdfDocumentRelation).filter(
                        and_(
                            PdfDocumentRelation.source_doc_id == source_id,
                            PdfDocumentRelation.target_doc_id == target_id
                        )
                    ).first()

                    if not existing:
                        relation = PdfDocumentRelation(
                            source_doc_id=source_id,
                            target_doc_id=target_id,
                            relation_type="related",
                            match_key=key_name,
                            match_value=key_value
                        )
                        db.add(relation)
                        new_relations.append({
                            "source_doc_id": source_id,
                            "target_doc_id": target_id,
                            "relation_type": "related",
                            "match_key": key_name,
                            "match_value": key_value
                        })

                    # 同时建立反向关联
                    existing_reverse = db.query(PdfDocumentRelation).filter(
                        and_(
                            PdfDocumentRelation.source_doc_id == target_id,
                            PdfDocumentRelation.target_doc_id == source_id
                        )
                    ).first()

                    if not existing_reverse:
                        relation = PdfDocumentRelation(
                            source_doc_id=target_id,
                            target_doc_id=source_id,
                            relation_type="related",
                            match_key=key_name,
                            match_value=key_value
                        )
                        db.add(relation)

        db.commit()
        return new_relations

    def set_main_sub_relations(
        self,
        db: Session,
        main_doc_id: int,
        sub_doc_ids: List[int]
    ) -> List[Dict]:
        """
        设置主图纸与子图纸的关系

        Args:
            db: 数据库会话
            main_doc_id: 主图纸ID
            sub_doc_ids: 子图纸ID列表

        Returns:
            新建的关系列表
        """
        new_relations = []

        # 更新主图纸
        main_doc = db.query(PdfDocument).filter(PdfDocument.id == main_doc_id).first()
        if main_doc:
            main_doc.is_main = 1

        # 更新子图纸并建立关系
        for sub_id in sub_doc_ids:
            sub_doc = db.query(PdfDocument).filter(PdfDocument.id == sub_id).first()
            if sub_doc:
                sub_doc.parent_doc_id = main_doc_id

            # 检查是否已存在关系
            existing = db.query(PdfDocumentRelation).filter(
                and_(
                    PdfDocumentRelation.source_doc_id == main_doc_id,
                    PdfDocumentRelation.target_doc_id == sub_id
                )
            ).first()

            if not existing:
                relation = PdfDocumentRelation(
                    source_doc_id=main_doc_id,
                    target_doc_id=sub_id,
                    relation_type="sub"
                )
                db.add(relation)
                new_relations.append({
                    "source_doc_id": main_doc_id,
                    "target_doc_id": sub_id,
                    "relation_type": "sub"
                })

            # 反向关系
            existing_reverse = db.query(PdfDocumentRelation).filter(
                and_(
                    PdfDocumentRelation.source_doc_id == sub_id,
                    PdfDocumentRelation.target_doc_id == main_doc_id
                )
            ).first()

            if not existing_reverse:
                relation = PdfDocumentRelation(
                    source_doc_id=sub_id,
                    target_doc_id=main_doc_id,
                    relation_type="main"
                )
                db.add(relation)

        db.commit()
        return new_relations

    def get_document_relations(self, db: Session, doc_id: int) -> List[PdfDocumentRelation]:
        """获取文档的所有关联关系"""
        return db.query(PdfDocumentRelation).filter(
            PdfDocumentRelation.source_doc_id == doc_id
        ).all()

    def get_related_documents(self, db: Session, doc_id: int) -> List[Dict]:
        """获取关联文档列表（含文档详情）"""
        relations = db.query(PdfDocumentRelation).filter(
            PdfDocumentRelation.source_doc_id == doc_id
        ).all()

        result = []
        for rel in relations:
            target_doc = db.query(PdfDocument).filter(
                PdfDocument.id == rel.target_doc_id
            ).first()

            if target_doc:
                result.append({
                    "relation_id": rel.id,
                    "relation_type": rel.relation_type,
                    "match_key": rel.match_key,
                    "match_value": rel.match_value,
                    "doc_id": target_doc.id,
                    "file_name": target_doc.file_name,
                    "status": target_doc.status,
                    "page_count": target_doc.page_count
                })

        return result

    def create_relation(
        self,
        db: Session,
        source_doc_id: int,
        target_doc_id: int,
        relation_type: str,
        match_key: str = None,
        match_value: str = None
    ) -> PdfDocumentRelation:
        """手动创建关联关系"""
        # 检查是否已存在
        existing = db.query(PdfDocumentRelation).filter(
            and_(
                PdfDocumentRelation.source_doc_id == source_doc_id,
                PdfDocumentRelation.target_doc_id == target_doc_id
            )
        ).first()

        if existing:
            return existing

        relation = PdfDocumentRelation(
            source_doc_id=source_doc_id,
            target_doc_id=target_doc_id,
            relation_type=relation_type,
            match_key=match_key,
            match_value=match_value
        )
        db.add(relation)
        db.commit()
        db.refresh(relation)
        return relation

    def delete_relation(self, db: Session, relation_id: int) -> bool:
        """删除关联关系"""
        relation = db.query(PdfDocumentRelation).filter(
            PdfDocumentRelation.id == relation_id
        ).first()

        if relation:
            db.delete(relation)
            db.commit()
            return True
        return False

    def detect_main_sub_by_keywords(
        self,
        db: Session,
        doc_ids: List[int],
        main_key: str,
        main_value: str,
        sub_key: str = None,
        sub_value_pattern: str = None
    ) -> List[Dict]:
        """
        基于关键字值自动检测主/子图纸关系

        Args:
            db: 数据库会话
            doc_ids: 待检测的文档ID列表
            main_key: 主图纸的关键字名称
            main_value: 主图纸的关键字值
            sub_key: 子图纸的关键字名称（默认同main_key）
            sub_value_pattern: 子图纸值的匹配模式（如 "A-*" 表示以A-开头）

        Returns:
            新建的关系列表
        """
        if len(doc_ids) < 2:
            return []

        sub_key = sub_key or main_key

        # 查询所有文档的关键字值
        key_data_list = db.query(KeyData).filter(
            KeyData.doc_id.in_(doc_ids),
            KeyData.key_name.in_([main_key, sub_key])
        ).all()

        # 分类文档
        main_docs = []
        sub_docs = []

        for kd in key_data_list:
            if kd.key_name == main_key and kd.key_value and kd.key_value.strip() == main_value:
                if kd.doc_id not in main_docs:
                    main_docs.append(kd.doc_id)
            elif kd.key_name == sub_key and kd.key_value:
                val = kd.key_value.strip()
                # 检查是否匹配子图纸模式
                if sub_value_pattern:
                    if self._match_pattern(val, sub_value_pattern):
                        if kd.doc_id not in sub_docs:
                            sub_docs.append(kd.doc_id)
                elif sub_value_pattern is None and val != main_value:
                    # 如果没有指定模式，则所有不等于主值的都视为子图纸
                    if kd.doc_id not in sub_docs:
                        sub_docs.append(kd.doc_id)

        new_relations = []

        # 为每个主图纸建立与所有子图纸的关系
        for main_id in main_docs:
            for sub_id in sub_docs:
                if main_id == sub_id:
                    continue

                # 检查是否已存在关系
                existing = db.query(PdfDocumentRelation).filter(
                    and_(
                        PdfDocumentRelation.source_doc_id == main_id,
                        PdfDocumentRelation.target_doc_id == sub_id
                    )
                ).first()

                if not existing:
                    # 主 -> 子
                    relation = PdfDocumentRelation(
                        source_doc_id=main_id,
                        target_doc_id=sub_id,
                        relation_type="sub",
                        match_key=main_key,
                        match_value=main_value
                    )
                    db.add(relation)
                    new_relations.append({
                        "source_doc_id": main_id,
                        "target_doc_id": sub_id,
                        "relation_type": "sub",
                        "match_key": main_key,
                        "match_value": main_value
                    })

                # 子 -> 主（反向）
                existing_reverse = db.query(PdfDocumentRelation).filter(
                    and_(
                        PdfDocumentRelation.source_doc_id == sub_id,
                        PdfDocumentRelation.target_doc_id == main_id
                    )
                ).first()

                if not existing_reverse:
                    relation = PdfDocumentRelation(
                        source_doc_id=sub_id,
                        target_doc_id=main_id,
                        relation_type="main",
                        match_key=main_key,
                        match_value=main_value
                    )
                    db.add(relation)

        # 更新文档的 is_main 和 parent_doc_id 字段
        for main_id in main_docs:
            main_doc = db.query(PdfDocument).filter(PdfDocument.id == main_id).first()
            if main_doc:
                main_doc.is_main = 1

        for sub_id in sub_docs:
            sub_doc = db.query(PdfDocument).filter(PdfDocument.id == sub_id).first()
            if sub_doc and main_docs:
                sub_doc.parent_doc_id = main_docs[0]

        db.commit()
        return new_relations

    @staticmethod
    def _match_pattern(value: str, pattern: str) -> bool:
        """简单的模式匹配（支持 * 通配符）"""
        import fnmatch
        return fnmatch.fnmatch(value, pattern)

    def auto_detect_all(self, db: Session) -> List[Dict]:
        """对所有文档执行自动关联检测"""
        all_docs = db.query(PdfDocument).filter(
            PdfDocument.status == "completed"
        ).all()

        doc_ids = [d.id for d in all_docs]
        return self.detect_relations(db, doc_ids)


relation_service = RelationService()
