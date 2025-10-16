package com.simpla.vectorial.processor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.simpla.vectorial.dto.SearchRequestDTO;
import com.simpla.vectorial.dto.SearchResponseDTO;
import com.simpla.vectorial.dto.StoreResponseDTO;
import com.simpla.vectorial.service.VectorStoreService;
import com.simpla.vectorial.service.VectorStoreFactory;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

/**
 * Core business logic for vectorial document processing.
 * This class is transport-agnostic and can be used by gRPC, REST, or any other interface.
 */
public class VectorialProcessor {

    private static final String DIVISION = "division";
    private static final String ARTICLE = "article";
    private static final String SUMMARIZED_TEXT = "summarized_text";

    private final VectorStoreService vectorStore;
    private final ObjectMapper objectMapper;

    public VectorialProcessor() {
        this.vectorStore = VectorStoreFactory.createVectorStore();
        this.objectMapper = new ObjectMapper();

        // Initialize the vector store
        try {
            vectorStore.initialize();
            System.out.println("VectorialProcessor initialized with " + vectorStore.getStoreType() +
                    " vector store (index: " + vectorStore.getIndexName() + ")");
        } catch (Exception e) {
            System.err.println("Failed to initialize vector store: " + e.getMessage());
            throw new RuntimeException("Vector store initialization failed", e);
        }
    }

