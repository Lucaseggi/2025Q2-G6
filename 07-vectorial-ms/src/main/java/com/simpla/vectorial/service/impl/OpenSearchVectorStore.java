package com.simpla.vectorial.service.impl;

import com.simpla.vectorial.service.VectorStoreService;
import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.opensearch.action.admin.cluster.health.ClusterHealthRequest;
import org.opensearch.action.admin.cluster.health.ClusterHealthResponse;
import org.opensearch.client.indices.CreateIndexRequest;
import org.opensearch.client.indices.CreateIndexResponse;
import org.opensearch.client.indices.GetIndexRequest;
import org.opensearch.action.support.master.AcknowledgedResponse;
import org.opensearch.action.index.IndexRequest;
import org.opensearch.action.index.IndexResponse;
import org.opensearch.action.search.SearchRequest;
import org.opensearch.action.search.SearchResponse;
import org.opensearch.client.RequestOptions;
import org.opensearch.client.RestClient;
import org.opensearch.client.RestClientBuilder;
import org.opensearch.client.RestHighLevelClient;
import org.opensearch.common.xcontent.XContentType;
import org.opensearch.index.query.QueryBuilders;
import org.opensearch.index.query.BoolQueryBuilder;
import org.opensearch.index.query.TermQueryBuilder;
import org.opensearch.search.builder.SearchSourceBuilder;
import org.opensearch.search.SearchHit;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.ArrayList;

public class OpenSearchVectorStore implements VectorStoreService {

    private RestHighLevelClient client;
    private String host;
    private int port;
    private String scheme;
    private String indexName;
    private String username;
    private String password;

    public OpenSearchVectorStore() {
        // Load configuration from environment variables
        loadConfiguration();
    }

    private void loadConfiguration() {
        host = System.getenv("OPENSEARCH_HOST");
        String portStr = System.getenv("OPENSEARCH_PORT");
        scheme = System.getenv("OPENSEARCH_SCHEME");
        indexName = System.getenv("OPENSEARCH_INDEX");
        username = System.getenv("OPENSEARCH_USERNAME");
        password = System.getenv("OPENSEARCH_PASSWORD");

        // Set defaults if environment variables are not provided
        host = host != null ? host : "opensearch";
        port = portStr != null ? Integer.parseInt(portStr) : 9200;
        scheme = scheme != null ? scheme : "http";
        indexName = indexName != null ? indexName : "documents";
        // username and password can be null for development (no auth)

        System.out.println("OpenSearch configuration loaded:");
        System.out.println("  Host: " + host);
        System.out.println("  Port: " + port);
        System.out.println("  Scheme: " + scheme);
        System.out.println("  Index: " + indexName);
        System.out.println("  Authentication: " + (username != null && !username.trim().isEmpty() ? "enabled" : "disabled"));
    }

