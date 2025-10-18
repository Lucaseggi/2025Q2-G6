package com.simpla.vectorial.dto;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SearchRequestDTO {
    private List<Double> embedding;
    private Map<String, String> filters;
    private int limit;

    // Default constructor for Jackson
    public SearchRequestDTO() {
        this.filters = new HashMap<>();
        this.limit = 10;
    }

    public SearchRequestDTO(List<Double> embedding, Map<String, String> filters, int limit) {
        this.embedding = embedding;
        this.filters = filters != null ? filters : new HashMap<>();
        this.limit = limit;
    }

    public List<Double> getEmbedding() {
        return embedding;
    }

    public void setEmbedding(List<Double> embedding) {
        this.embedding = embedding;
    }

    public Map<String, String> getFilters() {
        return filters;
    }

    public void setFilters(Map<String, String> filters) {
        this.filters = filters;
    }

    public int getLimit() {
        return limit;
    }

    public void setLimit(int limit) {
        this.limit = limit;
    }
}
