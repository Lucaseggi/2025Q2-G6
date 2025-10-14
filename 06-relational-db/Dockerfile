FROM postgres:16-alpine

# Set environment variables
ENV POSTGRES_DB=simpla_rag
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres123

# Copy initialization scripts
COPY sql/ /docker-entrypoint-initdb.d/

# Set the data directory
ENV PGDATA=/var/lib/postgresql/data/pgdata

# Expose port
EXPOSE 5432