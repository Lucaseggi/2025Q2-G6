package com.simpla.vectorial.dto;

import java.util.List;
import java.util.Map;

public class SearchResponseDTO {
    private final boolean success;
    private final String message;
    private final List<DocumentMatch> results;

    public SearchResponseDTO(boolean success, String message, List<DocumentMatch> results) {
        this.success = success;
        this.message = message;
        this.results = results;
    }

    public boolean isSuccess() {
        return success;
    }

    public String getMessage() {
        return message;
    }

    public List<DocumentMatch> getResults() {
        return results;
    }

    public static class DocumentMatch {
        private final String documentId;
        private final double score;
        private final Map<String, Object> metadata;

        public DocumentMatch(String documentId, double score, Map<String, Object> metadata) {
            this.documentId = documentId;
            this.score = score;
            this.metadata = metadata;
        }

        public String getDocumentId() {
            return documentId;
        }

        public double getScore() {
            return score;
        }

        public Map<String, Object> getMetadata() {
            return metadata;
        }
    }
}
