FROM maven:3.9-eclipse-temurin-17 AS builder

ARG MODE=api
WORKDIR /app

COPY pom-${MODE}.xml ./pom.xml

RUN mvn dependency:go-offline -B

COPY src ./src

RUN mvn clean package -DskipTests

# Runtime stage
FROM eclipse-temurin:17-jre

WORKDIR /app

COPY --from=builder /app/target/relational-guard-1.0.0.jar ./relational-guard.jar

EXPOSE 50051 8090

ENTRYPOINT ["java", "-jar", "relational-guard.jar"]