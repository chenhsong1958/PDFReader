
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
}
