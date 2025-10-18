package com.simpla.relational;

import com.simpla.relational.dto.GetBatchResponseDTO;
import com.simpla.relational.dto.ReconstructNormResponseDTO;
import com.simpla.relational.dto.StoreResponseDTO;
import com.simpla.relational.processor.RelationalProcessor;
import com.simpla.relational.proto.*;
import io.grpc.stub.StreamObserver;

import java.util.ArrayList;
import java.util.List;

/**
 * gRPC service implementation for relational guard.
 * Delegates all business logic to RelationalProcessor.
 */
public class RelationalServiceImpl extends RelationalServiceGrpc.RelationalServiceImplBase {

    private final RelationalProcessor processor;

    public RelationalServiceImpl() {
        this.processor = new RelationalProcessor();
    }

    @Override
    public void store(StoreRequest request, StreamObserver<StoreResponse> responseObserver) {
        // Delegate to processor
        StoreResponseDTO result = processor.processStore(request.getData());

        // Convert DTO to gRPC response
        StoreResponse response = buildStoreResponse(
            result.isSuccess(),
            result.getMessage(),
            result.getPkMappingJson()
        );

        sendResponse(responseObserver, response);
    }

    @Override
    public void reconstructNorm(ReconstructNormRequest request, StreamObserver<ReconstructNormResponse> responseObserver) {
        // Delegate to processor
        ReconstructNormResponseDTO result = processor.processReconstructByInfolegId(request.getInfolegId());

        // Convert DTO to gRPC response
        ReconstructNormResponse response = buildReconstructNormResponse(
            result.isSuccess(),
            result.getMessage(),
            result.getNormaJson()
        );

        sendResponse(responseObserver, response);
    }

    @Override
    public void reconstructNormById(ReconstructNormByIdRequest request, StreamObserver<ReconstructNormResponse> responseObserver) {
        // Delegate to processor
        ReconstructNormResponseDTO result = processor.processReconstructById(request.getId());

        // Convert DTO to gRPC response
        ReconstructNormResponse response = buildReconstructNormResponse(
            result.isSuccess(),
            result.getMessage(),
            result.getNormaJson()
        );

        sendResponse(responseObserver, response);
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

    @Override
    public void getBatch(GetBatchRequest request, StreamObserver<GetBatchResponse> responseObserver) {
        // Convert gRPC EntityPairs to DTOs
        List<RelationalProcessor.EntityPairDTO> entityPairs = new ArrayList<>();
        for (EntityPair entityPair : request.getEntitiesList()) {
            entityPairs.add(new RelationalProcessor.EntityPairDTO(
                entityPair.getType(),
                entityPair.getId()
            ));
        }

        // Delegate to processor
        GetBatchResponseDTO result = processor.processGetBatch(entityPairs);

        // Convert DTO to gRPC response
        GetBatchResponse response = buildGetBatchResponse(
            result.isSuccess(),
            result.getMessage(),
            result.getNormasJson()
        );

        sendResponse(responseObserver, response);
    }

    public void shutdown() {
        processor.shutdown();
    }
}