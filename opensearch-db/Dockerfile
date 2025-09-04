FROM opensearchproject/opensearch:2.12.0

# Copy custom configuration if needed
COPY opensearch.yml /usr/share/opensearch/config/opensearch.yml

# Create custom index templates and mappings directory
RUN mkdir -p /usr/share/opensearch/config/templates

COPY index-templates/ /usr/share/opensearch/config/templates/

# Set proper permissions
USER opensearch

EXPOSE 9200 9600