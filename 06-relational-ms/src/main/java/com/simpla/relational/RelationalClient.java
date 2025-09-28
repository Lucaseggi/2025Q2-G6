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
        System.out.println("Calling store() with data: " + data);

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

        System.out.println("Response - Success: " + response.getSuccess() + ", Message: " + response.getMessage());
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
        int infolegId = 183532; // Default from demo data

        if (args.length > 0) {
            try {
                infolegId = Integer.parseInt(args[0]);
            } catch (NumberFormatException e) {
                System.err.println("Invalid infoleg_id: " + args[0] + ". Using default: " + infolegId);
            }
        }

        if (args.length > 1) {
            target = args[1];
        }

        System.out.println("Connecting to relational-ms at: " + target);
        System.out.println("Testing ReconstructNorm with infoleg_id: " + infolegId);

        ManagedChannel channel = ManagedChannelBuilder.forTarget(target)
                .usePlaintext()
                .build();

        try {
            RelationalClient client = new RelationalClient(channel);

            // Test the ReconstructNorm method
            client.reconstructNorm(infolegId);

        } finally {
            channel.shutdownNow().awaitTermination(5, TimeUnit.SECONDS);
        }
    }
}