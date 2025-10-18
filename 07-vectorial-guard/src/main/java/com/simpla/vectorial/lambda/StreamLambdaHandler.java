package com.simpla.vectorial.lambda;

import com.amazonaws.serverless.exceptions.ContainerInitializationException;
import com.amazonaws.serverless.proxy.model.AwsProxyRequest;
import com.amazonaws.serverless.proxy.model.AwsProxyResponse;
import com.amazonaws.serverless.proxy.spring.SpringBootLambdaContainerHandler;
import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestStreamHandler;
import com.simpla.vectorial.VectorialApplication;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * AWS Lambda handler for Spring Boot application.
 * This single handler serves all API endpoints through Spring Boot's routing.
 *
 * Uses AWS Serverless Java Container to wrap the Spring Boot application,
 * allowing it to run in AWS Lambda while maintaining all Spring functionality
 * including dependency injection, request mapping, and middleware.
 */
public class StreamLambdaHandler implements RequestStreamHandler {

    private static SpringBootLambdaContainerHandler<AwsProxyRequest, AwsProxyResponse> handler;

    static {
        try {
            // Initialize Spring Boot application within Lambda container
            // The container is initialized once and reused across invocations (warm starts)
            handler = SpringBootLambdaContainerHandler.getAwsProxyHandler(VectorialApplication.class);

            // Optional: Set initialization timeout (default is 10 seconds)
            // handler.setInitializationTimeout(20_000);

        } catch (ContainerInitializationException e) {
            // If we fail to initialize the container, log and rethrow
            e.printStackTrace();
            throw new RuntimeException("Unable to load Spring Boot application", e);
        }
    }

    @Override
    public void handleRequest(InputStream input, OutputStream output, Context context)
            throws IOException {
        // Proxy the request through the Spring Boot container
        handler.proxyStream(input, output, context);
    }
}
