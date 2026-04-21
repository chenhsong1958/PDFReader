package org.pdfreader.pdfreader.entity;

import javax.persistence.*;
import org.hibernate.annotations.Type;
import java.time.LocalDateTime;

@Entity
@Table(name = "pdf_content")
public class PdfContent {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long docId;

    private Integer pageNum;

    private String contentType;

    @Column(columnDefinition = "TEXT")
    private String contentText;

    @Column(columnDefinition = "JSON")
    private String tableData;

    @Column(columnDefinition = "JSON")
    private String bbox;

    private Integer confidence;

    @Column(updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

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
    public String getBbox() { return bbox; }
    public void setBbox(String bbox) { this.bbox = bbox; }
    public Integer getConfidence() { return confidence; }
    public void setConfidence(Integer confidence) { this.confidence = confidence; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