    @Override
    public void initialize() {
        try {
            RestClientBuilder builder = RestClient.builder(new HttpHost(host, port, scheme));

            // Add authentication if provided
            if (username != null && !username.trim().isEmpty() && password != null && !password.trim().isEmpty()) {
                CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
                credentialsProvider.setCredentials(
                    AuthScope.ANY,
                    new UsernamePasswordCredentials(username, password)
                );

                builder.setHttpClientConfigCallback(httpClientBuilder ->
                    httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider)
                );
            }

            client = new RestHighLevelClient(builder);
            System.out.println("OpenSearch client initialized successfully");

            // Ensure the index exists with proper knn_vector mapping
            ensureIndexExists();

        } catch (Exception e) {
            System.err.println("Failed to initialize OpenSearch client: " + e.getMessage());
            e.printStackTrace();
            throw new RuntimeException("OpenSearch initialization failed", e);
        }
    }

    @Override
    public long getDocumentCount() {
        try {
            SearchRequest searchRequest = new SearchRequest(indexName);
            SearchSourceBuilder searchSourceBuilder = new SearchSourceBuilder();
            searchSourceBuilder.query(QueryBuilders.matchAllQuery());
            searchSourceBuilder.size(0); // We only want the count, not the documents
            searchRequest.source(searchSourceBuilder);

            SearchResponse searchResponse = client.search(searchRequest, RequestOptions.DEFAULT);
            long totalHits = searchResponse.getHits().getTotalHits().value;

            System.out.println("OpenSearch document count query executed successfully");
            return totalHits;

        } catch (Exception e) {
            System.err.println("Failed to get document count from OpenSearch: " + e.getMessage());
            e.printStackTrace();
            return -1;
        }
    }

    @Override
    public boolean isHealthy() {
        try {
            ClusterHealthRequest request = new ClusterHealthRequest();
            ClusterHealthResponse response = client.cluster().health(request, RequestOptions.DEFAULT);

            boolean isHealthy = !response.isTimedOut() &&
                               (response.getStatus().equals(org.opensearch.cluster.health.ClusterHealthStatus.GREEN) ||
                                response.getStatus().equals(org.opensearch.cluster.health.ClusterHealthStatus.YELLOW));

            System.out.println("OpenSearch health check: " +
                             (isHealthy ? "healthy" : "unhealthy") +
                             " (status: " + response.getStatus() + ")");
            return isHealthy;

        } catch (Exception e) {
            System.err.println("OpenSearch health check failed: " + e.getMessage());
            return false;
        }
    }

    @Override
    public String getStoreType() {
        return "OpenSearch";
    }

    @Override
    public String getIndexName() {
        return indexName;
    }

    @Override
    public StoreResult storeDocument(String documentId, List<Double> embedding, Map<String, Object> metadata) {
        try {
            // Create the document structure for OpenSearch
            Map<String, Object> document = new HashMap<>();
            document.put("embedding", embedding);
            document.putAll(metadata);

            // Create index request
            IndexRequest request = new IndexRequest(indexName)
                .id(documentId)
                .source(document, XContentType.JSON);

            // Execute the indexing request
            IndexResponse response = client.index(request, RequestOptions.DEFAULT);

            System.out.println("Document stored successfully: " + documentId +
                             " (result: " + response.getResult() + ")");

            return new StoreResult(true,
                "Document stored successfully with result: " + response.getResult(),
                documentId);

        } catch (Exception e) {
            String errorMessage = "Failed to store document " + documentId + ": " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            return new StoreResult(false, errorMessage, documentId);
        }
    }

    @Override
    public SearchResult searchDocuments(List<Double> queryEmbedding, Map<String, String> filters, int limit) {
        try {
            SearchRequest searchRequest = new SearchRequest(indexName);
            SearchSourceBuilder searchSourceBuilder = new SearchSourceBuilder();

            // Build k-NN query JSON manually for OpenSearch
            StringBuilder knnQueryJson = new StringBuilder();
            knnQueryJson.append("{\"knn\": {\"embedding\": {");
            knnQueryJson.append("\"vector\": [");
            for (int i = 0; i < queryEmbedding.size(); i++) {
                if (i > 0) knnQueryJson.append(",");
                knnQueryJson.append(queryEmbedding.get(i));
            }
            knnQueryJson.append("], \"k\": ").append(limit);

            // Add metadata filters if provided
            if (filters != null && !filters.isEmpty()) {
                knnQueryJson.append(", \"filter\": {\"bool\": {\"must\": [");
                boolean first = true;
                for (Map.Entry<String, String> filter : filters.entrySet()) {
                    if (!first) knnQueryJson.append(",");
                    knnQueryJson.append("{\"term\": {\"").append(filter.getKey()).append("\": \"").append(filter.getValue()).append("\"}}");
                    first = false;
                }
                knnQueryJson.append("]}}");
            }

            knnQueryJson.append("}}}");

            // Set the query using wrapper query
            searchSourceBuilder.query(QueryBuilders.wrapperQuery(knnQueryJson.toString()));

            searchSourceBuilder.size(limit);
            searchRequest.source(searchSourceBuilder);

            // Execute the search
            SearchResponse searchResponse = client.search(searchRequest, RequestOptions.DEFAULT);

            // Process search results
            List<VectorStoreService.SearchResult.DocumentMatch> matches = new ArrayList<>();
            for (SearchHit hit : searchResponse.getHits().getHits()) {
                String documentId = hit.getId();
                double score = hit.getScore();
                Map<String, Object> metadata = new HashMap<>(hit.getSourceAsMap());

                // Remove the embedding from metadata to keep response lean
                metadata.remove("embedding");

                matches.add(new VectorStoreService.SearchResult.DocumentMatch(documentId, score, metadata));
            }

            System.out.println("Search executed successfully. Found " + matches.size() + " matches out of " +
                             searchResponse.getHits().getTotalHits().value + " total documents");

            return new SearchResult(true,
                "Search completed successfully. Found " + matches.size() + " matches",
                matches);

        } catch (Exception e) {
            String errorMessage = "Failed to execute search: " + e.getMessage();
            System.err.println(errorMessage);
            e.printStackTrace();
            return new SearchResult(false, errorMessage, new ArrayList<>());
        }
    }

    private void ensureIndexExists() {
        try {
            // Check if index exists
            GetIndexRequest existsRequest = new GetIndexRequest(indexName);
            boolean indexExists = client.indices().exists(existsRequest, RequestOptions.DEFAULT);

            if (!indexExists) {
                System.out.println("Index '" + indexName + "' does not exist. Creating with proper knn_vector mapping...");
                createIndexWithKnnMapping();
            } else {
                System.out.println("Index '" + indexName + "' already exists");
            }

        } catch (Exception e) {
            System.err.println("Failed to check/create index: " + e.getMessage());
            e.printStackTrace();
            throw new RuntimeException("Index initialization failed", e);
        }
    }

    private void createIndexWithKnnMapping() {
        try {
            String indexMapping = """
                {
                  "settings": {
                    "index": {
                      "knn": true,
                      "knn.algo_param.ef_search": 100
                    }
                  },
                  "mappings": {
                    "properties": {
                      "embedding": {
                        "type": "knn_vector",
                        "dimension": 768,
                        "method": {
                          "name": "hnsw",
                          "space_type": "cosinesimil",
                          "engine": "lucene",
                          "parameters": {
                            "ef_construction": 128,
                            "m": 24
                          }
                        }
                      },
                      "infoleg_id": {"type": "long"},
                      "tipo_norma": {"type": "keyword"},
                      "jurisdiccion": {"type": "keyword"},
                      "source": {"type": "keyword"},
                      "document_type": {"type": "keyword"},
                      "division_index": {"type": "long"},
                      "article_index": {"type": "long"},
                      "division_name": {"type": "text"},
                      "division_ordinal": {"type": "keyword"},
                      "division_title": {"type": "text"},
                      "article_ordinal": {"type": "keyword"},
                      "division_order": {"type": "long"},
                      "article_order": {"type": "long"}
                    }
                  }
                }
                """;

            CreateIndexRequest createRequest = new CreateIndexRequest(indexName);
            createRequest.source(indexMapping, org.opensearch.common.xcontent.XContentType.JSON);

            CreateIndexResponse createResponse = client.indices().create(createRequest, RequestOptions.DEFAULT);

            if (createResponse.isAcknowledged()) {
                System.out.println("Index '" + indexName + "' created successfully with knn_vector mapping");
            } else {
                throw new RuntimeException("Index creation was not acknowledged");
            }

        } catch (Exception e) {
            System.err.println("Failed to create index with knn mapping: " + e.getMessage());
            e.printStackTrace();
            throw new RuntimeException("Index creation failed", e);
        }
    }

    @Override
    public void shutdown() {
        if (client != null) {
            try {
                client.close();
                System.out.println("OpenSearch client closed successfully");
            } catch (Exception e) {
                System.err.println("Error closing OpenSearch client: " + e.getMessage());
                e.printStackTrace();
            }
        }
    }
}