    /**
     * Process and store a document with its embeddings
     */
    public StoreResponseDTO processStore(String jsonData) {
        System.out.println("Processing store request with data length: " + jsonData.length());

        try {
            // Check if the vector store is healthy
            if (!vectorStore.isHealthy()) {
                System.err.println("Vector store is not healthy");
                return new StoreResponseDTO(false, "Vector store is not healthy", 0);
            }

            // Parse the incoming data
            JsonNode rootNode = objectMapper.readTree(jsonData);

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
                    return new StoreResponseDTO(false,
                            "Invalid data format: neither 'scraping_data' nor 'data.norma' field found", 0);
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

                // Process summarized_text_embedding if present
                JsonNode summarizedTextEmbedding = normaNode.path("summarized_text_embedding");
                if (!summarizedTextEmbedding.isMissingNode() && summarizedTextEmbedding.isArray()) {
                    processSummarizedTextEmbedding(summarizedTextEmbedding, infolegId, tipoNorma,
                            jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario,
                            "texto_resumido", documentCount, errors);
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

            return new StoreResponseDTO(success, message, documentCount.get());

        } catch (Exception e) {
            String errorMessage = "Error processing vectorial store request: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            return new StoreResponseDTO(false, errorMessage, 0);
        }
    }

    /**
     * Process a search request
     */
    public SearchResponseDTO processSearch(SearchRequestDTO request) {
        System.out.println("Processing search with " + request.getEmbedding().size() + " embedding dimensions and " +
                request.getFilters().size() + " filters");

        try {
            // Check if the vector store is healthy
            if (!vectorStore.isHealthy()) {
                System.err.println("Vector store is not healthy");
                return new SearchResponseDTO(false, "Vector store is not healthy", Collections.emptyList());
            }

            // Get limit (default to 10 if not provided or invalid)
            int limit = request.getLimit() > 0 ? request.getLimit() : 10;

            System.out.println("Executing search with " + request.getEmbedding().size() + " dimensions, " +
                    request.getFilters().size() + " filters, limit: " + limit);

            // Execute the search
            VectorStoreService.SearchResult searchResult = vectorStore.searchDocuments(
                    request.getEmbedding(),
                    request.getFilters(),
                    limit);

            if (searchResult.isSuccess()) {
                // Convert to DTO
                List<SearchResponseDTO.DocumentMatch> matches = searchResult.getMatches().stream()
                        .map(match -> new SearchResponseDTO.DocumentMatch(
                                match.getDocumentId(),
                                match.getScore(),
                                match.getMetadata()))
                        .collect(Collectors.toList());

                System.out.println("Search completed successfully, returning " + matches.size() + " results");
                return new SearchResponseDTO(true, searchResult.getMessage(), matches);
            } else {
                return new SearchResponseDTO(false, searchResult.getMessage(), Collections.emptyList());
            }

        } catch (Exception e) {
            String errorMessage = "Error processing vectorial search request: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            return new SearchResponseDTO(false, errorMessage, Collections.emptyList());
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

        if (embeddingNode.isMissingNode() || !embeddingNode.isArray()) {
            System.out.println("Skipping division " + divisionIndex + " (" + divisionName + ") - no valid embedding");
        } else {
            // Store division embedding
            String documentId = String.format("n%d_d%d", infolegId, division.path("id").asInt());
            System.out.println("Attempting to store division: " + documentId);

            List<Double> embedding = extractEmbedding(embeddingNode);

            Map<String, Object> metadata = createDocumentMetadata(
                    DIVISION, division.path("id").asInt(),
                    source, infolegId,
                    tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario);

            storeDocumentAndTrack(documentId, embedding, metadata, DIVISION, documentCount, errors);
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
            if (embeddingNode.isMissingNode() || !embeddingNode.isArray()) {
                continue;
            }

            String documentId = String.format("n%d_a%d",
                    infolegId,
                    article.path("id").asInt());

            List<Double> embedding = extractEmbedding(embeddingNode);

            Map<String, Object> metadata = createDocumentMetadata(
                    ARTICLE, article.path("id").asInt(),
                    source, infolegId,
                    tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario);

            storeDocumentAndTrack(documentId, embedding, metadata, ARTICLE, documentCount, errors);

            JsonNode articlesNode = article.path("articles");
            if (!articlesNode.isMissingNode() && articlesNode.isArray()) {
                processArticles(articlesNode, infolegId, tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario, source, divisionIndex, documentCount, errors);
            }
        }
    }

    private void processSummarizedTextEmbedding(JsonNode embeddingNode, Integer infolegId, String tipoNorma,
                                                String jurisdiccion, String fechaDeSancion, Integer nroBoletin,
                                                String tituloSumario, String source, AtomicInteger documentCount,
                                                List<String> errors) {
        System.out.println("Processing summarized_text_embedding for norma: " + infolegId);

        if (!embeddingNode.isArray() || embeddingNode.isEmpty()) {
            System.out.println("Skipping summarized text embedding for norma " + infolegId + " - no valid embedding");
            return;
        }

        List<Double> embedding = extractEmbedding(embeddingNode);

        String documentId = String.format("n%d_summarized", infolegId);
        System.out.println("Attempting to store summarized text embedding: " + documentId);

        Map<String, Object> metadata = createDocumentMetadata(
                SUMMARIZED_TEXT, infolegId,
                source, infolegId,
                tipoNorma, jurisdiccion, fechaDeSancion, nroBoletin, tituloSumario);

        storeDocumentAndTrack(documentId, embedding, metadata, SUMMARIZED_TEXT, documentCount, errors);
    }

    private List<Double> extractEmbedding(JsonNode embeddingNode) {
        List<Double> embedding = new ArrayList<>();
        for (JsonNode embeddingValue : embeddingNode) {
            embedding.add(embeddingValue.asDouble());
        }
        return embedding;
    }

    private void storeDocumentAndTrack(String documentId, List<Double> embedding, Map<String, Object> metadata,
                                       String documentType, AtomicInteger documentCount, List<String> errors) {
        VectorStoreService.StoreResult result = vectorStore.storeDocument(documentId, embedding, metadata);
        if (result.isSuccess()) {
            documentCount.incrementAndGet();
            System.out.println("Stored " + documentType + ": " + documentId);
        } else {
            String errorMsg = documentType + " " + documentId + ": " + result.getMessage();
            System.err.println("Failed to store " + errorMsg);
            errors.add(errorMsg);
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
        metadata.put("source_id", String.valueOf(sourceId));
        metadata.put("document_type", documentType);
        metadata.put("document_id", String.valueOf(documentId));

        // Filters
        metadata.put("tipo_norma", tipoNorma);
        metadata.put("jurisdiccion", jurisdiccion);
        metadata.put("fecha_de_sancion", fechaDeSancion);
        metadata.put("nro_boletin", nroBoletin);
        metadata.put("titulo_sumario", tituloSumario);

        return metadata;
    }

    public VectorStoreService getVectorStore() {
        return vectorStore;
    }

    public void shutdown() {
        if (vectorStore != null) {
            try {
                vectorStore.shutdown();
                System.out.println("VectorialProcessor vector store shut down successfully");
            } catch (Exception e) {
                System.err.println("Error shutting down vector store: " + e.getMessage());
                e.printStackTrace();
            }
        }
    }
}
