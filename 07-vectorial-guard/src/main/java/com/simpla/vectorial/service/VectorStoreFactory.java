package com.simpla.vectorial.service;

import com.simpla.vectorial.service.impl.OpenSearchVectorStore;

public class VectorStoreFactory {

    private static final String OPENSEARCH_TYPE = "opensearch";
    private static final String DEFAULT_TYPE = OPENSEARCH_TYPE;

    /**
     * Create a VectorStoreService instance based on configuration
     * @return configured VectorStoreService implementation
     */
    public static VectorStoreService createVectorStore() {
        String storeType = System.getenv("VECTOR_STORE_TYPE");

        if (storeType == null || storeType.trim().isEmpty()) {
            storeType = DEFAULT_TYPE;
        }

        return createVectorStore(storeType.toLowerCase());
    }

    /**
     * Create a VectorStoreService instance for a specific type
     * @param storeType the type of vector store to create
     * @return configured VectorStoreService implementation
     */
    public static VectorStoreService createVectorStore(String storeType) {
        switch (storeType.toLowerCase()) {
            case OPENSEARCH_TYPE:
                return new OpenSearchVectorStore();

            // Future implementations can be added here:
            // case "pinecone":
            //     return new PineconeVectorStore();
            // case "weaviate":
            //     return new WeaviateVectorStore();

            default:
                System.out.println("Unknown vector store type: " + storeType + ". Falling back to OpenSearch.");
                return new OpenSearchVectorStore();
        }
    }

    /**
     * Get the list of supported vector store types
     * @return array of supported types
     */
    public static String[] getSupportedTypes() {
        return new String[]{OPENSEARCH_TYPE};
    }
}