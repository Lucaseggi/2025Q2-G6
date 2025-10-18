package com.simpla.vectorial.controller;

import com.simpla.vectorial.dto.SearchRequestDTO;
import com.simpla.vectorial.dto.SearchResponseDTO;
import com.simpla.vectorial.dto.StoreResponseDTO;
import com.simpla.vectorial.processor.VectorialProcessor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

/**
 * REST API Controller for vectorial document storage and search.
 * Delegates all business logic to VectorialProcessor.
 */
@RestController
@RequestMapping("/api/v1/vectorial")
public class VectorialController {

    private final VectorialProcessor processor;

    public VectorialController(VectorialProcessor processor) {
        this.processor = processor;
    }

    /**
     * Store a document with embeddings
     * POST /api/v1/vectorial/store
     *
     * Request body: JSON string containing document data
     * Response: StoreResponseDTO with success status and document count
     */
    @PostMapping("/store")
    public ResponseEntity<StoreResponseDTO> store(@RequestBody String jsonData) {
        try {
            StoreResponseDTO response = processor.processStore(jsonData);

            if (response.isSuccess()) {
                return ResponseEntity.ok(response);
            } else {
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
            }
        } catch (Exception e) {
            StoreResponseDTO errorResponse = new StoreResponseDTO(
                false,
                "Error processing store request: " + e.getMessage(),
                0
            );
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Search for similar documents using vector similarity
     * POST /api/v1/vectorial/search
     *
     * Request body: SearchRequestDTO with embedding, filters, and limit
     * Response: SearchResponseDTO with matching documents
     */
    @PostMapping("/search")
    public ResponseEntity<SearchResponseDTO> search(@RequestBody SearchRequestDTO request) {
        try {
            SearchResponseDTO response = processor.processSearch(request);

            if (response.isSuccess()) {
                return ResponseEntity.ok(response);
            } else {
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
            }
        } catch (Exception e) {
            SearchResponseDTO errorResponse = new SearchResponseDTO(
                false,
                "Error processing search request: " + e.getMessage(),
                java.util.Collections.emptyList()
            );
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Health check endpoint
     * GET /api/v1/vectorial/health
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        boolean isHealthy = processor.getVectorStore().isHealthy();

        if (isHealthy) {
            return ResponseEntity.ok("Vector store is healthy");
        } else {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body("Vector store is not healthy");
        }
    }
}
