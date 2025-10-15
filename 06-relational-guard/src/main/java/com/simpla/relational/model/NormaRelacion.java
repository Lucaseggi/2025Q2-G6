package com.simpla.relational.model;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class NormaRelacion {
    @JsonProperty("id")
    private Long id;

    @JsonProperty("norma_origen_infoleg_id")
    private Integer normaOrigenInfolegId;

    @JsonProperty("norma_destino_infoleg_id")
    private Integer normaDestinoInfolegId;

    @JsonProperty("tipo_relacion")
    private String tipoRelacion; // 'complementa' or 'complementada_por'

    public NormaRelacion() {}

    // Getters and setters
    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Integer getNormaOrigenInfolegId() {
        return normaOrigenInfolegId;
    }

    public void setNormaOrigenInfolegId(Integer normaOrigenInfolegId) {
        this.normaOrigenInfolegId = normaOrigenInfolegId;
    }

    public Integer getNormaDestinoInfolegId() {
        return normaDestinoInfolegId;
    }

    public void setNormaDestinoInfolegId(Integer normaDestinoInfolegId) {
        this.normaDestinoInfolegId = normaDestinoInfolegId;
    }

    public String getTipoRelacion() {
        return tipoRelacion;
    }

    public void setTipoRelacion(String tipoRelacion) {
        this.tipoRelacion = tipoRelacion;
    }
}
