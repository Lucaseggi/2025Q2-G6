package com.simpla.vectorial;

import com.simpla.vectorial.proto.VectorialServiceGrpc;
import com.simpla.vectorial.proto.StoreRequest;
import com.simpla.vectorial.proto.StoreResponse;
import com.simpla.vectorial.proto.SearchRequest;
import com.simpla.vectorial.proto.SearchResponse;
import com.simpla.vectorial.proto.SearchResult;
import com.simpla.vectorial.service.VectorStoreService;
import com.simpla.vectorial.service.VectorStoreFactory;
import io.grpc.stub.StreamObserver;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

public class VectorialServiceImpl extends VectorialServiceGrpc.VectorialServiceImplBase {

    private static final String DIVISION = "division";
    private static final String ARTICLE = "article";

    private final VectorStoreService vectorStore;
    private final ObjectMapper objectMapper;

    public VectorialServiceImpl() {
        // Create vector store instance using factory
        this.vectorStore = VectorStoreFactory.createVectorStore();
        this.objectMapper = new ObjectMapper();

        // Initialize the vector store
        try {
            vectorStore.initialize();
            System.out.println("VectorialService initialized with " + vectorStore.getStoreType() +
                             " vector store (index: " + vectorStore.getIndexName() + ")");
        } catch (Exception e) {
            System.err.println("Failed to initialize vector store: " + e.getMessage());
            throw new RuntimeException("Vector store initialization failed", e);
        }
    }

    @Override
    public void store(StoreRequest request, StreamObserver<StoreResponse> responseObserver) {
        String requestData = request.getData();
        System.out.println("Store method called with data length: " + requestData.length());

        try {
            // First check if the vector store is healthy
            if (!vectorStore.isHealthy()) {
                System.err.println("Vector store is not healthy");
                sendErrorResponse(responseObserver, "Vector store is not healthy");
                return;
            }

            // Parse the incoming data
            JsonNode rootNode = objectMapper.readTree(requestData);

            // Handle both old and new data formats
            JsonNode normaNode = null;
            JsonNode structuredDataNode = null;
            Integer infolegId = null;
            String tipoNorma = "";
            String jurisdiccion = "";
            String fechaDeSancion = "";
            Integer nroBoletin = null;
            String tituloSumario = "";

            // Try new ProcessedData format first
            JsonNode scrapingDataNode = rootNode.path("scraping_data");
            if (!scrapingDataNode.isMissingNode()) {
                // New format: ProcessedData structure
                JsonNode infolegResponse = scrapingDataNode.path("infoleg_response");
                JsonNode processingData = rootNode.path("processing_data");

                if (!infolegResponse.isMissingNode()) {
                    infolegId = infolegResponse.path("infoleg_id").asInt();
                    tipoNorma = infolegResponse.path("tipo_norma").asText("");
                    jurisdiccion = infolegResponse.path("jurisdiccion").asText("");
                    fechaDeSancion = infolegResponse.path("sancion").asText("");
                    nroBoletin = infolegResponse.path("nro_boletin").asInt();
                    tituloSumario = infolegResponse.path("titulo_sumario").asText("");

                    // Get structured data from processing_data.parsings.original_text.structured_data
                    if (!processingData.isMissingNode()) {
                        JsonNode parsings = processingData.path("parsings");
                        JsonNode originalTextParsing = parsings.path("original_text");
                        structuredDataNode = originalTextParsing.path("structured_data");
                    }
                }
            } else {
                // Try old format: data.norma structure
                JsonNode dataNode = rootNode.path("data");
                normaNode = dataNode.path("norma");

                if (normaNode.isMissingNode()) {
                    sendErrorResponse(responseObserver, "Invalid data format: neither 'scraping_data' nor 'data.norma' field found");
                    return;
                }

                // Extract basic norma metadata from old format
                infolegId = normaNode.path("infoleg_id").asInt();
                tipoNorma = normaNode.path("tipo_norma").asText("");
                jurisdiccion = normaNode.path("jurisdiccion").asText("");
                fechaDeSancion = normaNode.path("sancion").asText("");
                nroBoletin = normaNode.path("nro_boletin").asInt();
                tituloSumario = normaNode.path("titulo_sumario").asText("");
                structuredDataNode = normaNode.path("structured_texto_norma");
            }

            System.out.println("Processing norma with infoleg_id: " + infolegId);

            // Counter for tracking stored documents
            AtomicInteger documentCount = new AtomicInteger(0);
            List<String> errors = new ArrayList<>();

            // Process structured data if present
            if (!structuredDataNode.isMissingNode()) {
                JsonNode divisions = structuredDataNode.path("divisions");
                if (divisions.isArray()) {
                    processDivisions(divisions, infolegId, tipoNorma,
                            jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario,
                                   "texto_norma", documentCount, errors);
                }
            }

            // For old format, also check for structured_texto_norma_actualizado
            if (normaNode != null) {
                JsonNode structuredTextoNormaActualizado = normaNode.path("structured_texto_norma_actualizado");
                if (!structuredTextoNormaActualizado.isMissingNode()) {
                    JsonNode divisions = structuredTextoNormaActualizado.path("divisions");
                    if (divisions.isArray()) {
                        processDivisions(divisions, infolegId, tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario,
                                       "texto_norma_actualizado", documentCount, errors);
                    }
                }
            }

            // Prepare response
            String message;
            boolean success = errors.isEmpty();

            if (success) {
                message = String.format("Successfully stored %d documents for norma %d",
                                      documentCount.get(), infolegId);
                System.out.println(message);
            } else {
                message = String.format("Partially completed: stored %d documents for norma %d, but %d errors occurred: %s",
                                      documentCount.get(), infolegId, errors.size(),
                                      String.join("; ", errors.subList(0, Math.min(3, errors.size()))));
                System.err.println(message);
            }

            StoreResponse response = StoreResponse.newBuilder()
                    .setSuccess(success)
                    .setMessage(message)
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();

        } catch (Exception e) {
            String errorMessage = "Error processing vectorial store request: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            sendErrorResponse(responseObserver, errorMessage);
        }
    }

