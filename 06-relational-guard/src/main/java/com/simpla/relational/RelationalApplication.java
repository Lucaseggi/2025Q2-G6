package com.simpla.relational;

import com.simpla.relational.processor.RelationalProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import javax.annotation.PreDestroy;

/**
 * Spring Boot Application for Relational Guard REST API.
 * This provides an HTTP REST interface alongside the existing gRPC service.
 * Both use the same RelationalProcessor for business logic.
 */
@SpringBootApplication
public class RelationalApplication {

    private RelationalProcessor processor;

    /**
     * Configure RelationalProcessor as a singleton bean
     */
    @Bean
    public RelationalProcessor relationalProcessor() {
        if (processor == null) {
            processor = new RelationalProcessor();
        }
        return processor;
    }

    /**
     * Ensure proper shutdown of database connection pool on application termination
     */
    @PreDestroy
    public void onShutdown() {
        if (processor != null) {
            System.out.println("Shutting down RelationalApplication...");
            processor.shutdown();
        }
    }

    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(RelationalApplication.class);
        // Ensure port 8090 is used
        app.setDefaultProperties(java.util.Collections.singletonMap("server.port", "8090"));
        app.run(args);
    }
}
