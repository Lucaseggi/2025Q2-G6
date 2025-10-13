package com.simpla.relational.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonIgnore;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

public class NormaBatchData {
    @JsonProperty("infoleg_id")
    private Integer infolegId;

    @JsonProperty("jurisdiccion")
    private String jurisdiccion;

    @JsonProperty("titulo_sumario")
    private String tituloSumario;

    @JsonProperty("publicacion")
    private LocalDate publicacion;

    @JsonProperty("texto_resumido")
    private String textoResumido;

    @JsonProperty("nro_boletin")
    private String nroBoletin;

    @JsonProperty("pag_boletin")
    private String pagBoletin;

    @JsonProperty("titulo_resumido")
    private String tituloResumido;

    @JsonProperty("tipo_norma")
    private String tipoNorma;

    @JsonProperty("divisions")
    private List<Division> divisions = new ArrayList<>();

    @JsonProperty("articles")
    private List<Article> articles = new ArrayList<>();

    // Internal tracking (not serialized)
    @JsonIgnore
    private List<Long> divisionIds = new ArrayList<>();

    @JsonIgnore
    private List<Long> articleIds = new ArrayList<>();

    // Getters and setters
    public Integer getInfolegId() { return infolegId; }
    public void setInfolegId(Integer infolegId) { this.infolegId = infolegId; }

    public String getJurisdiccion() { return jurisdiccion; }
    public void setJurisdiccion(String jurisdiccion) { this.jurisdiccion = jurisdiccion; }

    public String getTituloSumario() { return tituloSumario; }
    public void setTituloSumario(String tituloSumario) { this.tituloSumario = tituloSumario; }

    public LocalDate getPublicacion() { return publicacion; }
    public void setPublicacion(LocalDate publicacion) { this.publicacion = publicacion; }

    public String getTextoResumido() { return textoResumido; }
    public void setTextoResumido(String textoResumido) { this.textoResumido = textoResumido; }

    public String getNroBoletin() { return nroBoletin; }
    public void setNroBoletin(String nroBoletin) { this.nroBoletin = nroBoletin; }

    public String getPagBoletin() { return pagBoletin; }
    public void setPagBoletin(String pagBoletin) { this.pagBoletin = pagBoletin; }

    public String getTituloResumido() { return tituloResumido; }
    public void setTituloResumido(String tituloResumido) { this.tituloResumido = tituloResumido; }

    public String getTipoNorma() { return tipoNorma; }
    public void setTipoNorma(String tipoNorma) { this.tipoNorma = tipoNorma; }

    public List<Division> getDivisions() { return divisions; }
    public void setDivisions(List<Division> divisions) { this.divisions = divisions; }

    public List<Article> getArticles() { return articles; }
    public void setArticles(List<Article> articles) { this.articles = articles; }

    public List<Long> getDivisionIds() { return divisionIds; }
    public void setDivisionIds(List<Long> divisionIds) { this.divisionIds = divisionIds; }

    public List<Long> getArticleIds() { return articleIds; }
    public void setArticleIds(List<Long> articleIds) { this.articleIds = articleIds; }

    public void addDivisionId(Long id) { this.divisionIds.add(id); }
    public void addArticleId(Long id) { this.articleIds.add(id); }

    public void addDivision(Division division) { this.divisions.add(division); }
    public void addArticle(Article article) { this.articles.add(article); }
}
