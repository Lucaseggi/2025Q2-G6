package com.simpla.relational;

import com.simpla.relational.proto.RelationalServiceGrpc;
import com.simpla.relational.proto.StoreRequest;
import com.simpla.relational.proto.StoreResponse;
import com.simpla.relational.proto.ReconstructNormRequest;
import com.simpla.relational.proto.ReconstructNormResponse;
import com.simpla.relational.proto.GetBatchRequest;
import com.simpla.relational.proto.GetBatchResponse;
import com.simpla.relational.proto.EntityPair;
import com.simpla.relational.model.Norma;
import com.simpla.relational.model.Division;
import com.simpla.relational.model.Article;
import com.simpla.relational.repository.NormaRepository;
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;
import io.grpc.stub.StreamObserver;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

public class RelationalServiceImpl extends RelationalServiceGrpc.RelationalServiceImplBase {

    private final HikariDataSource dataSource;
    private final NormaRepository normaRepository;
    private final ObjectMapper objectMapper;

    public RelationalServiceImpl() {
        // Initialize database connection pool
        HikariConfig config = new HikariConfig();

        String dbHost = System.getenv("POSTGRES_HOST");
        String dbPort = System.getenv("POSTGRES_PORT");
        String dbName = System.getenv("POSTGRES_DB");
        String dbUser = System.getenv("POSTGRES_USER");
        String dbPassword = System.getenv("POSTGRES_PASSWORD");

        // Use defaults if environment variables are not set
        dbHost = dbHost != null ? dbHost : "postgres";
        dbPort = dbPort != null ? dbPort : "5432";
        dbName = dbName != null ? dbName : "simpla_rag";
        dbUser = dbUser != null ? dbUser : "postgres";
        dbPassword = dbPassword != null ? dbPassword : "postgres123";

        String jdbcUrl = String.format("jdbc:postgresql://%s:%s/%s", dbHost, dbPort, dbName);

        config.setJdbcUrl(jdbcUrl);
        config.setUsername(dbUser);
        config.setPassword(dbPassword);
        config.setMaximumPoolSize(10);
        config.setConnectionTimeout(30000);
        config.setIdleTimeout(600000);
        config.setMaxLifetime(1800000);

        this.dataSource = new HikariDataSource(config);
        this.normaRepository = new NormaRepository(dataSource);
        this.objectMapper = new ObjectMapper();
        this.objectMapper.registerModule(new JavaTimeModule());
        this.objectMapper.configure(com.fasterxml.jackson.databind.DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);

        System.out.println("Database connection pool initialized with URL: " + jdbcUrl);
    }

    @Override
    public void store(StoreRequest request, StreamObserver<StoreResponse> responseObserver) {
        System.out.println("Store method called with data length: " + request.getData().length());

        try {
            // Parse the JSON data to extract the norma
            String jsonData = request.getData();

            // Parse JSON to extract norma data
            com.fasterxml.jackson.databind.JsonNode rootNode = objectMapper.readTree(jsonData);
            com.fasterxml.jackson.databind.JsonNode dataNode = rootNode.path("data");
            com.fasterxml.jackson.databind.JsonNode normaNode = dataNode.path("norma");

            if (normaNode.isMissingNode()) {
                StoreResponse response = StoreResponse.newBuilder()
                        .setSuccess(false)
                        .setMessage("Invalid data format: 'norma' field not found")
                        .build();

                responseObserver.onNext(response);
                responseObserver.onCompleted();
                return;
            }

            // Convert the norma node to Norma object
            Norma norma = objectMapper.treeToValue(normaNode, Norma.class);

            System.out.println("Storing norma with infoleg_id: " + norma.getInfolegId());

            // Insert the complete norma with all its divisions and articles, capturing PKs
            com.simpla.relational.repository.NormaRepository.InsertionResult insertionResult =
                normaRepository.insertCompleteNormaWithPks(norma);

            System.out.println("Successfully stored norma with database ID: " + insertionResult.getNormaId());
            System.out.println("Division PKs: " + insertionResult.getDivisionPks().size());
            System.out.println("Article PKs: " + insertionResult.getArticlePks().size());

            // Convert insertion result to JSON for the vectorial-ms
            String pkMappingJson = objectMapper.writeValueAsString(insertionResult);

            StoreResponse response = StoreResponse.newBuilder()
                    .setSuccess(true)
                    .setMessage("Norma stored successfully with ID: " + insertionResult.getNormaId() + " (infoleg_id: " + norma.getInfolegId() + ")")
                    .setPkMappingJson(pkMappingJson)
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();

        } catch (Exception e) {
            System.err.println("Error storing norma: " + e.getMessage());
            e.printStackTrace();

            StoreResponse response = StoreResponse.newBuilder()
                    .setSuccess(false)
                    .setMessage("Error storing norma: " + e.getMessage())
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        }
    }

