package org.pdfreader.pdfreader.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

public class ParseResponse {
    @JsonProperty("doc_id")
    private Long docId;
    private String status;
    @JsonProperty("page_count")
    private Integer pageCount;
    @JsonProperty("tables_count")
    private Integer tablesCount;
    private String message;

    public ParseResponse() {}

    public ParseResponse(Long docId, String status, Integer pageCount, Integer tablesCount, String message) {
        this.docId = docId;
        this.status = status;
        this.pageCount = pageCount;
        this.tablesCount = tablesCount;
        this.message = message;
    }

    // Getters and Setters
    public Long getDocId() { return docId; }
    public void setDocId(Long docId) { this.docId = docId; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public Integer getPageCount() { return pageCount; }
    public void setPageCount(Integer pageCount) { this.pageCount = pageCount; }
    public Integer getTablesCount() { return tablesCount; }
    public void setTablesCount(Integer tablesCount) { this.tablesCount = tablesCount; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
}
