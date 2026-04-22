package org.pdfreader.pdfreader.entity;

import javax.persistence.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "pdf_document_relation")
public class PdfDocumentRelation {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long sourceDocId;

    @Column(nullable = false)
    private Long targetDocId;

    @Column(nullable = false)
    private String relationType;

    private String matchKey;

    private String matchValue;

    @Column(updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getSourceDocId() { return sourceDocId; }
    public void setSourceDocId(Long sourceDocId) { this.sourceDocId = sourceDocId; }
    public Long getTargetDocId() { return targetDocId; }
    public void setTargetDocId(Long targetDocId) { this.targetDocId = targetDocId; }
    public String getRelationType() { return relationType; }
    public void setRelationType(String relationType) { this.relationType = relationType; }
    public String getMatchKey() { return matchKey; }
    public void setMatchKey(String matchKey) { this.matchKey = matchKey; }
    public String getMatchValue() { return matchValue; }
    public void setMatchValue(String matchValue) { this.matchValue = matchValue; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
