package com.simpla.relational.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.ArrayList;

public class Division {
    private Long id;

    @JsonProperty("name")
    private String name;

    @JsonProperty("ordinal")
    private String ordinal;

    @JsonProperty("title")
    private String title;

    @JsonProperty("body")
    private String body;

    @JsonProperty("order")
    private Integer orderIndex;

    @JsonProperty("articles")
    private List<Article> articles = new ArrayList<>();

    @JsonProperty("divisions")
    private List<Division> childDivisions = new ArrayList<>();

    private Long parentDivisionId;

    public Division() {}

    public Division(Long id, String name, String ordinal, String title, String body, Integer orderIndex) {
        this.id = id;
        this.name = name;
        this.ordinal = ordinal;
        this.title = title;
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

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getOrdinal() {
        return ordinal;
    }

    public void setOrdinal(String ordinal) {
        this.ordinal = ordinal;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
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

    public List<Article> getArticles() {
        return articles;
    }

    public void setArticles(List<Article> articles) {
        this.articles = articles != null ? articles : new ArrayList<>();
    }

    public void addArticle(Article article) {
        if (this.articles == null) {
            this.articles = new ArrayList<>();
        }
        this.articles.add(article);
    }

    public List<Division> getChildDivisions() {
        return childDivisions;
    }

    public void setChildDivisions(List<Division> childDivisions) {
        this.childDivisions = childDivisions != null ? childDivisions : new ArrayList<>();
    }

    public void addChildDivision(Division division) {
        if (this.childDivisions == null) {
            this.childDivisions = new ArrayList<>();
        }
        this.childDivisions.add(division);
    }

    public Long getParentDivisionId() {
        return parentDivisionId;
    }

    public void setParentDivisionId(Long parentDivisionId) {
        this.parentDivisionId = parentDivisionId;
    }
}