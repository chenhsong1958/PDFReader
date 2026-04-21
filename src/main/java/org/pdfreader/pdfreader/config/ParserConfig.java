package org.pdfreader.pdfreader.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class ParserConfig {

    @Value("${parser.service.url}")
    private String parserServiceUrl;

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }

    public String getParserServiceUrl() {
        return parserServiceUrl;
    }
}
