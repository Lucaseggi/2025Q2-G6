package com.simpla.relational.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class NormaReferencia {
    @JsonProperty("id")
    private Long id;

    @JsonProperty("norma_id")
    private Long normaId;

    @JsonProperty("numero")
    private Integer numero;

    @JsonProperty("dependencia")
    private String dependencia;

    @JsonProperty("rama_digesto")
    private String ramaDigesto;

    public NormaReferencia() {}

    // Getters and setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getNormaId() {
        return normaId;
    }

    public void setNormaId(Long normaId) {
        this.normaId = normaId;
    }

    public Integer getNumero() {
        return numero;
    }

    public void setNumero(Integer numero) {
        this.numero = numero;
    }

    public String getDependencia() {
        return dependencia;
    }

    public void setDependencia(String dependencia) {
        this.dependencia = dependencia;
    }

    public String getRamaDigesto() {
        return ramaDigesto;
    }

    public void setRamaDigesto(String ramaDigesto) {
        this.ramaDigesto = ramaDigesto;
    }
}
