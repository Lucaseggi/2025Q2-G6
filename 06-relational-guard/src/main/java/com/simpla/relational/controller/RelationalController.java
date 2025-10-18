package com.simpla.relational.controller;

import com.simpla.relational.dto.GetBatchRequestDTO;
import com.simpla.relational.dto.GetBatchResponseDTO;
import com.simpla.relational.dto.ReconstructNormResponseDTO;
import com.simpla.relational.dto.StoreResponseDTO;
import com.simpla.relational.processor.RelationalProcessor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.stream.Collectors;

/**
 * REST API Controller for relational document storage and retrieval.
 * Delegates all business logic to RelationalProcessor.
 */
@RestController
@RequestMapping("/api/v1/relational")
public class RelationalController {

    private final RelationalProcessor processor;

    public RelationalController(RelationalProcessor processor) {
        this.processor = processor;
    }

    /**
     * Store a norma document
     * POST /api/v1/relational/store
     *
     * Request body: JSON string containing norma data
     * Response: StoreResponseDTO with success status and PK mapping JSON
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
                null
            );
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Reconstruct a norma by infoleg_id
     * GET /api/v1/relational/reconstruct?infoleg_id={infoleg_id}
     *
     * Query parameter: infoleg_id (required)
     * Response: ReconstructNormResponseDTO with norma JSON
     */
    @GetMapping("/reconstruct")
    public ResponseEntity<ReconstructNormResponseDTO> reconstructByInfolegId(
            @RequestParam("infoleg_id") int infolegId) {
        try {
            ReconstructNormResponseDTO response = processor.processReconstructByInfolegId(infolegId);

            if (response.isSuccess()) {
                return ResponseEntity.ok(response);
            } else {
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
            }
        } catch (Exception e) {
            ReconstructNormResponseDTO errorResponse = new ReconstructNormResponseDTO(
                false,
                "Error processing reconstruct request: " + e.getMessage(),
                null
            );
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Reconstruct a norma by database id
     * GET /api/v1/relational/reconstruct/{id}
     *
     * Path parameter: id (required)
     * Response: ReconstructNormResponseDTO with norma JSON
     */
    @GetMapping("/reconstruct/{id}")
    public ResponseEntity<ReconstructNormResponseDTO> reconstructById(@PathVariable long id) {
        try {
            ReconstructNormResponseDTO response = processor.processReconstructById(id);

            if (response.isSuccess()) {
                return ResponseEntity.ok(response);
            } else {
                return ResponseEntity.status(HttpStatus.NOT_FOUND).body(response);
            }
        } catch (Exception e) {
            ReconstructNormResponseDTO errorResponse = new ReconstructNormResponseDTO(
                false,
                "Error processing reconstruct request: " + e.getMessage(),
                null
            );
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Get batch of normas based on entity pairs
     * POST /api/v1/relational/batch
     *
     * Request body: GetBatchRequestDTO with list of entity pairs
     * Response: GetBatchResponseDTO with normas JSON
     */
    @PostMapping("/batch")
    public ResponseEntity<GetBatchResponseDTO> getBatch(@RequestBody GetBatchRequestDTO request) {
        try {
            // Convert request DTOs to processor DTOs
            List<RelationalProcessor.EntityPairDTO> entityPairs = request.getEntities().stream()
                .map(e -> new RelationalProcessor.EntityPairDTO(e.getType(), e.getId()))
                .collect(Collectors.toList());

            GetBatchResponseDTO response = processor.processGetBatch(entityPairs);

            if (response.isSuccess()) {
                return ResponseEntity.ok(response);
            } else {
                return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(response);
            }
        } catch (Exception e) {
            GetBatchResponseDTO errorResponse = new GetBatchResponseDTO(
                false,
                "Error processing batch request: " + e.getMessage(),
                "[]"
            );
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(errorResponse);
        }
    }

    /**
     * Health check endpoint
     * GET /api/v1/relational/health
     */
    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("Relational service is healthy");
    }
}
