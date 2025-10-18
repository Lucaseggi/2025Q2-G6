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

COPY --from=builder /app/target/vectorial-guard-1.0.0.jar ./vectorial-guard.jar

EXPOSE 50052 8080

ENTRYPOINT ["java", "-jar", "vectorial-guard.jar"]
