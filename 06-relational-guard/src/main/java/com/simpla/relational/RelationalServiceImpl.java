package com.simpla.relational;

import com.simpla.relational.model.NormaBatchData;
import com.simpla.relational.proto.*;
import com.simpla.relational.model.Norma;
import com.simpla.relational.model.Division;
import com.simpla.relational.model.Article;
import com.simpla.relational.repository.NormaRepository;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import io.grpc.stub.StreamObserver;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import com.fasterxml.jackson.databind.SerializationFeature;

import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

public class RelationalServiceImpl extends RelationalServiceGrpc.RelationalServiceImplBase {

    private final HikariDataSource dataSource;
    private final NormaRepository normaRepository;
    private final ObjectMapper objectMapper;

    public RelationalServiceImpl() {
        this.dataSource = initializeDataSource();
        this.normaRepository = new NormaRepository(dataSource);
        this.objectMapper = initializeObjectMapper();
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

    @Override
    public void store(StoreRequest request, StreamObserver<StoreResponse> responseObserver) {
        System.out.println("Store method called with data length: " + request.getData().length());

        try {
            Norma norma = parseNormaFromRequest(request.getData());

            System.out.println("Storing norma with infoleg_id: " + norma.getInfolegId());

            // Insert the complete norma with all its divisions and articles, capturing PKs
            com.simpla.relational.repository.NormaRepository.InsertionResult insertionResult =
                normaRepository.insertCompleteNormaWithPks(norma);

            System.out.println("Successfully stored norma with database ID: " + insertionResult.getNormaId());
            System.out.println("Division PKs: " + insertionResult.getDivisionPks().size());
            System.out.println("Article PKs: " + insertionResult.getArticlePks().size());

            // Convert insertion result to JSON for the vectorial-guard
            String pkMappingJson = objectMapper.writeValueAsString(insertionResult);

            String message = "Norma stored successfully with ID: " + insertionResult.getNormaId() + " (infoleg_id: " + norma.getInfolegId() + ")";
            sendResponse(responseObserver, buildStoreResponse(true, message, pkMappingJson));

        } catch (InvalidDataFormatException e) {
            sendResponse(responseObserver, buildStoreResponse(false, e.getMessage(), null));
        } catch (Exception e) {
            System.err.println("Error storing norma: " + e.getMessage());
            e.printStackTrace();
            sendResponse(responseObserver, buildStoreResponse(false, "Error storing norma: " + e.getMessage(), null));
        }
    }

    private Norma parseNormaFromRequest(String jsonData) throws Exception {
        com.fasterxml.jackson.databind.JsonNode rootNode = objectMapper.readTree(jsonData);
        com.fasterxml.jackson.databind.JsonNode dataNode = rootNode.path("data");
        com.fasterxml.jackson.databind.JsonNode normaNode = dataNode.path("norma");

        if (normaNode.isMissingNode()) {
            throw new InvalidDataFormatException("Invalid data format: 'norma' field not found");
        }

        return objectMapper.treeToValue(normaNode, Norma.class);
    }

    private static class InvalidDataFormatException extends Exception {
        public InvalidDataFormatException(String message) {
            super(message);
        }
    }

    @Override
    public void reconstructNorm(ReconstructNormRequest request, StreamObserver<ReconstructNormResponse> responseObserver) {
        System.out.println("ReconstructNorm method called with infoleg_id: " + request.getInfolegId());
        reconstructNormInternal(
            () -> normaRepository.findByInfolegId(request.getInfolegId()),
            "infoleg_id: " + request.getInfolegId(),
            responseObserver
        );
    }

    @Override
    public void reconstructNormById(ReconstructNormByIdRequest request, StreamObserver<ReconstructNormResponse> responseObserver) {
        System.out.println("ReconstructNormById method called with id: " + request.getId());
        reconstructNormInternal(
            () -> normaRepository.findById(request.getId()),
            "id: " + request.getId(),
            responseObserver
        );
    }

    private void reconstructNormInternal(
            NormaFetcher fetcher,
            String identifier,
            StreamObserver<ReconstructNormResponse> responseObserver
    ) {
        try {
            Norma norma = fetcher.fetch();

            if (norma == null) {
                sendResponse(responseObserver, buildReconstructNormResponse(false, "Norma not found with " + identifier, null));
                return;
            }

            // Convert norma to JSON
            String normaJson = objectMapper.writeValueAsString(norma);
            System.out.println("Norma reconstructed successfully, JSON length: " + normaJson.length());

            sendResponse(responseObserver, buildReconstructNormResponse(true, "Norma reconstructed successfully from database", normaJson));

        } catch (Exception e) {
            System.err.println("Error reconstructing norma: " + e.getMessage());
            e.printStackTrace();
            sendResponse(responseObserver, buildReconstructNormResponse(false, "Error reconstructing norma: " + e.getMessage(), null));
        }
    }

    private StoreResponse buildStoreResponse(boolean success, String message, String pkMappingJson) {
        StoreResponse.Builder builder = StoreResponse.newBuilder()
                .setSuccess(success)
                .setMessage(message);

        if (pkMappingJson != null) {
            builder.setPkMappingJson(pkMappingJson);
        }

        return builder.build();
    }

    private ReconstructNormResponse buildReconstructNormResponse(boolean success, String message, String normaJson) {
        ReconstructNormResponse.Builder builder = ReconstructNormResponse.newBuilder()
                .setSuccess(success)
                .setMessage(message);

        if (normaJson != null) {
            builder.setNormaJson(normaJson);
        }

        return builder.build();
    }

    private GetBatchResponse buildGetBatchResponse(boolean success, String message, String normasJson) {
        return GetBatchResponse.newBuilder()
                .setSuccess(success)
                .setMessage(message)
                .setNormasJson(normasJson)
                .build();
    }

    private <T> void sendResponse(StreamObserver<T> responseObserver, T response) {
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @FunctionalInterface
    private interface NormaFetcher {
        Norma fetch() throws Exception;
    }

    @Override
    public void getBatch(GetBatchRequest request, StreamObserver<GetBatchResponse> responseObserver) {
        System.out.println("GetBatch method called with " + request.getEntitiesCount() + " entities");

        try {
            List<NormaBatchData> normaBatchDataList = fetchNormasBatch(request.getEntitiesList());

            // Convert to JSON
            String normasJson = objectMapper.writeValueAsString(normaBatchDataList);

            System.out.println("Retrieved " + normaBatchDataList.size() + " unique norms");

            String message = "Retrieved " + normaBatchDataList.size() + " unique norms";
            sendResponse(responseObserver, buildGetBatchResponse(true, message, normasJson));

        } catch (Exception e) {
            System.err.println("Error retrieving batch entities: " + e.getMessage());
            e.printStackTrace();
            sendResponse(responseObserver, buildGetBatchResponse(false, "Error retrieving batch entities: " + e.getMessage(), "[]"));
        }
    }

    private List<NormaBatchData> fetchNormasBatch(List<EntityPair> entityPairs) throws SQLException {
        // Map to track which entities belong to which norm
        java.util.Map<Long, NormaBatchData> normaMap = new java.util.LinkedHashMap<>();

        for (EntityPair entityPair : entityPairs) {
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
        for (java.util.Map.Entry<Long, NormaBatchData> entry : normaMap.entrySet()) {
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

    public void shutdown() {
        if (dataSource != null && !dataSource.isClosed()) {
            dataSource.close();
            System.out.println("Database connection pool closed");
        }
    }
}