package com.simpla.relational.dto;

/**
 * DTO for batch retrieval response.
 * Transport-agnostic response that can be used by gRPC, REST, or any other interface.
 */
public class GetBatchResponseDTO {
    private final boolean success;
    private final String message;
    private final String normasJson;

    public GetBatchResponseDTO(boolean success, String message, String normasJson) {
        this.success = success;
        this.message = message;
        this.normasJson = normasJson;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public String getNormasJson() {
        return normasJson;
    }
}
