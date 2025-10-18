package com.simpla.relational.dto;

/**
 * DTO for store operation response.
 * Transport-agnostic response that can be used by gRPC, REST, or any other interface.
 */
public class StoreResponseDTO {
    private final boolean success;
    private final String message;
    private final String pkMappingJson;

    public StoreResponseDTO(boolean success, String message, String pkMappingJson) {
        this.success = success;
        this.message = message;
        this.pkMappingJson = pkMappingJson;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public String getPkMappingJson() {
        return pkMappingJson;
    }
}
