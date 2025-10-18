package com.simpla.relational.dto;

import java.util.ArrayList;
import java.util.List;

/**
 * DTO for batch retrieval request.
 * Transport-agnostic request that can be used by gRPC, REST, or any other interface.
 */
public class GetBatchRequestDTO {
    private List<EntityPairDTO> entities;

    // Default constructor for Jackson
    public GetBatchRequestDTO() {
        this.entities = new ArrayList<>();
    }

    public GetBatchRequestDTO(List<EntityPairDTO> entities) {
        this.entities = entities != null ? entities : new ArrayList<>();
    }

    public List<EntityPairDTO> getEntities() {
        return entities;
    }

    public void setEntities(List<EntityPairDTO> entities) {
        this.entities = entities;
    }

    /**
     * Inner class for entity pair
     */
    public static class EntityPairDTO {
        private String type;
        private long id;

        // Default constructor for Jackson
        public EntityPairDTO() {
        }

        public EntityPairDTO(String type, long id) {
            this.type = type;
            this.id = id;
        }

        public String getType() {
            return type;
        }

        public void setType(String type) {
            this.type = type;
        }

        public long getId() {
            return id;
        }

        public void setId(long id) {
            this.id = id;
        }
    }
}
