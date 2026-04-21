package org.pdfreader.pdfreader.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;

public class ContentResponse {
    private Long id;
    @JsonProperty("doc_id")
    private Long docId;
    @JsonProperty("page_num")
    private Integer pageNum;
    @JsonProperty("content_type")
    private String contentType;
    @JsonProperty("content_text")
    private String contentText;
    @JsonProperty("table_data")
    private String tableData;
    @JsonProperty("created_at")
    private LocalDateTime createdAt;

    public ContentResponse() {}

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getDocId() { return docId; }
    public void setDocId(Long docId) { this.docId = docId; }
    public Integer getPageNum() { return pageNum; }
    public void setPageNum(Integer pageNum) { this.pageNum = pageNum; }
    public String getContentType() { return contentType; }
    public void setContentType(String contentType) { this.contentType = contentType; }
    public String getContentText() { return contentText; }
    public void setContentText(String contentText) { this.contentText = contentText; }
    public String getTableData() { return tableData; }
    public void setTableData(String tableData) { this.tableData = tableData; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
