package com.simpla.vectorial;

import com.simpla.vectorial.dto.SearchRequestDTO;
import com.simpla.vectorial.dto.SearchResponseDTO;
import com.simpla.vectorial.dto.StoreResponseDTO;
import com.simpla.vectorial.processor.VectorialProcessor;
import com.simpla.vectorial.proto.VectorialServiceGrpc;
import com.simpla.vectorial.proto.StoreRequest;
import com.simpla.vectorial.proto.StoreResponse;
import com.simpla.vectorial.proto.SearchRequest;
import com.simpla.vectorial.proto.SearchResponse;
import com.simpla.vectorial.proto.SearchResult;
import io.grpc.stub.StreamObserver;

import java.util.*;

public class VectorialServiceImpl extends VectorialServiceGrpc.VectorialServiceImplBase {

    private final VectorialProcessor processor;

    public VectorialServiceImpl() {
        this.processor = new VectorialProcessor();
    }

    @Override
    public void store(StoreRequest request, StreamObserver<StoreResponse> responseObserver) {
        // Delegate to processor
        StoreResponseDTO result = processor.processStore(request.getData());

        // Convert DTO to gRPC response
        StoreResponse response = StoreResponse.newBuilder()
                .setSuccess(result.isSuccess())
                .setMessage(result.getMessage())
                .build();

        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }

    @Override
    public void search(SearchRequest request, StreamObserver<SearchResponse> responseObserver) {
        // Extract parameters from gRPC request
        List<Double> queryEmbedding = new ArrayList<>(request.getEmbeddingList());

        SearchRequestDTO searchRequest = new SearchRequestDTO(
                queryEmbedding,
                new HashMap<>(request.getFiltersMap()),
                request.getLimit()
        );

        // Delegate to processor
        SearchResponseDTO result = processor.processSearch(searchRequest);

        // Convert DTO to gRPC response
        SearchResponse.Builder responseBuilder = SearchResponse.newBuilder()
                .setSuccess(result.isSuccess())
                .setMessage(result.getMessage());

        for (SearchResponseDTO.DocumentMatch match : result.getResults()) {
            SearchResult.Builder resultBuilder = SearchResult.newBuilder()
                    .setDocumentId(match.getDocumentId())
                    .setScore(match.getScore());

            // Add metadata to the result
            for (Map.Entry<String, Object> metadataEntry : match.getMetadata().entrySet()) {
                resultBuilder.putMetadata(metadataEntry.getKey(), String.valueOf(metadataEntry.getValue()));
            }

            responseBuilder.addResults(resultBuilder.build());
        }

        responseObserver.onNext(responseBuilder.build());
        responseObserver.onCompleted();
    }

    public VectorialProcessor getProcessor() {
        return processor;
    }

    public void shutdown() {
        processor.shutdown();
    }
}