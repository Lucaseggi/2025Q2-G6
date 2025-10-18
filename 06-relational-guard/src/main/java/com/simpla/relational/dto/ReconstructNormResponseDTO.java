package com.simpla.relational.dto;

/**
 * DTO for norm reconstruction response.
 * Transport-agnostic response that can be used by gRPC, REST, or any other interface.
 */
public class ReconstructNormResponseDTO {
    private final boolean success;
    private final String message;
    private final String normaJson;

    public ReconstructNormResponseDTO(boolean success, String message, String normaJson) {
        this.success = success;
        this.message = message;
        this.normaJson = normaJson;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public String getNormaJson() {
        return normaJson;
    }
}
