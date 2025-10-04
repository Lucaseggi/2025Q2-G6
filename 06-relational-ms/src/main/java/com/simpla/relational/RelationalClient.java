package com.simpla.relational;

import com.simpla.relational.proto.RelationalServiceGrpc;
import com.simpla.relational.proto.StoreRequest;
import com.simpla.relational.proto.StoreResponse;
import com.simpla.relational.proto.ReconstructNormRequest;
import com.simpla.relational.proto.ReconstructNormResponse;
import io.grpc.Channel;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.StatusRuntimeException;

import java.util.concurrent.TimeUnit;

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

    public static void main(String[] args) throws Exception {
        String target = "localhost:50051";
        String mode = "reconstruct"; // "store" or "reconstruct"
        int infolegId = 183532; // Default from demo data
        String jsonFile = null;

        // Parse arguments: mode [infoleg_id|json_file] [target]
        if (args.length > 0) {
            mode = args[0];
        }

        if (args.length > 1) {
            if (mode.equals("store")) {
                jsonFile = args[1];
            } else {
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
            } else {
                System.out.println("Testing ReconstructNorm with infoleg_id: " + infolegId);
                client.reconstructNorm(infolegId);
            }

        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}