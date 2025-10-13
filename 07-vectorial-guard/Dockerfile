# Multi-stage build for Java gRPC Vectorial service
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

# Copy pom.xml and download dependencies (for better caching)
COPY pom.xml ./
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Generate protobuf classes and build the application
RUN mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:17-jre

WORKDIR /app

# Copy the fat jar from builder stage
COPY --from=builder /app/target/vectorial-ms-1.0.0-jar-with-dependencies.jar ./vectorial-ms.jar

# Expose gRPC port
EXPOSE 50052

# Run the application
CMD ["java", "-jar", "vectorial-ms.jar"]