package org.pdfreader.pdfreader.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "pdf_document")
public class PdfDocument {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String fileName;

    private String filePath;

    private Long fileSize;

    private Integer pageCount;

    @Column(updatable = false)
    private LocalDateTime uploadTime;

    private LocalDateTime parseTime;

    private String status = "pending";

    private String errorMessage;

    @PrePersist
    protected void onCreate() {
        uploadTime = LocalDateTime.now();
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getFileName() { return fileName; }
    public void setFileName(String fileName) { this.fileName = fileName; }
    public String getFilePath() { return filePath; }
    public void setFilePath(String filePath) { this.filePath = filePath; }
    public Long getFileSize() { return fileSize; }
    public void setFileSize(Long fileSize) { this.fileSize = fileSize; }
    public Integer getPageCount() { return pageCount; }
    public void setPageCount(Integer pageCount) { this.pageCount = pageCount; }
    public LocalDateTime getUploadTime() { return uploadTime; }
    public void setUploadTime(LocalDateTime uploadTime) { this.uploadTime = uploadTime; }
    public LocalDateTime getParseTime() { return parseTime; }
    public void setParseTime(LocalDateTime parseTime) { this.parseTime = parseTime; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }
}
