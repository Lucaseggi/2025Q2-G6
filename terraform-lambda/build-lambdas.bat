@echo off
echo Building Lambda JARs using Docker...

cd ..

echo Building relational-guard...
docker run --rm -v "%cd%\06-relational-guard:/app" -w /app maven:3.9-eclipse-temurin-17 mvn clean package -DskipTests -f pom-lambda.xml

if not exist "terraform-lambda\lambda-artifacts" mkdir terraform-lambda\lambda-artifacts
copy 06-relational-guard\target\relational-guard-1.0.0.jar terraform-lambda\lambda-artifacts\

echo Building vectorial-guard...
docker run --rm -v "%cd%\07-vectorial-guard:/app" -w /app maven:3.9-eclipse-temurin-17 mvn clean package -DskipTests -f pom-lambda.xml

copy 07-vectorial-guard\target\vectorial-guard-1.0.0.jar terraform-lambda\lambda-artifacts\

cd terraform-lambda
echo.
echo Lambda JARs built and copied to lambda-artifacts/
