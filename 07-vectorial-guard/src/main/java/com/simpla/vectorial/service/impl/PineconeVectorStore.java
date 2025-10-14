package com.simpla.vectorial.service.impl;

import com.simpla.vectorial.service.VectorStoreService;
import com.google.protobuf.Struct;
import com.google.protobuf.Value;
import io.grpc.NameResolverRegistry;
import io.grpc.internal.DnsNameResolverProvider;
import io.pinecone.clients.Index;
import io.pinecone.clients.Pinecone;
import io.pinecone.proto.DescribeIndexStatsResponse;
import io.pinecone.proto.UpsertResponse;
import io.pinecone.unsigned_indices_model.QueryResponseWithUnsignedIndices;
import io.pinecone.unsigned_indices_model.ScoredVectorWithUnsignedIndices;
import io.pinecone.unsigned_indices_model.VectorWithUnsignedIndices;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import static io.pinecone.commons.IndexInterface.buildUpsertVectorWithUnsignedIndices;

public class PineconeVectorStore implements VectorStoreService {

    private Pinecone pineconeClient;
    private Index index;
    private String apiKey;
    private String indexName;
    private String environment;

    public PineconeVectorStore() {
        loadConfiguration();
    }

    private void loadConfiguration() {
        apiKey = System.getenv("PINECONE_API_KEY");
        indexName = System.getenv("PINECONE_INDEX_NAME");
        environment = System.getenv("PINECONE_ENVIRONMENT");

        // Set defaults if environment variables are not provided
        indexName = indexName != null ? indexName : "documents";
        environment = environment != null ? environment : "gcp-starter";

        if (apiKey == null || apiKey.trim().isEmpty()) {
            System.err.println("WARNING: PINECONE_API_KEY is not set. Pinecone client will fail to initialize.");
        }

        System.out.println("Pinecone configuration loaded:");
        System.out.println("  Environment: " + environment);
        System.out.println("  Index: " + indexName);
        System.out.println("  API Key: " + (apiKey != null && !apiKey.trim().isEmpty() ? "configured" : "not configured"));
    }

    @Override
    public void initialize() {
        try {
            if (apiKey == null || apiKey.trim().isEmpty()) {
                throw new RuntimeException("PINECONE_API_KEY is required but not configured");
            }

            pineconeClient = new Pinecone.Builder(apiKey).build();
            System.out.println("Pinecone client initialized successfully");

            // MAGIA NEGRA https://mchesnavsky.tech/name-resolution-providers/
            NameResolverRegistry.getDefaultRegistry().register(new DnsNameResolverProvider());

            index = pineconeClient.getIndexConnection(indexName);
            System.out.println("Connected to Pinecone index: " + indexName);

            if (!isHealthy()) {
                throw new RuntimeException("Failed to connect to Pinecone index or index is not accessible");
            }

        } catch (Exception e) {
            System.err.println("Failed to initialize Pinecone client: " + e.getMessage());
            e.printStackTrace();
            throw new RuntimeException("Pinecone initialization failed", e);
        }
    }

    @Override
    public long getDocumentCount() {
        try {
            // Get index stats
            DescribeIndexStatsResponse stats = index.describeIndexStats();

            if (stats != null) {
                long count = stats.getTotalVectorCount();
                System.out.println("Pinecone document count: " + count);
                return count;
            }

            System.out.println("Unable to retrieve document count from Pinecone");
            return -1;

        } catch (Exception e) {
            System.err.println("Failed to get document count from Pinecone: " + e.getMessage());
            e.printStackTrace();
            return -1;
        }
    }

    @Override
    public boolean isHealthy() {
        return true;
//        try {
//            if (index == null) {
//                return false;
//            }
//
//            // Try to get index stats as a health check
//            DescribeIndexStatsResponse stats = index.describeIndexStats();
//            boolean isHealthy = stats != null;
//
//            System.out.println("Pinecone health check: " + (isHealthy ? "healthy" : "unhealthy"));
//            return isHealthy;
//
//        } catch (Exception e) {
//            System.err.println("Pinecone health check failed: " + e.getMessage());
//            return false;
//        }
    }

    @Override
    public String getStoreType() {
        return "Pinecone";
    }

    @Override
    public String getIndexName() {
        return indexName;
    }

