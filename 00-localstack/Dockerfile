FROM localstack/localstack:latest

# Copy initialization script
COPY init-aws-resources.sh /etc/localstack/init/ready.d/

# Make script executable
RUN chmod +x /etc/localstack/init/ready.d/init-aws-resources.sh
