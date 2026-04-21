package org.pdfreader.pdfreader.repository;

import org.pdfreader.pdfreader.entity.PdfDocument;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface PdfDocumentRepository extends JpaRepository<PdfDocument, Long> {
    List<PdfDocument> findByStatus(String status);
    List<PdfDocument> findByOrderByUploadTimeDesc();
}
