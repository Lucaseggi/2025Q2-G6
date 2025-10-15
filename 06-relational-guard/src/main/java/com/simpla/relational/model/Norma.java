package com.simpla.relational.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonInclude;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.ArrayList;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class Norma {
    @JsonProperty("infoleg_id")
    private Integer infolegId;

    @JsonProperty("jurisdiccion")
    private String jurisdiccion;

    @JsonProperty("clase_norma")
    private String claseNorma;

    @JsonProperty("tipo_norma")
    private String tipoNorma;

    @JsonProperty("sancion")
    private LocalDate sancion;

    @JsonProperty("publicacion")
    private LocalDate publicacion;

    @JsonProperty("titulo_sumario")
    private String tituloSumario;

    @JsonProperty("titulo_resumido")
    private String tituloResumido;

    @JsonProperty("observaciones")
    private String observaciones;

    @JsonProperty("nro_boletin")
    private String nroBoletin;

    @JsonProperty("pag_boletin")
    private String pagBoletin;

    @JsonProperty("texto_resumido")
    private String textoResumido;

    @JsonProperty("texto_norma")
    private String textoNorma;

    @JsonProperty("texto_norma_actualizado")
    private String textoNormaActualizado;

    @JsonProperty("estado")
    private String estado;

    @JsonProperty("purified_texto_norma")
    private String purifiedTextoNorma;

    @JsonProperty("purified_texto_norma_actualizado")
    private String purifiedTextoNormaActualizado;

    @JsonProperty("embedding_model")
    private String embeddingModel;

    @JsonProperty("embedding_source")
    private String embeddingSource;

    @JsonProperty("embedded_at")
    private LocalDateTime embeddedAt;

    @JsonProperty("embedding_type")
    private String embeddingType;

    @JsonProperty("llm_model_used")
    private String llmModelUsed;

    @JsonProperty("llm_tokens_used")
    private Integer llmTokensUsed;

    @JsonProperty("llm_processing_time")
    private Double llmProcessingTime;

    @JsonProperty("llm_similarity_score")
    private Double llmSimilarityScore;

    @JsonProperty("structured_texto_norma")
    private StructuredTexto structuredTextoNorma;

    @JsonProperty("structured_texto_norma_actualizado")
    private StructuredTexto structuredTextoNormaActualizado;

    @JsonProperty("id_normas")
    private List<NormaReferencia> idNormas;

    @JsonProperty("lista_normas_que_complementa")
    private List<Integer> listaNormasQueComplementa;

    @JsonProperty("lista_normas_que_la_complementan")
    private List<Integer> listaNormasQueLaComplementan;

    public Norma() {}

    // Getters and setters
    public Integer getInfolegId() {
        return infolegId;
    }

    public void setInfolegId(Integer infolegId) {
        this.infolegId = infolegId;
    }

    public String getJurisdiccion() {
        return jurisdiccion;
    }

    public void setJurisdiccion(String jurisdiccion) {
        this.jurisdiccion = jurisdiccion;
    }

    public String getClaseNorma() {
        return claseNorma;
    }

    public void setClaseNorma(String claseNorma) {
        this.claseNorma = claseNorma;
    }

    public String getTipoNorma() {
        return tipoNorma;
    }

    public void setTipoNorma(String tipoNorma) {
        this.tipoNorma = tipoNorma;
    }

    public LocalDate getSancion() {
        return sancion;
    }

    public void setSancion(LocalDate sancion) {
        this.sancion = sancion;
    }

    public LocalDate getPublicacion() {
        return publicacion;
    }

    public void setPublicacion(LocalDate publicacion) {
        this.publicacion = publicacion;
    }

    public String getTituloSumario() {
        return tituloSumario;
    }

    public void setTituloSumario(String tituloSumario) {
        this.tituloSumario = tituloSumario;
    }

    public String getTituloResumido() {
        return tituloResumido;
    }

    public void setTituloResumido(String tituloResumido) {
        this.tituloResumido = tituloResumido;
    }

    public String getObservaciones() {
        return observaciones;
    }

    public void setObservaciones(String observaciones) {
        this.observaciones = observaciones;
    }

    public String getNroBoletin() {
        return nroBoletin;
    }

    public void setNroBoletin(String nroBoletin) {
        this.nroBoletin = nroBoletin;
    }

    public String getPagBoletin() {
        return pagBoletin;
    }

    public void setPagBoletin(String pagBoletin) {
        this.pagBoletin = pagBoletin;
    }

    public String getTextoResumido() {
        return textoResumido;
    }

    public void setTextoResumido(String textoResumido) {
        this.textoResumido = textoResumido;
    }

    public String getTextoNorma() {
        return textoNorma;
    }

    public void setTextoNorma(String textoNorma) {
        this.textoNorma = textoNorma;
    }

    public String getTextoNormaActualizado() {
        return textoNormaActualizado;
    }

    public void setTextoNormaActualizado(String textoNormaActualizado) {
        this.textoNormaActualizado = textoNormaActualizado;
    }

    public String getEstado() {
        return estado;
    }

    public void setEstado(String estado) {
        this.estado = estado;
    }

    public String getPurifiedTextoNorma() {
        return purifiedTextoNorma;
    }

    public void setPurifiedTextoNorma(String purifiedTextoNorma) {
        this.purifiedTextoNorma = purifiedTextoNorma;
    }

    public String getPurifiedTextoNormaActualizado() {
        return purifiedTextoNormaActualizado;
    }

    public void setPurifiedTextoNormaActualizado(String purifiedTextoNormaActualizado) {
        this.purifiedTextoNormaActualizado = purifiedTextoNormaActualizado;
    }

    public String getEmbeddingModel() {
        return embeddingModel;
    }

    public void setEmbeddingModel(String embeddingModel) {
        this.embeddingModel = embeddingModel;
    }

    public String getEmbeddingSource() {
        return embeddingSource;
    }

    public void setEmbeddingSource(String embeddingSource) {
        this.embeddingSource = embeddingSource;
    }

    public LocalDateTime getEmbeddedAt() {
        return embeddedAt;
    }

    public void setEmbeddedAt(LocalDateTime embeddedAt) {
        this.embeddedAt = embeddedAt;
    }

    public String getEmbeddingType() {
        return embeddingType;
    }

    public void setEmbeddingType(String embeddingType) {
        this.embeddingType = embeddingType;
    }

    public String getLlmModelUsed() {
        return llmModelUsed;
    }

    public void setLlmModelUsed(String llmModelUsed) {
        this.llmModelUsed = llmModelUsed;
    }

    public Integer getLlmTokensUsed() {
        return llmTokensUsed;
    }

    public void setLlmTokensUsed(Integer llmTokensUsed) {
        this.llmTokensUsed = llmTokensUsed;
    }

    public Double getLlmProcessingTime() {
        return llmProcessingTime;
    }

    public void setLlmProcessingTime(Double llmProcessingTime) {
        this.llmProcessingTime = llmProcessingTime;
    }

    public Double getLlmSimilarityScore() {
        return llmSimilarityScore;
    }

    public void setLlmSimilarityScore(Double llmSimilarityScore) {
        this.llmSimilarityScore = llmSimilarityScore;
    }

    public StructuredTexto getStructuredTextoNorma() {
        return structuredTextoNorma;
    }

    public void setStructuredTextoNorma(StructuredTexto structuredTextoNorma) {
        this.structuredTextoNorma = structuredTextoNorma;
    }

    public StructuredTexto getStructuredTextoNormaActualizado() {
        return structuredTextoNormaActualizado;
    }

    public void setStructuredTextoNormaActualizado(StructuredTexto structuredTextoNormaActualizado) {
        this.structuredTextoNormaActualizado = structuredTextoNormaActualizado;
    }

    public List<NormaReferencia> getIdNormas() {
        return idNormas;
    }

    public void setIdNormas(List<NormaReferencia> idNormas) {
        this.idNormas = idNormas;
    }

    public List<Integer> getListaNormasQueComplementa() {
        return listaNormasQueComplementa;
    }

    public void setListaNormasQueComplementa(List<Integer> listaNormasQueComplementa) {
        this.listaNormasQueComplementa = listaNormasQueComplementa;
    }

    public List<Integer> getListaNormasQueLaComplementan() {
        return listaNormasQueLaComplementan;
    }

    public void setListaNormasQueLaComplementan(List<Integer> listaNormasQueLaComplementan) {
        this.listaNormasQueLaComplementan = listaNormasQueLaComplementan;
    }

    // Inner class for structured texto
    public static class StructuredTexto {
        @JsonProperty("divisions")
        private List<Division> divisions = new ArrayList<>();

        public StructuredTexto() {}

        public List<Division> getDivisions() {
            return divisions;
        }

        public void setDivisions(List<Division> divisions) {
            this.divisions = divisions != null ? divisions : new ArrayList<>();
        }

        public void addDivision(Division division) {
            if (this.divisions == null) {
                this.divisions = new ArrayList<>();
            }
            this.divisions.add(division);
        }
    }
}