package com.simpla.relational;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.protobuf.services.ProtoReflectionService;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

public class RelationalServer {
    private Server server;
    private RelationalServiceImpl relationalService;

    private void start() throws IOException {
        int port = 50051;
        relationalService = new RelationalServiceImpl();

        server = ServerBuilder.forPort(port)
                .addService(relationalService)
                .addService(ProtoReflectionService.newInstance()) // Enable reflection for testing
                .build()
                .start();

        System.out.println("gRPC server started, listening on " + port);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            System.err.println("*** shutting down gRPC server since JVM is shutting down");
            try {
                RelationalServer.this.stop();
            } catch (InterruptedException e) {
                e.printStackTrace(System.err);
            }
            System.err.println("*** server shut down");
        }));
    }

    private void stop() throws InterruptedException {
        if (relationalService != null) {
            relationalService.shutdown();
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
        final RelationalServer server = new RelationalServer();
        server.start();
        server.blockUntilShutdown();
    }
}