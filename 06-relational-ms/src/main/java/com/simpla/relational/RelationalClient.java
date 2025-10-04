package com.simpla.relational;

import com.simpla.relational.proto.RelationalServiceGrpc;
import com.simpla.relational.proto.StoreRequest;
import com.simpla.relational.proto.StoreResponse;
import com.simpla.relational.proto.ReconstructNormRequest;
import com.simpla.relational.proto.ReconstructNormResponse;
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

    public void store(String data) {
        System.out.println("Calling store() with data length: " + data.length());
        System.out.println("Data preview: " + (data.length() > 200 ? data.substring(0, 200) + "..." : data));

        StoreRequest request = StoreRequest.newBuilder()
                .setData(data)
                .build();

        StoreResponse response;
        try {
            response = blockingStub.store(request);
        } catch (StatusRuntimeException e) {
            System.err.println("RPC failed: " + e.getStatus());
            return;
        }

        System.out.println("\n=== STORE RESPONSE ===");
        System.out.println("Success: " + response.getSuccess());
        System.out.println("Message: " + response.getMessage());
        System.out.println("PK Mapping JSON: " + response.getPkMappingJson());
        System.out.println("=====================\n");
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

        System.out.println("Response - Success: " + response.getSuccess());
        System.out.println("Message: " + response.getMessage());

        if (response.getSuccess() && !response.getNormaJson().isEmpty()) {
            System.out.println("Norma JSON length: " + response.getNormaJson().length());
            // Optionally print first 500 chars of JSON for inspection
            String json = response.getNormaJson();
            if (json.length() > 500) {
                System.out.println("JSON Preview: " + json.substring(0, 500) + "...");
            } else {
                System.out.println("JSON Content: " + json);
            }
        }
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
            System.out.println("\nDivisions JSON:");
            String divisionsJson = response.getDivisionsJson();
            if (divisionsJson.length() > 500) {
                System.out.println(divisionsJson.substring(0, 500) + "...");
                System.out.println("(Total length: " + divisionsJson.length() + " chars)");
            } else {
                System.out.println(divisionsJson);
            }

            System.out.println("\nArticles JSON:");
            String articlesJson = response.getArticlesJson();
            if (articlesJson.length() > 500) {
                System.out.println(articlesJson.substring(0, 500) + "...");
                System.out.println("(Total length: " + articlesJson.length() + " chars)");
            } else {
                System.out.println(articlesJson);
            }
        }
        System.out.println("=========================\n");
    }

    public static void main(String[] args) throws Exception {
        String target = "localhost:50051";
        String mode = "batch"; // "store", "reconstruct", or "batch"
        int infolegId = 183532; // Default from demo data
        String jsonFile = null;

        // Parse arguments: mode [infoleg_id|json_file] [target]
        if (args.length > 0) {
            mode = args[0];
        }

        if (args.length > 1) {
            if (mode.equals("store")) {
                jsonFile = args[1];
            } else if (!mode.equals("batch")) {
                try {
                    infolegId = Integer.parseInt(args[1]);
                } catch (NumberFormatException e) {
                    System.err.println("Invalid infoleg_id: " + args[1] + ". Using default: " + infolegId);
                }
            }
        }

        if (args.length > 2) {
            target = args[2];
        }

        System.out.println("Connecting to relational-ms at: " + target);

        ManagedChannel channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext()
                .build();

        try {
            RelationalClient client = new RelationalClient(channel);

            if (mode.equals("store")) {
                if (jsonFile == null) {
                    System.err.println("Error: JSON file path required for store mode");
                    System.err.println("Usage: RelationalClient store <json_file> [target]");
                    return;
                }

                System.out.println("Reading JSON from file: " + jsonFile);
                String jsonData = new String(java.nio.file.Files.readAllBytes(
                    java.nio.file.Paths.get(jsonFile)
                ));

                client.store(jsonData);
            } else if (mode.equals("batch")) {
                System.out.println("Testing GetBatch with sample division and article IDs");

                // Create sample entity pairs - replace with actual IDs from your database
                List<EntityPair> entities = new ArrayList<>();

                // Add some division IDs (you can modify these based on your actual data)
                entities.add(EntityPair.newBuilder()
                        .setType("division")
                        .setId(1)
                        .build());

                entities.add(EntityPair.newBuilder()
                        .setType("division")
                        .setId(2)
                        .build());

                // Add some article IDs (you can modify these based on your actual data)
                entities.add(EntityPair.newBuilder()
                        .setType("article")
                        .setId(1)
                        .build());

                entities.add(EntityPair.newBuilder()
                        .setType("article")
                        .setId(2)
                        .build());

                entities.add(EntityPair.newBuilder()
                        .setType("article")
                        .setId(3)
                        .build());

                client.getBatch(entities);
            } else {
                System.out.println("Testing ReconstructNorm with infoleg_id: " + infolegId);
                client.reconstructNorm(infolegId);
            }

        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}