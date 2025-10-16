package com.simpla.vectorial.dto;

public class StoreResponseDTO {
    private final boolean success;
    private final String message;
    private final Integer documentCount;

    public StoreResponseDTO(boolean success, String message, Integer documentCount) {
        this.success = success;
        this.message = message;
        this.documentCount = documentCount;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public Integer getDocumentCount() {
        return documentCount;
    }
}
