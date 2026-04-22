package org.pdfreader.pdfreader.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.pdfreader.pdfreader.dto.ContentResponse;
import org.pdfreader.pdfreader.dto.ParseResponse;
import org.pdfreader.pdfreader.entity.PdfContent;
import org.pdfreader.pdfreader.entity.PdfDocument;
import org.pdfreader.pdfreader.repository.PdfContentRepository;
import org.pdfreader.pdfreader.repository.PdfDocumentRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class PdfParserService {

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private PdfDocumentRepository documentRepository;

    @Autowired
    private PdfContentRepository contentRepository;

    @Value("${parser.service.url}")
    private String parserServiceUrl;

    private final ObjectMapper objectMapper = new ObjectMapper();

    /**
     * 上传PDF到Python解析服务
     */
    public ParseResponse uploadAndParse(MultipartFile file) throws IOException {
        String url = parserServiceUrl + "/api/v1/upload";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        ByteArrayResource fileResource = new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        };

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", fileResource);

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        ResponseEntity<ParseResponse> response = restTemplate.exchange(
            url,
            HttpMethod.POST,
            requestEntity,
            ParseResponse.class
        );

        return response.getBody();
    }

    /**
     * 批量上传PDF到Python解析服务
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> uploadBatch(List<MultipartFile> files, String relations) throws IOException {
        String url = parserServiceUrl + "/api/v1/upload/batch";

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        for (MultipartFile file : files) {
            ByteArrayResource fileResource = new ByteArrayResource(file.getBytes()) {
                @Override
                public String getFilename() {
                    return file.getOriginalFilename();
                }
            };
            body.add("files", fileResource);
        }

        if (relations != null && !relations.isEmpty()) {
            body.add("relations", relations);
        }

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);

        ResponseEntity<Map> response = restTemplate.exchange(
            url,
            HttpMethod.POST,
            requestEntity,
            Map.class
        );

        return response.getBody();
    }

    /**
     * 查询解析状态
     */
    public ParseResponse getStatus(Long docId) {
        String url = parserServiceUrl + "/api/v1/status/" + docId;
        return restTemplate.getForObject(url, ParseResponse.class);
    }

    /**
     * 获取解析内容
     */
    public List<ContentResponse> getContent(Long docId, String contentType, Integer page) {
        StringBuilder url = new StringBuilder(parserServiceUrl + "/api/v1/content/" + docId);
        url.append("?");
        if (contentType != null) {
            url.append("content_type=").append(contentType).append("&");
        }
        if (page != null) {
            url.append("page=").append(page);
        }

        ResponseEntity<List> response = restTemplate.exchange(
            url.toString(),
            HttpMethod.GET,
            null,
            List.class
        );

        return response.getBody();
    }

    /**
     * 删除文档
     */
    public void deleteDocument(Long docId) {
        String url = parserServiceUrl + "/api/v1/document/" + docId;
        restTemplate.delete(url);
    }

    /**
     * 获取所有文档列表
     */
    public List<PdfDocument> getAllDocuments() {
        return documentRepository.findByOrderByUploadTimeDesc();
    }

    /**
     * 获取关键信息键值对
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> getKeyValues(Long docId) {
        String url = parserServiceUrl + "/api/v1/key-values/" + docId;
        ResponseEntity<Map> response = restTemplate.exchange(
            url,
            HttpMethod.GET,
            null,
            Map.class
        );
        return response.getBody();
    }

    /**
     * 获取所有关键字配置
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listKeys() {
        String url = parserServiceUrl + "/api/v1/keys";
        ResponseEntity<List> response = restTemplate.exchange(
            url,
            HttpMethod.GET,
            null,
            List.class
        );
        return response.getBody();
    }

    /**
     * 新增关键字
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> createKey(Map<String, Object> keyConfig) {
        String url = parserServiceUrl + "/api/v1/keys";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(keyConfig, headers);
        ResponseEntity<Map> response = restTemplate.exchange(
            url,
            HttpMethod.POST,
            entity,
            Map.class
        );
        return response.getBody();
    }

    /**
     * 更新关键字
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> updateKey(Long keyId, Map<String, Object> keyConfig) {
        String url = parserServiceUrl + "/api/v1/keys/" + keyId;
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(keyConfig, headers);
        ResponseEntity<Map> response = restTemplate.exchange(
            url,
            HttpMethod.PUT,
            entity,
            Map.class
        );
        return response.getBody();
    }

    /**
     * 删除关键字
     */
    public void deleteKey(Long keyId) {
        String url = parserServiceUrl + "/api/v1/keys/" + keyId;
        restTemplate.delete(url);
    }

    // ==================== 关联关系管理 ====================

    /**
     * 获取文档的所有关联关系
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getDocumentRelations(Long docId) {
        String url = parserServiceUrl + "/api/v1/documents/" + docId + "/relations";
        ResponseEntity<List> response = restTemplate.exchange(
            url,
            HttpMethod.GET,
            null,
            List.class
        );
        return response.getBody();
    }

    /**
     * 获取关联文档列表
     */
    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getRelatedDocuments(Long docId) {
        String url = parserServiceUrl + "/api/v1/documents/" + docId + "/related";
        ResponseEntity<List> response = restTemplate.exchange(
            url,
            HttpMethod.GET,
            null,
            List.class
        );
        return response.getBody();
    }

    /**
     * 手动创建关联关系
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> createRelation(Map<String, Object> relation) {
        String url = parserServiceUrl + "/api/v1/relations";
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(relation, headers);
        ResponseEntity<Map> response = restTemplate.exchange(
            url,
            HttpMethod.POST,
            entity,
            Map.class
        );
        return response.getBody();
    }

    /**
     * 删除关联关系
     */
    public void deleteRelation(Long relationId) {
        String url = parserServiceUrl + "/api/v1/relations/" + relationId;
        restTemplate.delete(url);
    }

    /**
     * 自动检测所有文档的关联关系
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> autoDetectRelations() {
        String url = parserServiceUrl + "/api/v1/relations/auto-detect";
        ResponseEntity<Map> response = restTemplate.exchange(
            url,
            HttpMethod.POST,
            null,
            Map.class
        );
        return response.getBody();
    }
}
