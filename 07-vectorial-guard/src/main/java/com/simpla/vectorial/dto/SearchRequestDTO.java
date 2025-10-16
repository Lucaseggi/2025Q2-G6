package com.simpla.vectorial.dto;

import java.util.List;
import java.util.Map;

public class SearchRequestDTO {
    private final List<Double> embedding;
    private final Map<String, String> filters;
    private final int limit;

    public SearchRequestDTO(List<Double> embedding, Map<String, String> filters, int limit) {
        this.embedding = embedding;
        this.filters = filters;
        this.limit = limit;
    }

    public List<Double> getEmbedding() {
        return embedding;
    }

    public Map<String, String> getFilters() {
        return filters;
    }

    public int getLimit() {
        return limit;
    }
}
