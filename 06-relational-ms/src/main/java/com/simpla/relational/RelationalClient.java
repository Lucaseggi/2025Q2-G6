package com.simpla.relational;

import com.simpla.relational.proto.RelationalServiceGrpc;
import com.simpla.relational.proto.GetBatchRequest;
import com.simpla.relational.proto.GetBatchResponse;
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
                System.out.println(normasJson.substring(0, 500) + "...");
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

        System.out.println("Connecting to relational-ms at: " + target);

        ManagedChannel channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext()
                .build();

        try {
            RelationalClient client = new RelationalClient(channel);

            System.out.println("Testing GetBatch with article ID 4");

            List<EntityPair> entities = new ArrayList<>();

            // Add article with ID 4
            entities.add(EntityPair.newBuilder()
                    .setType("article")
                    .setId(4)
                    .build());

            client.getBatch(entities);

        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}
