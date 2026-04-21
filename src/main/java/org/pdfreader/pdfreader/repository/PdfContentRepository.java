package org.pdfreader.pdfreader.repository;

import org.pdfreader.pdfreader.entity.PdfContent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PdfContentRepository extends JpaRepository<PdfContent, Long> {
    List<PdfContent> findByDocId(Long docId);
    List<PdfContent> findByDocIdAndContentType(Long docId, String contentType);
    List<PdfContent> findByDocIdAndPageNum(Long docId, Integer pageNum);
    void deleteByDocId(Long docId);
}
