package com.simpla.vectorial;

import com.simpla.vectorial.processor.VectorialProcessor;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

import javax.annotation.PreDestroy;

/**
 * Spring Boot Application for Vectorial Guard REST API.
 * This provides an HTTP REST interface alongside the existing gRPC service.
 * Both use the same VectorialProcessor for business logic.
 */
@SpringBootApplication
public class VectorialApplication {

    private VectorialProcessor processor;

    /**
     * Configure VectorialProcessor as a singleton bean
     */
    @Bean
    public VectorialProcessor vectorialProcessor() {
        if (processor == null) {
            processor = new VectorialProcessor();
        }
        return processor;
    }

    /**
     * Ensure proper shutdown of vector store on application termination
     */
    @PreDestroy
    public void onShutdown() {
        if (processor != null) {
            System.out.println("Shutting down VectorialApplication...");
            processor.shutdown();
        }
    }

    public static void main(String[] args) {
        SpringApplication app = new SpringApplication(VectorialApplication.class);
        // Ensure port 8080 is used
        app.setDefaultProperties(java.util.Collections.singletonMap("server.port", "8080"));
        app.run(args);
    }
}
