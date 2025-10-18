package com.simpla.relational.processor;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.simpla.relational.dto.GetBatchResponseDTO;
import com.simpla.relational.dto.ReconstructNormResponseDTO;
import com.simpla.relational.dto.StoreResponseDTO;
import com.simpla.relational.model.Article;
import com.simpla.relational.model.Division;
import com.simpla.relational.model.Norma;
import com.simpla.relational.model.NormaBatchData;
import com.simpla.relational.repository.NormaRepository;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import java.sql.SQLException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Core business logic for relational document processing.
 * This class is transport-agnostic and can be used by gRPC, REST, or any other interface.
 */
public class RelationalProcessor {

    private final HikariDataSource dataSource;
    private final NormaRepository normaRepository;
    private final ObjectMapper objectMapper;

    public RelationalProcessor() {
        this.dataSource = initializeDataSource();
        this.normaRepository = new NormaRepository(dataSource);
        this.objectMapper = initializeObjectMapper();

        System.out.println("RelationalProcessor initialized");
    }

    private HikariDataSource initializeDataSource() {
        HikariConfig config = new HikariConfig();

        String dbHost = getEnvOrDefault("POSTGRES_HOST", "postgres");
        String dbPort = getEnvOrDefault("POSTGRES_PORT", "5432");
        String dbName = getEnvOrDefault("POSTGRES_DB", "simpla_rag");
        String dbUser = getEnvOrDefault("POSTGRES_USER", "postgres");
        String dbPassword = getEnvOrDefault("POSTGRES_PASSWORD", "postgres123");

        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", dbHost, dbPort, dbName);

        config.setJdbcUrl(jdbcUrl);
        config.setUsername(dbUser);
        config.setPassword(dbPassword);
        config.setMaximumPoolSize(10);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);

        System.out.println("Database connection pool initialized with URL: " + jdbcUrl);

