FROM localstack/localstack:3.0

# Set environment variables for SQS configuration
ENV SERVICES=sqs
ENV DEBUG=1
ENV DATA_DIR=/var/lib/localstack/data

# Create data directory
RUN mkdir -p /var/lib/localstack/data

# Copy initialization script
COPY init-sqs.sh /etc/localstack/init/ready.d/init-sqs.sh
RUN chmod +x /etc/localstack/init/ready.d/init-sqs.sh

EXPOSE 4566

CMD ["localstack", "start"]