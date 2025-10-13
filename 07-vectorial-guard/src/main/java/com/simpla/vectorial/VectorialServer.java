package com.simpla.vectorial;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.protobuf.services.ProtoReflectionService;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

public class VectorialServer {
    private Server server;
    private VectorialServiceImpl vectorialService;

    private void start() throws IOException {
        int port = 50052; // Using different port from relational-ms (50051)
        vectorialService = new VectorialServiceImpl();

        server = ServerBuilder.forPort(port)
                .addService(vectorialService)
                .addService(ProtoReflectionService.newInstance()) // Enable reflection for testing
                .build()
                .start();

        System.out.println("gRPC Vectorial server started, listening on " + port);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.err.println("*** shutting down gRPC Vectorial server since JVM is shutting down");
            try {
                VectorialServer.this.stop();
            } catch (InterruptedException e) {
                e.printStackTrace(System.err);
            }
            System.err.println("*** Vectorial server shut down");
        }));
    }

    private void stop() throws InterruptedException {
        if (vectorialService != null) {
            vectorialService.shutdown();
        }
        if (server != null) {
            server.shutdown().awaitTermination(30, TimeUnit.SECONDS);
        }
    }

    private void blockUntilShutdown() throws InterruptedException {
        if (server != null) {
            server.awaitTermination();
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        final VectorialServer server = new VectorialServer();
        server.start();
        server.blockUntilShutdown();
    }
}