    @Override
    public StoreResult storeDocument(String documentId, List<Double> embedding, Map<String, Object> metadata) {
        try {
            // Convert Double list to float list for Pinecone
            List<Float> floatEmbedding = embedding.stream()
                .map(Double::floatValue)
                .collect(Collectors.toList());

            // Convert metadata to Struct format
            Struct.Builder metadataBuilder = Struct.newBuilder();
            if (metadata != null) {
                for (Map.Entry<String, Object> entry : metadata.entrySet()) {
                    Object value = entry.getValue();
                    Value protoValue;

                    if (value instanceof String) {
                        protoValue = Value.newBuilder().setStringValue((String) value).build();
                    } else if (value instanceof Number) {
                        protoValue = Value.newBuilder().setNumberValue(((Number) value).doubleValue()).build();
                    } else if (value instanceof Boolean) {
                        protoValue = Value.newBuilder().setBoolValue((Boolean) value).build();
                    } else {
                        // Default to string representation for other types
                        protoValue = Value.newBuilder().setStringValue(String.valueOf(value)).build();
                    }

                    metadataBuilder.putFields(entry.getKey(), protoValue);
                }
            }

            Struct metadataStruct = metadataBuilder.build();

            // Create vector using buildUpsertVectorWithUnsignedIndices
            // Note: We're not using sparse vectors, so sparseIndices and sparseValues are null
            VectorWithUnsignedIndices vector = buildUpsertVectorWithUnsignedIndices(
                documentId,
                floatEmbedding,
                null,  // sparseIndices
                null,  // sparseValues
                metadataStruct
            );

            // Upsert the vector (empty string means default namespace)
            List<VectorWithUnsignedIndices> vectors = new ArrayList<>();
            vectors.add(vector);
            UpsertResponse response = index.upsert(vectors, "");

            System.out.println("Document stored successfully in Pinecone: " + documentId +
                             " (upserted count: " + response.getUpsertedCount() + ")");

            return new StoreResult(true,
                "Document stored successfully. Upserted count: " + response.getUpsertedCount(),
                documentId);

        } catch (Exception e) {
            String errorMessage = "Failed to store document " + documentId + " in Pinecone: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            return new StoreResult(false, errorMessage, documentId);
        }
    }

    @Override
    public SearchResult searchDocuments(List<Double> queryEmbedding, Map<String, String> filters, int limit) {
        try {
            // Convert Double list to float list for Pinecone
            List<Float> floatEmbedding = queryEmbedding.stream()
                .map(Double::floatValue)
                .collect(Collectors.toList());

            // Convert filters to Struct format for Pinecone metadata filtering
            Struct filterStruct = null;
            if (filters != null && !filters.isEmpty()) {
                Struct.Builder filterBuilder = Struct.newBuilder();

                for (Map.Entry<String, String> filter : filters.entrySet()) {
                    // Create a nested Struct for the $eq operator
                    Struct.Builder eqBuilder = Struct.newBuilder();
                    eqBuilder.putFields("$eq", Value.newBuilder().setStringValue(filter.getValue()).build());

                    // Add the field filter to the main filter struct
                    filterBuilder.putFields(filter.getKey(), Value.newBuilder().setStructValue(eqBuilder.build()).build());
                }

                filterStruct = filterBuilder.build();
            }

            // Execute the query (empty string means default namespace)
            QueryResponseWithUnsignedIndices queryResponse = index.queryByVector(limit, floatEmbedding, "", filterStruct, false, true);

            // Process search results
            List<VectorStoreService.SearchResult.DocumentMatch> matches = new ArrayList<>();

            if (queryResponse.getMatchesList() != null) {
                for (ScoredVectorWithUnsignedIndices match : queryResponse.getMatchesList()) {
                    String documentId = match.getId();
                    double score = match.getScore();

                    // Convert Struct metadata to Map<String, Object>
                    Map<String, Object> metadata = getFilterMap(match);

                    matches.add(new VectorStoreService.SearchResult.DocumentMatch(documentId, score, metadata));
                }
            }

            System.out.println("Search executed successfully in Pinecone. Found " + matches.size() + " matches");

            return new SearchResult(true,
                "Search completed successfully. Found " + matches.size() + " matches",
                matches);

        } catch (Exception e) {
            String errorMessage = "Failed to execute search in Pinecone: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            return new SearchResult(false, errorMessage, new ArrayList<>());
        }
    }

    private static Map<String, Object> getFilterMap(ScoredVectorWithUnsignedIndices match) {
        Map<String, Object> metadata = new HashMap<>();
        if (match.getMetadata() != null) {
            Struct metadataStruct = match.getMetadata();
            for (Map.Entry<String, Value> entry : metadataStruct.getFieldsMap().entrySet()) {
                Value value = entry.getValue();
                Object convertedValue;

                switch (value.getKindCase()) {
                    case STRING_VALUE:
                        convertedValue = value.getStringValue();
                        break;
                    case NUMBER_VALUE:
                        convertedValue = value.getNumberValue();
                        break;
                    case BOOL_VALUE:
                        convertedValue = value.getBoolValue();
                        break;
                    case NULL_VALUE:
                        convertedValue = null;
                        break;
                    default:
                        convertedValue = value.toString();
                        break;
                }

                metadata.put(entry.getKey(), convertedValue);
            }
        }
        return metadata;
    }

    @Override
    public void shutdown() {
        if (pineconeClient != null) {
            try {
                // Pinecone client doesn't require explicit shutdown
                // but we can set references to null for garbage collection
                index = null;
                pineconeClient = null;
                System.out.println("Pinecone client resources released");
            } catch (Exception e) {
                System.err.println("Error during Pinecone client shutdown: " + e.getMessage());
                e.printStackTrace();
            }
        }
    }
}
