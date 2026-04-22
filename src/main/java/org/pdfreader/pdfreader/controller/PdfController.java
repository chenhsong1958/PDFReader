
package org.pdfreader.pdfreader.controller;

import org.pdfreader.pdfreader.dto.ContentResponse;
import org.pdfreader.pdfreader.dto.ParseResponse;
import org.pdfreader.pdfreader.entity.PdfDocument;
import org.pdfreader.pdfreader.service.PdfParserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1")
@CrossOrigin(origins = "*")
public class PdfController {

    @Autowired
    private PdfParserService pdfParserService;

    @PostMapping("/upload")
    public ResponseEntity<ParseResponse> uploadPdf(@RequestParam("file") MultipartFile file) throws IOException {
        if (file.isEmpty() || !file.getOriginalFilename().toLowerCase().endsWith(".pdf")) {
            return ResponseEntity.badRequest().body(
                new ParseResponse(null, "error", 0, 0, "请上传PDF文件")
            );
        }
        ParseResponse response = pdfParserService.uploadAndParse(file);
        return ResponseEntity.ok(response);
    }

    @PostMapping(value = "/upload/batch", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<Map<String, Object>> uploadBatch(
        @RequestParam("files") List<MultipartFile> files,
        @RequestParam(value = "relations", required = false) String relations
    ) throws IOException {
        Map<String, Object> response = pdfParserService.uploadBatch(files, relations);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/status/{docId}")
    public ResponseEntity<ParseResponse> getStatus(@PathVariable Long docId) {
        ParseResponse response = pdfParserService.getStatus(docId);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/content/{docId}")
    public ResponseEntity<List<ContentResponse>> getContent(
        @PathVariable Long docId,
        @RequestParam(required = false) String contentType,
        @RequestParam(required = false) Integer page
    ) {
        List<ContentResponse> content = pdfParserService.getContent(docId, contentType, page);
        return ResponseEntity.ok(content);
    }

    @GetMapping("/key-values/{docId}")
    public ResponseEntity<Map<String, Object>> getKeyValues(@PathVariable Long docId) {
        Map<String, Object> result = pdfParserService.getKeyValues(docId);
        return ResponseEntity.ok(result);
    }

    // ==================== 关键字配置管理 ====================

    @GetMapping("/keys")
    public ResponseEntity<List<Map<String, Object>>> listKeys() {
        return ResponseEntity.ok(pdfParserService.listKeys());
    }

    @PostMapping("/keys")
    public ResponseEntity<Map<String, Object>> createKey(@RequestBody Map<String, Object> keyConfig) {
        return ResponseEntity.ok(pdfParserService.createKey(keyConfig));
    }

    @PutMapping("/keys/{keyId}")
    public ResponseEntity<Map<String, Object>> updateKey(
        @PathVariable Long keyId,
        @RequestBody Map<String, Object> keyConfig
    ) {
        return ResponseEntity.ok(pdfParserService.updateKey(keyId, keyConfig));
    }

    @DeleteMapping("/keys/{keyId}")
    public ResponseEntity<Void> deleteKey(@PathVariable Long keyId) {
        pdfParserService.deleteKey(keyId);
        return ResponseEntity.ok().build();
    }

    @GetMapping("/documents")
    public ResponseEntity<List<PdfDocument>> getAllDocuments() {
        return ResponseEntity.ok(pdfParserService.getAllDocuments());
    }

    @DeleteMapping("/document/{docId}")
    public ResponseEntity<Void> deleteDocument(@PathVariable Long docId) {
        pdfParserService.deleteDocument(docId);
        return ResponseEntity.ok().build();
    }

    // ==================== 关联关系管理 ====================

    @GetMapping("/documents/{docId}/relations")
    public ResponseEntity<List<Map<String, Object>>> getDocumentRelations(@PathVariable Long docId) {
        return ResponseEntity.ok(pdfParserService.getDocumentRelations(docId));
    }

    @GetMapping("/documents/{docId}/related")
    public ResponseEntity<List<Map<String, Object>>> getRelatedDocuments(@PathVariable Long docId) {
        return ResponseEntity.ok(pdfParserService.getRelatedDocuments(docId));
    }

    @PostMapping("/relations")
    public ResponseEntity<Map<String, Object>> createRelation(@RequestBody Map<String, Object> relation) {
        return ResponseEntity.ok(pdfParserService.createRelation(relation));
    }

    @DeleteMapping("/relations/{relationId}")
    public ResponseEntity<Void> deleteRelation(@PathVariable Long relationId) {
        pdfParserService.deleteRelation(relationId);
        return ResponseEntity.ok().build();
    }

    @PostMapping("/relations/auto-detect")
    public ResponseEntity<Map<String, Object>> autoDetectRelations() {
        return ResponseEntity.ok(pdfParserService.autoDetectRelations());
    }
}