    private void processDivisions(JsonNode divisionsArray, Integer infolegId, String tipoNorma,
                                 String jurisdiccion, String fechaDeSancion, Integer nroBoletin, String tituloSumario, String source, AtomicInteger documentCount,
                                 List<String> errors) {
        for (int i = 0; i < divisionsArray.size(); i++) {
            JsonNode division = divisionsArray.get(i);
            processDivision(division, infolegId, tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario, source, i, documentCount, errors);
        }
    }

    private void processDivision(JsonNode division, Integer infolegId, String tipoNorma,
                                String jurisdiccion, String fechaDeSancion, Integer nroBoletin, String tituloSumario, String source, int divisionIndex,
                                AtomicInteger documentCount, List<String> errors) {
        String divisionName = division.path("name").asText("Unknown");
        System.out.println("Processing division " + divisionIndex + ": " + divisionName);

        // Extract division data
        JsonNode embeddingNode = division.path("embedding");
        System.out.println("Division " + divisionIndex + " embedding check: missing=" + embeddingNode.isMissingNode() +
                          ", isArray=" + embeddingNode.isArray() +
                          ", size=" + (embeddingNode.isArray() ? embeddingNode.size() : 0));

        if (!embeddingNode.isMissingNode() && embeddingNode.isArray()) {
            // Store division embedding
            String documentId = String.format("n%d_d%d", infolegId, division.path("id").asInt());
            System.out.println("Attempting to store division: " + documentId);

            List<Double> embedding = new ArrayList<>();
            for (JsonNode embeddingValue : embeddingNode) {
                embedding.add(embeddingValue.asDouble());
            }

            Map<String, Object> metadata = createDocumentMetadata(
                    DIVISION, division.path("id").asInt(),
                    source, infolegId,
                    tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario);


            VectorStoreService.StoreResult result = vectorStore.storeDocument(documentId, embedding, metadata);
            if (result.isSuccess()) {
                documentCount.incrementAndGet();
                System.out.println("Stored division: " + documentId);
            } else {
                System.err.println("Failed to store division " + documentId + ": " + result.getMessage());
                errors.add("Division " + documentId + ": " + result.getMessage());
            }
        } else {
            System.out.println("Skipping division " + divisionIndex + " (" + divisionName + ") - no valid embedding");
        }

        // Process articles in this division
        JsonNode articlesNode = division.path("articles");
        if (!articlesNode.isMissingNode() && articlesNode.isArray()) {
            processArticles(articlesNode, infolegId, tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario, source, divisionIndex, documentCount, errors);
        }

        // Process nested divisions recursively
        JsonNode nestedDivisionsNode = division.path("divisions");
        if (!nestedDivisionsNode.isMissingNode() && nestedDivisionsNode.isArray()) {
            processDivisions(nestedDivisionsNode, infolegId, tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario, source, documentCount, errors);
        }
    }

    private void processArticles(JsonNode articlesArray, Integer infolegId, String tipoNorma,
                                String jurisdiccion, String fechaDeSancion, Integer nroBoletin, String tituloSumario, String source, int divisionIndex,
                                AtomicInteger documentCount, List<String> errors) {
        for (int i = 0; i < articlesArray.size(); i++) {
            JsonNode article = articlesArray.get(i);

            JsonNode embeddingNode = article.path("embedding");
            if (!embeddingNode.isMissingNode() && embeddingNode.isArray()) {
                String documentId = String.format("n%d_a%d",
                        infolegId,
                        article.path("id").asInt());

                List<Double> embedding = new ArrayList<>();
                for (JsonNode embeddingValue : embeddingNode) {
                    embedding.add(embeddingValue.asDouble());
                }

                Map<String, Object> metadata = createDocumentMetadata(
                        ARTICLE, article.path("id").asInt(),
                        source, infolegId,
                        tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario);

                VectorStoreService.StoreResult result = vectorStore.storeDocument(documentId, embedding, metadata);
                if (result.isSuccess()) {
                    documentCount.incrementAndGet();
                    System.out.println("Stored article: " + documentId);
                } else {
                    errors.add("Article " + documentId + ": " + result.getMessage());
                }
            }

            JsonNode articlesNode = article.path("articles");
            if (!articlesNode.isMissingNode() && articlesNode.isArray()) {
                processArticles(articlesNode, infolegId, tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario, source, divisionIndex, documentCount, errors);
            }
        }
    }

