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