    @Override
    public void reconstructNorm(ReconstructNormRequest request, StreamObserver<ReconstructNormResponse> responseObserver) {
        System.out.println("ReconstructNorm method called with infoleg_id: " + request.getInfolegId());

        try {
            // Find norma by infoleg_id
            Norma norma = normaRepository.findByInfolegId(request.getInfolegId());

            if (norma == null) {
                ReconstructNormResponse response = ReconstructNormResponse.newBuilder()
                        .setSuccess(false)
                        .setMessage("Norma not found with infoleg_id: " + request.getInfolegId())
                        .build();

                responseObserver.onNext(response);
                responseObserver.onCompleted();
                return;
            }

            // Convert norma to JSON
            String normaJson = objectMapper.writeValueAsString(norma);
            System.out.println("Norma reconstructed successfully, JSON length: " + normaJson.length());

            ReconstructNormResponse response = ReconstructNormResponse.newBuilder()
                    .setSuccess(true)
                    .setMessage("Norma reconstructed successfully from database")
                    .setNormaJson(normaJson)
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();

        } catch (Exception e) {
            System.err.println("Error reconstructing norma: " + e.getMessage());
            e.printStackTrace();

            ReconstructNormResponse response = ReconstructNormResponse.newBuilder()
                    .setSuccess(false)
                    .setMessage("Error reconstructing norma: " + e.getMessage())
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        }
    }

    @Override
    public void getBatch(GetBatchRequest request, StreamObserver<GetBatchResponse> responseObserver) {
        System.out.println("GetBatch method called with " + request.getEntitiesCount() + " entities");

        try {
            List<Division> divisions = new ArrayList<>();
            List<Article> articles = new ArrayList<>();

            // Process each entity pair
            for (EntityPair entityPair : request.getEntitiesList()) {
                String type = entityPair.getType();
                long id = entityPair.getId();

                System.out.println("Processing entity: type=" + type + ", id=" + id);

                if ("division".equalsIgnoreCase(type)) {
                    Division division = normaRepository.findDivisionById(id);
                    if (division != null) {
                        divisions.add(division);
                    } else {
                        System.out.println("Division not found with id: " + id);
                    }
                } else if ("article".equalsIgnoreCase(type)) {
                    Article article = normaRepository.findArticleById(id);
                    if (article != null) {
                        articles.add(article);
                    } else {
                        System.out.println("Article not found with id: " + id);
                    }
                } else {
                    System.out.println("Unknown entity type: " + type);
                }
            }

            // Convert to JSON
            String divisionsJson = objectMapper.writeValueAsString(divisions);
            String articlesJson = objectMapper.writeValueAsString(articles);

            System.out.println("Retrieved " + divisions.size() + " divisions and " + articles.size() + " articles");

            GetBatchResponse response = GetBatchResponse.newBuilder()
                    .setSuccess(true)
                    .setMessage("Retrieved " + divisions.size() + " divisions and " + articles.size() + " articles")
                    .setDivisionsJson(divisionsJson)
                    .setArticlesJson(articlesJson)
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();

        } catch (Exception e) {
            System.err.println("Error retrieving batch entities: " + e.getMessage());
            e.printStackTrace();

            GetBatchResponse response = GetBatchResponse.newBuilder()
                    .setSuccess(false)
                    .setMessage("Error retrieving batch entities: " + e.getMessage())
                    .setDivisionsJson("[]")
                    .setArticlesJson("[]")
                    .build();

            responseObserver.onNext(response);
            responseObserver.onCompleted();
        }
    }

    private int getArticlesCount() throws SQLException {
        String sql = "SELECT COUNT(*) FROM articles";

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {

            if (rs.next()) {
                return rs.getInt(1);
            }
            return 0;
        }
    }

    public void shutdown() {
        if (dataSource != null && !dataSource.isClosed()) {
            dataSource.close();
            System.out.println("Database connection pool closed");
        }
    }
}