# 关键字驱动的图纸关联识别实现总结

## 概述
项目已完成基于用户指定关键字的多图纸关联识别功能，支持自动识别主图/子图关系。

## 实现的功能

### 1. 数据库表补全 ✓
**文件**: `sql/init.sql`

添加了缺失的三个表：
- `key_config` - 用户自定义关键字配置表
- `key_data` - 关键字提取结果表
- `pdf_document_relation` - 图纸关联关系表（已存在，确保完整）

### 2. 后端关键字驱动的主/子检测 ✓
**文件**: `pdf-parser-service/app/services/relation_service.py`

新增方法：
- `detect_main_sub_by_keywords()` - 基于关键字值自动检测主/子图纸关系
  - 支持指定主图关键字名称和值
  - 支持子图关键字名称（默认同主图）
  - 支持子图值的通配符匹配模式（如 `A-100-*`）
  - 自动更新文档的 `is_main` 和 `parent_doc_id` 字段

- `_match_pattern()` - 简单的模式匹配工具（支持 `*` 通配符）

### 3. 上传接口改进 ✓
**文件**: `pdf-parser-service/app/api/routes.py`

修改内容：
- 新增 `MainSubRelationConfig` schema 用于接收关键字配置
- 修改 `/upload/batch` 接口，改为接收关键字驱动的关系配置
  - 旧格式：`{"mainDocIndex": 0, "subDocIndices": [2]}`
  - 新格式：`{"main_key": "图号", "main_value": "A-100", "sub_key": "图号", "sub_value_pattern": "A-100-*"}`

- 修改 `_set_relations_after_parse()` 延迟任务
  - 解析完成后自动调用 `detect_main_sub_by_keywords()` 检测主/子关系
  - 同时执行 `detect_relations()` 检测其他基于相同关键字值的关联

### 4. 前端 UI 更新 ✓
**文件**: `src/main/resources/static/index.html`

改进内容：
- 替换了索引输入为关键字选择
  - 主图关键字选择器
  - 主图关键字值输入框
  - 子图关键字选择器（可选，默认同主图）
  - 子图匹配模式输入框（可选，支持通配符）

- 更新了 `loadKeys()` 函数，同时填充关键字选择器
- 更新了上传逻辑，构建新的关键字配置格式

## 工作流程

### 用户操作流程
1. 在"关键字配置"区域添加关键字（如"图号"）
2. 在"批量上传PDF"区域：
   - 选择多个PDF文件
   - 选择主图关键字和值（如：关键字="图号"，值="A-100"）
   - 可选：指定子图关键字和匹配模式（如：模式="A-100-*"）
   - 点击"批量上传并解析"

### 后台处理流程
1. 文件上传到服务器
2. 后台任务逐个处理PDF文件
3. 提取关键字值并保存到 `key_data` 表
4. 所有文件解析完成后，执行关联检测：
   - 调用 `detect_main_sub_by_keywords()` 按关键字值检测主/子关系
   - 调用 `detect_relations()` 检测其他相同关键字值的关联
5. 在 `pdf_document_relation` 表中记录所有关系

## 数据库关系类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `main` | 子图指向主图 | 子图 → 主图 |
| `sub` | 主图指向子图 | 主图 → 子图 |
| `related` | 相同关键字值的关联 | 图纸A → 图纸B（同一物料编码） |

## 测试验证

运行测试脚本验证功能：
```bash
python test_keyword_relations.py
```

测试结果：
- ✓ 创建关键字配置
- ✓ 创建测试文档
- ✓ 添加关键字值
- ✓ 检测主/子关系（3个关系）
- ✓ 验证文档标记（is_main, parent_doc_id）

## API 示例

### 批量上传（关键字驱动）
```bash
curl -X POST http://localhost:9090/api/v1/upload/batch \
  -F "files=@doc1.pdf" \
  -F "files=@doc2.pdf" \
  -F "files=@doc3.pdf" \
  -F 'relations={"main_key":"图号","main_value":"A-100","sub_key":"图号","sub_value_pattern":"A-100-*"}'
```

### 获取文档关联
```bash
curl http://localhost:9090/api/v1/documents/{docId}/related
```

## 注意事项

1. **关键字必须先配置** - 在上传前需要在"关键字配置"区域添加相应的关键字
2. **关键字值提取** - 系统会自动从PDF中提取关键字值，需要确保PDF中包含相应的关键字
3. **模式匹配** - 子图匹配模式支持 `*` 通配符（如 `A-100-*` 匹配 `A-100-01`, `A-100-02` 等）
4. **自动检测** - 即使不指定主/子关系配置，系统也会自动检测相同关键字值的关联

## 后续改进建议

1. 支持多个主图关键字的组合匹配
2. 支持更复杂的模式匹配（正则表达式）
3. 提供关系检测的可视化编辑界面
4. 支持手动调整自动检测的关系
