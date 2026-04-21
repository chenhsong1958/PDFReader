import os
import re
import json
import threading
import cv2
import numpy as np
import pdfplumber
import fitz  # PyMuPDF
from typing import List, Dict, Any, Optional, Tuple


class PdfParserService:
    """PDF解析服务，支持文本提取、表格提取、OCR识别和关键信息提取"""

    def __init__(self, upload_dir: str = "./uploads"):
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        self._ocr_engine = None
        self._ocr_lock = threading.Lock()

    @property
    def ocr_engine(self):
        if self._ocr_engine is None:
            with self._ocr_lock:
                if self._ocr_engine is None:
                    os.environ['FLAGS_use_mkldnn'] = '0'
                    from paddleocr import PaddleOCR
                    from app.config import settings
                    self._ocr_engine = PaddleOCR(
                        use_angle_cls=True,
                        lang=settings.OCR_LANG,
                        show_log=False,
                    )
        return self._ocr_engine

    def classify_pages(self, file_path: str) -> Dict[int, str]:
        """逐页判定类型: 'text' 或 'image'"""
        from app.config import settings
        threshold = settings.OCR_TEXT_THRESHOLD
        page_types = {}
        try:
            doc = fitz.open(file_path)
            for page_num_0, page in enumerate(doc):
                text = page.get_text().strip()
                page_types[page_num_0 + 1] = "text" if len(text) > threshold else "image"
            doc.close()
        except Exception as e:
            raise Exception(f"页面分类失败: {str(e)}")
        return page_types

    def ocr_page(self, page) -> Tuple[str, float, List[Dict]]:
        """对PyMuPDF页面对象运行PaddleOCR，返回 (文本, 置信度0-100, 结构化OCR行数据)"""
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)

        img_bytes = pix.tobytes("png")
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        result = self.ocr_engine.ocr(img, cls=True)

        if not result or not result[0]:
            return "", 0.0, []

        texts = []
        confidences = []
        ocr_lines = []  # 结构化数据: [{text, confidence, bbox}]
        for line in result[0]:
            text = line[1][0]
            conf = line[1][1]
            bbox = line[0]  # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
            texts.append(text)
            confidences.append(conf)
            ocr_lines.append({
                "text": text,
                "confidence": conf,
                "bbox": bbox
            })

        combined_text = "\n".join(texts)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return combined_text, round(avg_confidence * 100), ocr_lines

    def parse_pdf(self, file_path: str, page_types: Dict[int, str] = None, key_configs: List[Dict] = None) -> Dict[str, Any]:
        """解析PDF文件，提取文本、表格和关键信息
        key_configs: [{"key_name": "物料编码", "aliases": ["物料号", "零件编号"]}, ...]
        """
        result = {
            "file_path": file_path,
            "page_count": 0,
            "contents": [],
            "tables": [],
            "key_values": [],
            "metadata": {}
        }

        try:
            doc = fitz.open(file_path)
            result["page_count"] = len(doc)
            result["metadata"] = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
            }

            if page_types is None:
                page_types = {i + 1: "text" for i in range(len(doc))}

            pdf = pdfplumber.open(file_path)
            try:
                # 收集所有页的OCR行数据用于空间分析
                all_ocr_lines = {}
                for page_num, page in enumerate(pdf.pages, 1):
                    page_type = page_types.get(page_num, "text")
                    if page_type == "image":
                        fitz_page = doc[page_num - 1]
                        self._process_image_page(fitz_page, page_num, result, all_ocr_lines)
                    else:
                        self._process_text_page(page, page_num, result)
            finally:
                pdf.close()
            doc.close()

            # 提取关键信息（使用用户配置或默认关键字）
            result["key_values"] = self.extract_key_values(
                result["contents"], result["tables"], key_configs, all_ocr_lines
            )

            return result

        except Exception as e:
            raise Exception(f"PDF解析失败: {str(e)}")

    def _process_text_page(self, page, page_num: int, result: Dict):
        """pdfplumber处理文本页"""
        text = page.extract_text()
        if text:
            result["contents"].append({
                "page_num": page_num,
                "content_type": "text",
                "content_text": text,
                "bbox": None,
                "confidence": 100
            })

        tables = page.extract_tables()
        for table_idx, table in enumerate(tables):
            if table and len(table) > 0:
                cleaned_table = self._clean_table(table)
                result["tables"].append({
                    "page_num": page_num,
                    "table_index": table_idx,
                    "headers": cleaned_table[0] if cleaned_table else [],
                    "rows": cleaned_table[1:] if len(cleaned_table) > 1 else [],
                    "bbox": page.find_tables()[table_idx].bbox if table_idx < len(page.find_tables()) else None
                })

    def _process_image_page(self, fitz_page, page_num: int, result: Dict, all_ocr_lines: Dict = None):
        """PaddleOCR处理图片页"""
        from app.config import settings

        if not settings.OCR_ENABLED:
            result["contents"].append({
                "page_num": page_num,
                "content_type": "text",
                "content_text": "[OCR未启用，无法提取图片页面内容]",
                "bbox": None,
                "confidence": 0
            })
            return

        text, confidence, ocr_lines = self.ocr_page(fitz_page)

        # 保存OCR行数据用于空间分析
        if all_ocr_lines is not None and ocr_lines:
            all_ocr_lines[page_num] = ocr_lines

        if text:
            result["contents"].append({
                "page_num": page_num,
                "content_type": "text",
                "content_text": text,
                "bbox": None,
                "confidence": confidence
            })

        # 尝试从OCR结果中检测表格结构
        if ocr_lines:
            tables = self._detect_tables_from_ocr(ocr_lines, page_num)
            result["tables"].extend(tables)

    def _detect_tables_from_ocr(self, ocr_lines: List[Dict], page_num: int) -> List[Dict]:
        """从OCR行数据中检测可能的表格结构（基于位置对齐）"""
        if len(ocr_lines) < 3:
            return []

        # 按Y坐标分组（同一行的文本Y坐标相近）
        y_tolerance = 15  # 像素容差
        line_groups = []
        current_group = [ocr_lines[0]]

        for i in range(1, len(ocr_lines)):
            curr_y = (ocr_lines[i]["bbox"][0][1] + ocr_lines[i]["bbox"][2][1]) / 2
            prev_y = (current_group[-1]["bbox"][0][1] + current_group[-1]["bbox"][2][1]) / 2

            if abs(curr_y - prev_y) < y_tolerance:
                current_group.append(ocr_lines[i])
            else:
                if len(current_group) >= 2:  # 至少2列才算表格行
                    line_groups.append(sorted(current_group, key=lambda x: x["bbox"][0][0]))
                current_group = [ocr_lines[i]]

        if len(current_group) >= 2:
            line_groups.append(sorted(current_group, key=lambda x: x["bbox"][0][0]))

        # 需要至少2行才能构成表格
        if len(line_groups) < 2:
            return []

        # 取列数最多的行作为参考列数
        col_count = max(len(g) for g in line_groups)

        # 只保留列数一致的行（或接近一致）
        consistent_groups = [g for g in line_groups if len(g) >= 2]

        if len(consistent_groups) < 2:
            return []

        # 构建表格
        headers = [g["text"].strip() for g in consistent_groups[0]]
        rows = []
        for group in consistent_groups[1:]:
            row = [g["text"].strip() for g in group]
            rows.append(row)

        return [{
            "page_num": page_num,
            "table_index": 0,
            "headers": headers,
            "rows": rows,
            "bbox": None
        }]

    # ---------- 关键信息提取 ----------

    DEFAULT_KEY_PATTERNS = [
        "物料编码", "物料号", "物料名称", "零件号", "零件名称",
        "图号", "图纸编号", "图样编号",
        "版本", "版次", "修订号",
        "材料", "材质", "材料牌号",
        "规格", "规格型号",
        "数量", "重量", "单重", "总重",
        "工艺", "表面处理", "检验标准",
        "项目名称", "项目编号", "合同编号",
        "客户", "供应商", "制造商",
        "备注", "说明", "技术要求",
    ]

    def _build_key_matcher(self, key_configs: List[Dict] = None) -> Dict[str, str]:
        """
        构建关键字匹配映射
        返回 {所有可能的匹配词: 标准key_name}
        """
        mapping = {}
        if key_configs:
            for cfg in key_configs:
                key_name = cfg.get("key_name", "")
                if not key_name:
                    continue
                mapping[key_name] = key_name
                for alias in (cfg.get("aliases") or []):
                    if alias:
                        mapping[alias] = key_name
        else:
            for k in self.DEFAULT_KEY_PATTERNS:
                mapping[k] = k
        return mapping

    def extract_key_values(self, contents: List[Dict], tables: List[Dict],
                          key_configs: List[Dict] = None,
                          all_ocr_lines: Dict = None) -> List[Dict]:
        """
        从文本内容、表格和OCR空间数据中提取关键信息键值对。
        返回 [{"key": "物料编码", "value": "X2FS-99000001", "source": "table|text|ocr_spatial", "page": 1, "confidence": 100}, ...]
        """
        key_values = []
        key_map = self._build_key_matcher(key_configs)
        match_words = list(key_map.keys())

        if not match_words:
            return []

        # 1. 从文本内容中提取（正则匹配）
        all_text_by_page = {}
        for c in contents:
            page = c.get("page_num", 0)
            conf = c.get("confidence", 100)
            all_text_by_page.setdefault(page, {"text": [], "confidence": conf})
            all_text_by_page[page]["text"].append(c.get("content_text", ""))

        for page, data in all_text_by_page.items():
            full_text = "\n".join(data["text"])
            conf = data.get("confidence", 100)
            kv_from_text = self._extract_kv_from_text(full_text, page, match_words, key_map, conf)
            key_values.extend(kv_from_text)

        # 2. 从表格中提取
        for table in tables:
            page = table.get("page_num", 0)
            headers = table.get("headers", [])
            rows = table.get("rows", [])

            for col_idx, header in enumerate(headers):
                header_clean = str(header).strip()
                matched_key = self._match_key(header_clean, match_words, key_map)
                if matched_key:
                    for row in rows:
                        if col_idx < len(row):
                            val = str(row[col_idx]).strip()
                            if val:
                                key_values.append({
                                    "key": matched_key,
                                    "value": val,
                                    "source": "table",
                                    "page": page,
                                    "confidence": 100
                                })

        # 3. 从OCR空间数据中提取（基于位置关系的键值匹配）
        if all_ocr_lines:
            spatial_kvs = self._extract_kv_from_spatial(all_ocr_lines, match_words, key_map)
            key_values.extend(spatial_kvs)

        # 去重：同一个 key + value 只保留第一个（优先保留置信度高的）
        seen = {}
        for kv in key_values:
            sig = (kv["key"], kv["value"])
            if sig not in seen:
                seen[sig] = kv
            else:
                if kv.get("confidence", 0) > seen[sig].get("confidence", 0):
                    seen[sig] = kv

        return list(seen.values())

    def _extract_kv_from_text(self, text: str, page: int, match_words: List[str], key_map: Dict, confidence: int = 100) -> List[Dict]:
        """从文本中用正则提取键值对（多种模式）"""
        results = []
        lines = text.split('\n')

        # 模式1: 关键字[:：]\s*值（在同一行）
        pattern = r'({})\s*[:：=]\s*(.+)'.format('|'.join(re.escape(k) for k in sorted(match_words, key=len, reverse=True)))
        for m in re.finditer(pattern, text):
            raw_key = m.group(1).strip()
            val = m.group(2).strip()
            val = re.split(r'\s{2,}|\n', val)[0].strip()
            if val and raw_key in key_map:
                results.append({
                    "key": key_map[raw_key],
                    "value": val,
                    "source": "text",
                    "page": page,
                    "confidence": confidence
                })

        # 模式2: 关键字后跟多个空格再跟值（在同一行）
        for word in sorted(match_words, key=len, reverse=True):
            p = re.compile(r'{}\s{{2,}}(\S.+)'.format(re.escape(word)))
            for m in p.finditer(text):
                val = m.group(1).strip()
                val = re.split(r'\s{2,}|\n', val)[0].strip()
                if val and word in key_map:
                    results.append({
                        "key": key_map[word],
                        "value": val,
                        "source": "text",
                        "page": page,
                        "confidence": confidence
                    })

        # 模式3: 关键字独占一行，下一行是值
        for word in sorted(match_words, key=len, reverse=True):
            for i, line in enumerate(lines):
                stripped = line.strip()
                # 关键字完全匹配或包含关键字（但不包含额外信息）
                if stripped == word or (word in stripped and len(stripped) <= len(word) + 2):
                    # 取下一行作为值
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and len(next_line) > 1 and not self._is_keyword(next_line, match_words):
                            results.append({
                                "key": key_map[word],
                                "value": next_line,
                                "source": "text",
                                "page": page,
                                "confidence": confidence
                            })

        # 模式4: 关键字后紧跟值（无分隔符，在同一行）
        for word in sorted(match_words, key=len, reverse=True):
            p = re.compile(r'{}(\S+.*)'.format(re.escape(word)))
            for m in p.finditer(text):
                val = m.group(1).strip()
                if val and len(val) > 1 and not self._is_keyword(val, match_words):
                    results.append({
                        "key": key_map[word],
                        "value": val,
                        "source": "text",
                        "page": page,
                        "confidence": max(confidence - 10, 50)  # 略低置信度
                    })

        return results

    def _is_keyword(self, text: str, match_words: List[str]) -> bool:
        """检查文本是否是某个关键字"""
        text = text.strip()
        for word in match_words:
            if text == word or (word in text and len(text) <= len(word) + 2):
                return True
        return False

    def _extract_kv_from_spatial(self, all_ocr_lines: Dict, match_words: List[str], key_map: Dict) -> List[Dict]:
        """从OCR空间数据中基于位置关系提取键值对"""
        results = []

        for page_num, ocr_lines in all_ocr_lines.items():
            for i, line_data in enumerate(ocr_lines):
                text = line_data["text"].strip()
                matched_key = None

                # 检查当前行是否包含关键字
                for word in match_words:
                    if text == word or text == word.replace(" ", ""):
                        matched_key = key_map[word]
                        break
                    # 关键字是文本的一部分（如"图号"在"图号CA20"中）
                    if word in text and len(text) <= len(word) + 4:
                        matched_key = key_map[word]
                        break

                if not matched_key:
                    continue

                bbox = line_data["bbox"]
                # 计算当前行的中心Y和右边界X
                curr_center_y = (bbox[0][1] + bbox[2][1]) / 2
                curr_right_x = bbox[1][0]
                curr_bottom_y = bbox[2][1]

                best_value = None
                best_dist = float('inf')

                # 策略1: 找右侧相邻的文本（同一行右边）
                for j, other in enumerate(ocr_lines):
                    if j == i:
                        continue
                    other_bbox = other["bbox"]
                    other_left_x = other_bbox[0][0]
                    other_center_y = (other_bbox[0][1] + other_bbox[2][1]) / 2

                    # 在同一行（Y接近）且在右侧（X更大）
                    if abs(other_center_y - curr_center_y) < 20 and other_left_x > curr_right_x - 10:
                        other_text = other["text"].strip()
                        if other_text and not self._is_keyword(other_text, match_words):
                            dist = other_left_x - curr_right_x
                            if dist < best_dist:
                                best_dist = dist
                                best_value = other_text

                # 策略2: 找下方相邻的文本（下一行）
                if best_value is None:
                    for j, other in enumerate(ocr_lines):
                        if j == i:
                            continue
                        other_bbox = other["bbox"]
                        other_top_y = other_bbox[0][1]
                        other_left_x = other_bbox[0][0]

                        # 在下方（Y更大）且X位置接近
                        if other_top_y > curr_bottom_y and other_top_y - curr_bottom_y < 100:
                            if abs(other_left_x - bbox[0][0]) < 80:
                                other_text = other["text"].strip()
                                if other_text and len(other_text) > 1 and not self._is_keyword(other_text, match_words):
                                    dist = other_top_y - curr_bottom_y
                                    if dist < best_dist:
                                        best_dist = dist
                                        best_value = other_text

                if best_value:
                    results.append({
                        "key": matched_key,
                        "value": best_value,
                        "source": "ocr_spatial",
                        "page": page_num,
                        "confidence": int(line_data.get("confidence", 0.8) * 100)
                    })

        return results

    def _match_key(self, header: str, match_words: List[str], key_map: Dict) -> Optional[str]:
        """匹配表头与关键字"""
        header = header.strip()
        if header in key_map:
            return key_map[header]
        for word in match_words:
            if word in header or header in word:
                return key_map.get(word)
        return None

    # ---------- 工具方法 ----------

    def _clean_table(self, table: List[List[Any]]) -> List[List[str]]:
        """清理表格数据，将None转为空字符串"""
        cleaned = []
        for row in table:
            cleaned_row = [str(cell) if cell is not None else "" for cell in row]
            cleaned.append(cleaned_row)
        return cleaned

    def extract_tables_with_camelot(self, file_path: str, flavor: str = 'lattice') -> List[Dict]:
        """使用Camelot提取表格（备用方案）"""
        try:
            import camelot
            tables = camelot.read_pdf(file_path, flavor=flavor, pages='all')
            result = []
            for i, table in enumerate(tables):
                df = table.df
                result.append({
                    "page_num": table.page,
                    "table_index": i,
                    "headers": df.columns.tolist(),
                    "rows": df.values.tolist(),
                    "accuracy": table.accuracy
                })
            return result
        except ImportError:
            return []
        except Exception as e:
            print(f"Camelot解析失败: {str(e)}")
            return []


parser_service = PdfParserService()
