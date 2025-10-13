package com.simpla.vectorial.service;

import java.util.List;
import java.util.Map;

public interface VectorStoreService {

    /**
     * Initialize the vector store connection and resources
     */
    void initialize();

    /**
     * Get the total number of documents in the vector store
     * @return document count
     */
    long getDocumentCount();

    /**
     * Check if the vector store is healthy and accessible
     * @return true if healthy, false otherwise
     */
    boolean isHealthy();

    /**
     * Get the type/name of the vector store implementation
     * @return store type identifier
     */
    String getStoreType();

    /**
     * Get the index/collection name being used
     * @return index name
     */
    String getIndexName();

    /**
     * Store a document with its embedding vector
     * @param documentId unique identifier for the document
     * @param embedding the embedding vector
     * @param metadata additional metadata for filtering
     * @return operation result details
     */
    StoreResult storeDocument(String documentId, List<Double> embedding, Map<String, Object> metadata);

    /**
     * Search for similar documents using k-NN with optional metadata filtering
     * @param queryEmbedding the query embedding vector
     * @param filters metadata filters to apply
     * @param limit maximum number of results to return
     * @return search results with scores and metadata
     */
    SearchResult searchDocuments(List<Double> queryEmbedding, Map<String, String> filters, int limit);

    /**
     * Clean up resources and close connections
     */
    void shutdown();

    /**
     * Result of a store operation
     */
    public static class StoreResult {
        private final boolean success;
        private final String message;
        private final String documentId;

        public StoreResult(boolean success, String message, String documentId) {
            this.success = success;
            this.message = message;
            this.documentId = documentId;
        }

        public boolean isSuccess() { return success; }
        public String getMessage() { return message; }
        public String getDocumentId() { return documentId; }
    }

    /**
     * Result of a search operation
     */
    public static class SearchResult {
        private final boolean success;
        private final String message;
        private final List<DocumentMatch> matches;

        public SearchResult(boolean success, String message, List<DocumentMatch> matches) {
            this.success = success;
            this.message = message;
            this.matches = matches;
        }

        public boolean isSuccess() { return success; }
        public String getMessage() { return message; }
        public List<DocumentMatch> getMatches() { return matches; }

        /**
         * Individual document match in search results
         */
        public static class DocumentMatch {
            private final String documentId;
            private final double score;
            private final Map<String, Object> metadata;

            public DocumentMatch(String documentId, double score, Map<String, Object> metadata) {
                this.documentId = documentId;
                this.score = score;
                this.metadata = metadata;
            }

            public String getDocumentId() { return documentId; }
            public double getScore() { return score; }
            public Map<String, Object> getMetadata() { return metadata; }
        }
    }
}