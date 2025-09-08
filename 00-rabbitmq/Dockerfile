FROM rabbitmq:3.12-management

# Enable RabbitMQ management plugin
RUN rabbitmq-plugins enable rabbitmq_management

# Copy configuration files
COPY rabbitmq.conf /etc/rabbitmq/
COPY definitions.json /etc/rabbitmq/

# Set permissions and create data directory
RUN mkdir -p /var/lib/rabbitmq && \
    chown -R rabbitmq:rabbitmq /var/lib/rabbitmq

# Expose ports
EXPOSE 5672 15672

# Use the official entrypoint
CMD ["rabbitmq-server"]