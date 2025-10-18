package com.simpla.relational;

import com.simpla.relational.proto.RelationalServiceGrpc;
import com.simpla.relational.proto.GetBatchRequest;
import com.simpla.relational.proto.GetBatchResponse;
import com.simpla.relational.proto.ReconstructNormRequest;
import com.simpla.relational.proto.ReconstructNormByIdRequest;
import com.simpla.relational.proto.ReconstructNormResponse;
import com.simpla.relational.proto.EntityPair;
import io.grpc.Channel;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;

import java.util.concurrent.TimeUnit;
import java.util.List;
import java.util.ArrayList;

public class RelationalClient {
    private final RelationalServiceGrpc.RelationalServiceBlockingStub blockingStub;

    public RelationalClient(Channel channel) {
        blockingStub = RelationalServiceGrpc.newBlockingStub(channel);
    }

    public void reconstructNorm(int infolegId) {
        System.out.println("Calling reconstructNorm() with infoleg_id: " + infolegId);

        ReconstructNormRequest request = ReconstructNormRequest.newBuilder()
                .setInfolegId(infolegId)
                .build();

        ReconstructNormResponse response;
        try {
            response = blockingStub.reconstructNorm(request);
        } catch (StatusRuntimeException e) {
            System.err.println("RPC failed: " + e.getStatus());
            return;
        }

        System.out.println("\n=== RECONSTRUCT NORM RESPONSE ===");
        System.out.println("Success: " + response.getSuccess());
        System.out.println("Message: " + response.getMessage());

        if (response.getSuccess()) {
            System.out.println("\nNorma JSON:");
            String normaJson = response.getNormaJson();
            if (normaJson.length() > 500) {
                System.out.println(normaJson);
                System.out.println("(Total length: " + normaJson.length() + " chars)");
            } else {
                System.out.println(normaJson);
            }
        }
        System.out.println("==================================\n");
    }

    public void reconstructNormById(long id) {
        System.out.println("Calling reconstructNormById() with id: " + id);

        ReconstructNormByIdRequest request = ReconstructNormByIdRequest.newBuilder()
                .setId(id)
                .build();

        ReconstructNormResponse response;
        try {
            response = blockingStub.reconstructNormById(request);
        } catch (StatusRuntimeException e) {
            System.err.println("RPC failed: " + e.getStatus());
            return;
        }

        System.out.println("\n=== RECONSTRUCT NORM BY ID RESPONSE ===");
        System.out.println("Success: " + response.getSuccess());
        System.out.println("Message: " + response.getMessage());

        if (response.getSuccess()) {
            System.out.println("\nNorma JSON:");
            String normaJson = response.getNormaJson();
            if (normaJson.length() > 500) {
                System.out.println(normaJson.substring(0, 500) + "...");
                System.out.println("(Total length: " + normaJson.length() + " chars)");
            } else {
                System.out.println(normaJson);
            }
        }
        System.out.println("========================================\n");
    }

    public void getBatch(List<EntityPair> entities) {
        System.out.println("Calling getBatch() with " + entities.size() + " entities:");
        for (EntityPair entity : entities) {
            System.out.println("  - type: " + entity.getType() + ", id: " + entity.getId());
        }

        GetBatchRequest request = GetBatchRequest.newBuilder()
                .addAllEntities(entities)
                .build();

        GetBatchResponse response;
        try {
            response = blockingStub.getBatch(request);
        } catch (StatusRuntimeException e) {
            System.err.println("RPC failed: " + e.getStatus());
            return;
        }

        System.out.println("\n=== GET BATCH RESPONSE ===");
        System.out.println("Success: " + response.getSuccess());
        System.out.println("Message: " + response.getMessage());

        if (response.getSuccess()) {
            System.out.println("\nNormas JSON:");
            String normasJson = response.getNormasJson();
            if (normasJson.length() > 500) {
                System.out.println(normasJson);
                System.out.println("(Total length: " + normasJson.length() + " chars)");
            } else {
                System.out.println(normasJson);
            }
        }
        System.out.println("=========================\n");
    }

    public static void main(String[] args) throws Exception {
        String target = "localhost:50051";

        if (args.length > 0) {
            target = args[0];
        }

        System.out.println("Connecting to relational-guard at: " + target);

        ManagedChannel channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext()
                .build();

        try {
            RelationalClient client = new RelationalClient(channel);

            // Test 1: ReconstructNorm by infoleg_id
            System.out.println("=== Test 1: ReconstructNorm by infoleg_id ===");
            client.reconstructNorm(183508);

            // Test 2: ReconstructNormById
            System.out.println("\n=== Test 2: ReconstructNorm by database ID ===");
//            client.reconstructNormById(1);

            // Test 3: GetBatch with article
            System.out.println("\n=== Test 3: GetBatch with article ID 4 ===");
            List<EntityPair> entities = new ArrayList<>();
            entities.add(EntityPair.newBuilder()
                    .setType("article")
                    .setId(4)
                    .build());
//            client.getBatch(entities);

        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}