    private Map<String, Object> createDocumentMetadata(
            String documentType, Integer documentId,
            String source, Integer sourceId,
            String tipoNorma,
            String jurisdiccion, String fechaDeSancion,
            Integer nroBoletin, String tituloSumario
    ) {
        Map<String, Object> metadata = new HashMap<>();

        // Basic norm identification
        metadata.put("source", source);
        metadata.put("source_id", sourceId);
        metadata.put("document_type", documentType);
        metadata.put("document_id", documentId);

        // Filters
        metadata.put("tipo_norma", tipoNorma);
        metadata.put("jurisdiccion", jurisdiccion);
        metadata.put("fecha_de_sancion", fechaDeSancion);
        metadata.put("nro_boletin", nroBoletin);
        metadata.put("titulo_sumario", tituloSumario);

        return metadata;
    }


    private void sendErrorResponse(StreamObserver<StoreResponse> responseObserver, String errorMessage) {
        StoreResponse response = StoreResponse.newBuilder()
                .setSuccess(false)
                .setMessage(errorMessage)
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    /**
     * Get the vector store instance for external access (e.g., for shutdown)
     * @return the vector store service
     */
    public VectorStoreService getVectorStore() {
        return vectorStore;
    }

    @Override
    public void search(SearchRequest request, StreamObserver<SearchResponse> responseObserver) {
        System.out.println("Search method called with " + request.getEmbeddingCount() + " embedding dimensions and " +
                          request.getFiltersCount() + " filters");

        try {
            // First check if the vector store is healthy
            if (!vectorStore.isHealthy()) {
                System.err.println("Vector store is not healthy");
                sendSearchErrorResponse(responseObserver, "Vector store is not healthy");
                return;
            }

            // Extract query embedding from request
            List<Double> queryEmbedding = new ArrayList<>();
            for (double value : request.getEmbeddingList()) {
                queryEmbedding.add(value);
            }

            // Extract filters from request
            Map<String, String> filters = new HashMap<>(request.getFiltersMap());

            // Get limit (default to 10 if not provided or invalid)
            int limit = request.getLimit() > 0 ? request.getLimit() : 10;

            System.out.println("Executing search with " + queryEmbedding.size() + " dimensions, " +
                             filters.size() + " filters, limit: " + limit);

            // Execute the search
            VectorStoreService.SearchResult searchResult = vectorStore.searchDocuments(queryEmbedding, filters, limit);

            if (searchResult.isSuccess()) {
                // Convert search results to protobuf format
                SearchResponse.Builder responseBuilder = SearchResponse.newBuilder()
                        .setSuccess(true)
                        .setMessage(searchResult.getMessage());

                for (VectorStoreService.SearchResult.DocumentMatch match : searchResult.getMatches()) {
                    SearchResult.Builder resultBuilder = SearchResult.newBuilder()
                            .setDocumentId(match.getDocumentId())
                            .setScore(match.getScore());

                    // Add metadata to the result
                    for (Map.Entry<String, Object> metadataEntry : match.getMetadata().entrySet()) {
                        resultBuilder.putMetadata(metadataEntry.getKey(), String.valueOf(metadataEntry.getValue()));
                    }

                    responseBuilder.addResults(resultBuilder.build());
                }

                SearchResponse response = responseBuilder.build();
                System.out.println("Search completed successfully, returning " + response.getResultsCount() + " results");

                responseObserver.onNext(response);
                responseObserver.onCompleted();

            } else {
                sendSearchErrorResponse(responseObserver, searchResult.getMessage());
            }

        } catch (Exception e) {
            String errorMessage = "Error processing vectorial search request: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            sendSearchErrorResponse(responseObserver, errorMessage);
        }
    }

    private void sendSearchErrorResponse(StreamObserver<SearchResponse> responseObserver, String errorMessage) {
        SearchResponse response = SearchResponse.newBuilder()
                .setSuccess(false)
                .setMessage(errorMessage)
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    /**
     * Shutdown the vector store gracefully
     */
    public void shutdown() {
        if (vectorStore != null) {
            try {
                vectorStore.shutdown();
                System.out.println("VectorialService vector store shut down successfully");
            } catch (Exception e) {
                System.err.println("Error shutting down vector store: " + e.getMessage());
                e.printStackTrace();
            }
        }
    }
}