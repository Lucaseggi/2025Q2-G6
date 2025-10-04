package com.simpla.relational.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.ArrayList;

public class Article {
    private Long id;

    @JsonProperty("ordinal")
    private String ordinal;

    @JsonProperty("body")
    private String body;

    @JsonProperty("order")
    private Integer orderIndex;

    @JsonProperty("articles")
    private List<Article> childArticles = new ArrayList<>();

    private Long parentArticleId;

    public Article() {}

    public Article(Long id, String ordinal, String body, Integer orderIndex) {
        this.id = id;
        this.ordinal = ordinal;
        this.body = body;
        this.orderIndex = orderIndex;
    }

    // Getters and setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getOrdinal() {
        return ordinal;
    }

    public void setOrdinal(String ordinal) {
        this.ordinal = ordinal;
    }

    public String getBody() {
        return body;
    }

    public void setBody(String body) {
        this.body = body;
    }

    public Integer getOrderIndex() {
        return orderIndex;
    }

    public void setOrderIndex(Integer orderIndex) {
        this.orderIndex = orderIndex;
    }

    public List<Article> getChildArticles() {
        return childArticles;
    }

    public void setChildArticles(List<Article> childArticles) {
        this.childArticles = childArticles != null ? childArticles : new ArrayList<>();
    }

    public void addChildArticle(Article article) {
        if (this.childArticles == null) {
            this.childArticles = new ArrayList<>();
        }
        this.childArticles.add(article);
    }

    public Long getParentArticleId() {
        return parentArticleId;
    }

    public void setParentArticleId(Long parentArticleId) {
        this.parentArticleId = parentArticleId;
    }
}