        return new HikariDataSource(config);
    }

    private ObjectMapper initializeObjectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        // Register JavaTimeModule FIRST before any configuration
        mapper.registerModule(new JavaTimeModule());

        // Serialize dates as ISO strings instead of arrays
        mapper.configure(com.fasterxml.jackson.databind.SerializationFeature.WRITE_DATES_AS_TIMESTAMPS, false);

        mapper.configure(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
        return mapper;
    }

    private String getEnvOrDefault(String key, String defaultValue) {
        String value = System.getenv(key);
        return value != null ? value : defaultValue;
    }

    /**
     * Process and store a norma document
     */
    public StoreResponseDTO processStore(String jsonData) {
        System.out.println("Processing store request with data length: " + jsonData.length());

        try {
            Norma norma = parseNormaFromRequest(jsonData);

            System.out.println("Storing norma with infoleg_id: " + norma.getInfolegId());

            // Insert the complete norma with all its divisions and articles, capturing PKs
            NormaRepository.InsertionResult insertionResult =
                normaRepository.insertCompleteNormaWithPks(norma);

            System.out.println("Successfully stored norma with database ID: " + insertionResult.getNormaId());
            System.out.println("Division PKs: " + insertionResult.getDivisionPks().size());
            System.out.println("Article PKs: " + insertionResult.getArticlePks().size());

            // Convert insertion result to JSON for the vectorial-guard
            String pkMappingJson = objectMapper.writeValueAsString(insertionResult);

            String message = "Norma stored successfully with ID: " + insertionResult.getNormaId() +
                           " (infoleg_id: " + norma.getInfolegId() + ")";

            return new StoreResponseDTO(true, message, pkMappingJson);

        } catch (InvalidDataFormatException e) {
            return new StoreResponseDTO(false, e.getMessage(), null);
        } catch (Exception e) {
            System.err.println("Error storing norma: " + e.getMessage());
            e.printStackTrace();
            return new StoreResponseDTO(false, "Error storing norma: " + e.getMessage(), null);
        }
    }

    /**
     * Reconstruct a norma by infoleg_id
     */
    public ReconstructNormResponseDTO processReconstructByInfolegId(int infolegId) {
        System.out.println("Reconstructing norma with infoleg_id: " + infolegId);

        try {
            Norma norma = normaRepository.findByInfolegId(infolegId);

            if (norma == null) {
                String message = "Norma not found with infoleg_id: " + infolegId;
                return new ReconstructNormResponseDTO(false, message, null);
            }

            // Convert norma to JSON
            String normaJson = objectMapper.writeValueAsString(norma);
            System.out.println("Norma reconstructed successfully, JSON length: " + normaJson.length());

            return new ReconstructNormResponseDTO(true, "Norma reconstructed successfully from database", normaJson);

        } catch (Exception e) {
            System.err.println("Error reconstructing norma: " + e.getMessage());
            e.printStackTrace();
            return new ReconstructNormResponseDTO(false, "Error reconstructing norma: " + e.getMessage(), null);
        }
    }

    /**
     * Reconstruct a norma by database id
     */
    public ReconstructNormResponseDTO processReconstructById(long id) {
        System.out.println("Reconstructing norma with id: " + id);

        try {
            Norma norma = normaRepository.findById(id);

            if (norma == null) {
                String message = "Norma not found with id: " + id;
                return new ReconstructNormResponseDTO(false, message, null);
            }

            // Convert norma to JSON
            String normaJson = objectMapper.writeValueAsString(norma);
            System.out.println("Norma reconstructed successfully, JSON length: " + normaJson.length());

            return new ReconstructNormResponseDTO(true, "Norma reconstructed successfully from database", normaJson);

        } catch (Exception e) {
            System.err.println("Error reconstructing norma: " + e.getMessage());
            e.printStackTrace();
            return new ReconstructNormResponseDTO(false, "Error reconstructing norma: " + e.getMessage(), null);
        }
    }

    /**
     * Get batch of normas based on entity pairs
     */
    public GetBatchResponseDTO processGetBatch(List<EntityPairDTO> entityPairs) {
        System.out.println("Processing getBatch request with " + entityPairs.size() + " entities");

        try {
            List<NormaBatchData> normaBatchDataList = fetchNormasBatch(entityPairs);

            // Convert to JSON
            String normasJson = objectMapper.writeValueAsString(normaBatchDataList);

            System.out.println("Retrieved " + normaBatchDataList.size() + " unique norms");

            String message = "Retrieved " + normaBatchDataList.size() + " unique norms";
            return new GetBatchResponseDTO(true, message, normasJson);

        } catch (Exception e) {
            System.err.println("Error retrieving batch entities: " + e.getMessage());
            e.printStackTrace();
            return new GetBatchResponseDTO(false, "Error retrieving batch entities: " + e.getMessage(), "[]");
        }
    }

    private Norma parseNormaFromRequest(String jsonData) throws Exception {
        JsonNode rootNode = objectMapper.readTree(jsonData);
        JsonNode dataNode = rootNode.path("data");
        JsonNode normaNode = dataNode.path("norma");

        if (normaNode.isMissingNode()) {
            throw new InvalidDataFormatException("Invalid data format: 'norma' field not found");
        }

        return objectMapper.treeToValue(normaNode, Norma.class);
    }

    private List<NormaBatchData> fetchNormasBatch(List<EntityPairDTO> entityPairs) throws SQLException {
        // Map to track which entities belong to which norm
        Map<Long, NormaBatchData> normaMap = new LinkedHashMap<>();

        for (EntityPairDTO entityPair : entityPairs) {
            String type = entityPair.getType();
            long entityId = entityPair.getId();

            System.out.println("Processing entity: type=" + type + ", id=" + entityId);

            Long normaId = null;

            if ("division".equalsIgnoreCase(type)) {
                normaId = normaRepository.findNormaIdByDivisionId(entityId);
                if (normaId != null) {
                    NormaBatchData normaBatchData = normaMap.computeIfAbsent(normaId, k -> new NormaBatchData());
                    normaBatchData.addDivisionId(entityId);
                } else {
                    System.out.println("Norma not found for division id: " + entityId);
                }
            } else if ("article".equalsIgnoreCase(type)) {
                normaId = normaRepository.findNormaIdByArticleId(entityId);
                if (normaId != null) {
                    NormaBatchData normaBatchData = normaMap.computeIfAbsent(normaId, k -> new NormaBatchData());
                    normaBatchData.addArticleId(entityId);
                } else {
                    System.out.println("Norma not found for article id: " + entityId);
                }
            } else {
                System.out.println("Unknown entity type: " + type);
            }
        }

        // Fetch norm summaries and requested entities
        List<NormaBatchData> result = new ArrayList<>();
        for (Map.Entry<Long, NormaBatchData> entry : normaMap.entrySet()) {
            Long normaId = entry.getKey();
            NormaBatchData batchData = entry.getValue();

            // Fetch norm batch data (metadata only)
            NormaBatchData normaBatchData = normaRepository.findNormaBatchDataById(normaId);
            if (normaBatchData != null) {
                // Transfer the tracked entity IDs to the fetched batch data
                normaBatchData.setDivisionIds(batchData.getDivisionIds());
                normaBatchData.setArticleIds(batchData.getArticleIds());

                // Fetch requested divisions
                for (Long divisionId : normaBatchData.getDivisionIds()) {
                    Division division = normaRepository.findDivisionById(divisionId);
                    if (division != null) {
                        normaBatchData.addDivision(division);
                    }
                }

                // Fetch requested articles
                for (Long articleId : normaBatchData.getArticleIds()) {
                    Article article = normaRepository.findArticleById(articleId);
                    if (article != null) {
                        normaBatchData.addArticle(article);
                    }
                }

                result.add(normaBatchData);
            } else {
                System.out.println("Norm batch data not found for norma_id: " + normaId);
            }
        }

        return result;
    }

    /**
     * DTO for entity pair (transport-agnostic)
     */
    public static class EntityPairDTO {
        private final String type;
        private final long id;

        public EntityPairDTO(String type, long id) {
            this.type = type;
            this.id = id;
        }

        public String getType() {
            return type;
        }

        public long getId() {
            return id;
        }
    }

    public static class InvalidDataFormatException extends Exception {
        public InvalidDataFormatException(String message) {
            super(message);
        }
    }

    public void shutdown() {
        if (dataSource != null && !dataSource.isClosed()) {
            dataSource.close();
            System.out.println("RelationalProcessor database connection pool closed");
        }
    }
}
