-- PDFReader 数据库初始化脚本
-- 创建数据库
CREATE DATABASE IF NOT EXISTS pdf_reader DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pdf_reader;

-- 文档基础表
CREATE TABLE IF NOT EXISTS pdf_document (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) COMMENT '文件存储路径',
    file_size BIGINT COMMENT '文件大小(字节)',
    page_count INT COMMENT '页数',
    upload_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    parse_time DATETIME COMMENT '解析完成时间',
    status VARCHAR(50) DEFAULT 'pending' COMMENT '状态: pending/processing/completed/failed',
    error_message TEXT COMMENT '错误信息',
    is_main TINYINT DEFAULT 0 COMMENT '是否为主图纸: 0-否 1-是',
    parent_doc_id BIGINT NULL COMMENT '父图纸ID(子图纸时使用)',
    INDEX idx_status (status),
    INDEX idx_upload_time (upload_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PDF文档表';

-- 提取内容表
CREATE TABLE IF NOT EXISTS pdf_content (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    doc_id BIGINT NOT NULL COMMENT '文档ID',
    page_num INT COMMENT '页码',
    content_type VARCHAR(50) COMMENT '内容类型: text/table/image',
    content_text TEXT COMMENT '文本内容',
    table_data JSON COMMENT '表格数据(JSON格式)',
    bbox JSON COMMENT '边界框坐标[x0,y0,x1,y1]',
    confidence INT COMMENT '置信度(0-100)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_id (doc_id),
    INDEX idx_content_type (content_type),
    INDEX idx_page_num (page_num),
    FOREIGN KEY (doc_id) REFERENCES pdf_document(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PDF内容表';

-- 解析任务日志表（可选，用于追踪解析历史）
CREATE TABLE IF NOT EXISTS parse_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    doc_id BIGINT NOT NULL,
    action VARCHAR(100) COMMENT '操作类型',
    detail TEXT COMMENT '详细信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_id (doc_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='解析日志表';

-- 关键字配置表 — 用户自定义需要提取的关键字
CREATE TABLE IF NOT EXISTS key_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    key_name VARCHAR(100) NOT NULL UNIQUE COMMENT '关键字名称，如：物料编码',
    aliases JSON COMMENT '别名列表，如：["物料号","零件编号","Item No"]',
    description VARCHAR(255) COMMENT '说明',
    enabled TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_enabled (enabled)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关键字配置表';

-- 提取结果表 — 按关键字分类存储提取值
CREATE TABLE IF NOT EXISTS key_data (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    doc_id BIGINT NOT NULL COMMENT '文档ID',
    key_name VARCHAR(100) NOT NULL COMMENT '对应key_config.key_name',
    key_value TEXT COMMENT '提取到的值',
    source VARCHAR(20) COMMENT '来源: text 或 table',
    page_num INT COMMENT '所在页码',
    confidence INT COMMENT '置信度',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doc_id (doc_id),
    INDEX idx_key_name (key_name),
    FOREIGN KEY (doc_id) REFERENCES pdf_document(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='关键字提取结果表';

-- 图纸关联关系表
CREATE TABLE IF NOT EXISTS pdf_document_relation (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source_doc_id BIGINT NOT NULL COMMENT '源图纸ID',
    target_doc_id BIGINT NOT NULL COMMENT '目标图纸ID',
    relation_type VARCHAR(20) NOT NULL COMMENT '关联类型: main(主图纸)/sub(子图纸)/related(关联)',
    match_key VARCHAR(100) COMMENT '匹配的关键字',
    match_value VARCHAR(500) COMMENT '匹配的关键字值',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source_doc (source_doc_id),
    INDEX idx_target_doc (target_doc_id),
    INDEX idx_relation_type (relation_type),
    UNIQUE KEY uk_source_target (source_doc_id, target_doc_id),
    FOREIGN KEY (source_doc_id) REFERENCES pdf_document(id) ON DELETE CASCADE,
    FOREIGN KEY (target_doc_id) REFERENCES pdf_document(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='图纸关联关系表';
