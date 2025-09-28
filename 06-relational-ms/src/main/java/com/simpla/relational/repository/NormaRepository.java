package com.simpla.relational.repository;

import com.simpla.relational.model.*;
import com.zaxxer.hikari.HikariDataSource;

import java.sql.*;
import java.sql.Date;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

public class NormaRepository {
    private final HikariDataSource dataSource;

    public NormaRepository(HikariDataSource dataSource) {
        this.dataSource = dataSource;
    }

    public static class InsertionResult {
        private Long normaId;
        private Map<String, Long> divisionPks;
        private Map<String, Long> articlePks;

        public InsertionResult() {
            this.divisionPks = new HashMap<>();
            this.articlePks = new HashMap<>();
        }

        public Long getNormaId() { return normaId; }
        public void setNormaId(Long normaId) { this.normaId = normaId; }

        public Map<String, Long> getDivisionPks() { return divisionPks; }
        public void setDivisionPks(Map<String, Long> divisionPks) { this.divisionPks = divisionPks; }

        public Map<String, Long> getArticlePks() { return articlePks; }
        public void setArticlePks(Map<String, Long> articlePks) { this.articlePks = articlePks; }

        public void addDivisionPk(String divisionKey, Long pk) {
            this.divisionPks.put(divisionKey, pk);
        }

        public void addArticlePk(String articleKey, Long pk) {
            this.articlePks.put(articleKey, pk);
        }
    }

    public Norma findByInfolegId(Integer infolegId) throws SQLException {
        String sql = """
            SELECT n.id, n.infoleg_id, n.jurisdiccion, n.clase_norma, n.tipo_norma,
                   n.sancion, n.publicacion, n.titulo_sumario, n.titulo_resumido,
                   n.observaciones, n.nro_boletin, n.pag_boletin, n.texto_resumido,
                   n.texto_norma, n.texto_norma_actualizado, n.estado,
                   n.purified_texto_norma, n.purified_texto_norma_actualizado,
                   n.embedding_model, n.embedding_source, n.embedded_at, n.embedding_type,
                   n.llm_model_used, n.llm_tokens_used, n.llm_processing_time, n.llm_similarity_score
            FROM normas_structured n
            WHERE n.infoleg_id = ?
            """;

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setInt(1, infolegId);

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    Norma norma = mapNormaFromResultSet(rs);

                    // Load structured divisions if we have a norma
                    if (norma != null) {
                        loadStructuredDivisions(norma, rs.getLong("id"));
                    }

                    return norma;
                }
            }
        }

        return null;
    }

    private Norma mapNormaFromResultSet(ResultSet rs) throws SQLException {
        Norma norma = new Norma();

        norma.setInfolegId(rs.getInt("infoleg_id"));
        norma.setJurisdiccion(rs.getString("jurisdiccion"));
        norma.setClaseNorma(rs.getString("clase_norma"));
        norma.setTipoNorma(rs.getString("tipo_norma"));

        Date sancionDate = rs.getDate("sancion");
        if (sancionDate != null) {
            norma.setSancion(sancionDate.toLocalDate());
        }

        Date publicacionDate = rs.getDate("publicacion");
        if (publicacionDate != null) {
            norma.setPublicacion(publicacionDate.toLocalDate());
        }

        norma.setTituloSumario(rs.getString("titulo_sumario"));
        norma.setTituloResumido(rs.getString("titulo_resumido"));
        norma.setObservaciones(rs.getString("observaciones"));
        norma.setNroBoletin(rs.getString("nro_boletin"));
        norma.setPagBoletin(rs.getString("pag_boletin"));
        norma.setTextoResumido(rs.getString("texto_resumido"));
        norma.setTextoNorma(rs.getString("texto_norma"));
        norma.setTextoNormaActualizado(rs.getString("texto_norma_actualizado"));
        norma.setEstado(rs.getString("estado"));
        norma.setPurifiedTextoNorma(rs.getString("purified_texto_norma"));
        norma.setPurifiedTextoNormaActualizado(rs.getString("purified_texto_norma_actualizado"));
        norma.setEmbeddingModel(rs.getString("embedding_model"));
        norma.setEmbeddingSource(rs.getString("embedding_source"));

        Timestamp embeddedAt = rs.getTimestamp("embedded_at");
        if (embeddedAt != null) {
            norma.setEmbeddedAt(embeddedAt.toLocalDateTime());
        }

        norma.setEmbeddingType(rs.getString("embedding_type"));
        norma.setLlmModelUsed(rs.getString("llm_model_used"));

        Integer llmTokens = rs.getInt("llm_tokens_used");
        if (!rs.wasNull()) {
            norma.setLlmTokensUsed(llmTokens);
        }

        Double processingTime = rs.getDouble("llm_processing_time");
        if (!rs.wasNull()) {
            norma.setLlmProcessingTime(processingTime);
        }

        Double similarityScore = rs.getDouble("llm_similarity_score");
        if (!rs.wasNull()) {
            norma.setLlmSimilarityScore(similarityScore);
        }

        return norma;
    }

    private void loadStructuredDivisions(Norma norma, Long normaId) throws SQLException {
        // Load all divisions for this norma
        List<Division> allDivisions = loadDivisionsForNorma(normaId);

        // Build hierarchical structure
        Map<Long, Division> divisionMap = new HashMap<>();
        List<Division> rootDivisions = new ArrayList<>();

        // First pass: create map and identify root divisions
        for (Division division : allDivisions) {
            divisionMap.put(division.getId(), division);
        }

        // Second pass: build hierarchy and load articles
        for (Division division : allDivisions) {
            // Load articles for this division
            loadArticlesForDivision(division, division.getId());

            // For now, we'll assume all divisions are root divisions
            // In a more complex scenario, you'd check parent_division_id
            rootDivisions.add(division);
        }

        // Set structured data on norma
        if (!rootDivisions.isEmpty()) {
            Norma.StructuredTexto structuredTexto = new Norma.StructuredTexto();
            structuredTexto.setDivisions(rootDivisions);
            norma.setStructuredTextoNorma(structuredTexto);
        }
    }

    private List<Division> loadDivisionsForNorma(Long normaId) throws SQLException {
        String sql = """
            SELECT d.id, d.name, d.ordinal, d.title, d.body, d.order_index
            FROM divisions d
            WHERE d.norma_id = ?
            ORDER BY d.order_index, d.id
            """;

        List<Division> divisions = new ArrayList<>();

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setLong(1, normaId);

            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    Division division = new Division();
                    division.setId(rs.getLong("id"));
                    division.setName(rs.getString("name"));
                    division.setOrdinal(rs.getString("ordinal"));
                    division.setTitle(rs.getString("title"));
                    division.setBody(rs.getString("body"));

                    Integer orderIndex = rs.getInt("order_index");
                    if (!rs.wasNull()) {
                        division.setOrderIndex(orderIndex);
                    }

                    divisions.add(division);
                }
            }
        }

        return divisions;
    }

    private void loadArticlesForDivision(Division division, Long divisionId) throws SQLException {
        String sql = """
            SELECT a.id, a.ordinal, a.body, a.order_index
            FROM articles a
            WHERE a.division_id = ?
            ORDER BY a.order_index, a.id
            """;

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setLong(1, divisionId);

            try (ResultSet rs = stmt.executeQuery()) {
                while (rs.next()) {
                    Article article = new Article();
                    article.setId(rs.getLong("id"));
                    article.setOrdinal(rs.getString("ordinal"));
                    article.setBody(rs.getString("body"));

                    Integer orderIndex = rs.getInt("order_index");
                    if (!rs.wasNull()) {
                        article.setOrderIndex(orderIndex);
                    }

                    division.addArticle(article);
                }
            }
        }
    }

    public Long insertNorma(Norma norma) throws SQLException {
        String sql = """
            INSERT INTO normas_structured (
                infoleg_id, jurisdiccion, clase_norma, tipo_norma, sancion, publicacion,
                titulo_sumario, titulo_resumido, observaciones, nro_boletin, pag_boletin,
                texto_resumido, texto_norma, texto_norma_actualizado, estado,
                purified_texto_norma, purified_texto_norma_actualizado,
                embedding_model, embedding_source, embedded_at, embedding_type,
                llm_model_used, llm_tokens_used, llm_processing_time, llm_similarity_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            RETURNING id
            """;

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setInt(1, norma.getInfolegId());
            stmt.setString(2, norma.getJurisdiccion());
            stmt.setString(3, norma.getClaseNorma());
            stmt.setString(4, norma.getTipoNorma());

            if (norma.getSancion() != null) {
                stmt.setDate(5, Date.valueOf(norma.getSancion()));
            } else {
                stmt.setNull(5, Types.DATE);
            }

            if (norma.getPublicacion() != null) {
                stmt.setDate(6, Date.valueOf(norma.getPublicacion()));
            } else {
                stmt.setNull(6, Types.DATE);
            }

            stmt.setString(7, norma.getTituloSumario());
            stmt.setString(8, norma.getTituloResumido());
            stmt.setString(9, norma.getObservaciones());
            stmt.setString(10, norma.getNroBoletin());
            stmt.setString(11, norma.getPagBoletin());
            stmt.setString(12, norma.getTextoResumido());
            stmt.setString(13, norma.getTextoNorma());
            stmt.setString(14, norma.getTextoNormaActualizado());
            stmt.setString(15, norma.getEstado());
            stmt.setString(16, norma.getPurifiedTextoNorma());
            stmt.setString(17, norma.getPurifiedTextoNormaActualizado());
            stmt.setString(18, norma.getEmbeddingModel());
            stmt.setString(19, norma.getEmbeddingSource());

            if (norma.getEmbeddedAt() != null) {
                stmt.setTimestamp(20, Timestamp.valueOf(norma.getEmbeddedAt()));
            } else {
                stmt.setNull(20, Types.TIMESTAMP);
            }

            stmt.setString(21, norma.getEmbeddingType());
            stmt.setString(22, norma.getLlmModelUsed());

            if (norma.getLlmTokensUsed() != null) {
                stmt.setInt(23, norma.getLlmTokensUsed());
            } else {
                stmt.setNull(23, Types.INTEGER);
            }

            if (norma.getLlmProcessingTime() != null) {
                stmt.setDouble(24, norma.getLlmProcessingTime());
            } else {
                stmt.setNull(24, Types.DOUBLE);
            }

            if (norma.getLlmSimilarityScore() != null) {
                stmt.setDouble(25, norma.getLlmSimilarityScore());
            } else {
                stmt.setNull(25, Types.DOUBLE);
            }

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    return rs.getLong(1);
                }
                throw new SQLException("Failed to get generated ID for norma");
            }
        }
    }

    public Long insertDivision(Long normaId, Division division) throws SQLException {
        String sql = """
            INSERT INTO divisions (norma_id, name, ordinal, title, body, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING id
            """;

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setLong(1, normaId);
            stmt.setString(2, division.getName());
            stmt.setString(3, division.getOrdinal());
            stmt.setString(4, division.getTitle());
            stmt.setString(5, division.getBody());

            if (division.getOrderIndex() != null) {
                stmt.setInt(6, division.getOrderIndex());
            } else {
                stmt.setNull(6, Types.INTEGER);
            }

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    Long divisionId = rs.getLong(1);
                    division.setId(divisionId);

                    // Note: Articles are inserted separately in insertDivisionsWithPks()
                    // to maintain proper PK tracking

                    return divisionId;
                }
                throw new SQLException("Failed to get generated ID for division");
            }
        }
    }

    public Long insertArticle(Long divisionId, Article article) throws SQLException {
        String sql = """
            INSERT INTO articles (division_id, ordinal, body, order_index)
            VALUES (?, ?, ?, ?)
            RETURNING id
            """;

        try (Connection conn = dataSource.getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {

            stmt.setLong(1, divisionId);
            stmt.setString(2, article.getOrdinal());
            stmt.setString(3, article.getBody());

            if (article.getOrderIndex() != null) {
                stmt.setInt(4, article.getOrderIndex());
            } else {
                stmt.setNull(4, Types.INTEGER);
            }

            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    Long articleId = rs.getLong(1);
                    article.setId(articleId);
                    return articleId;
                }
                throw new SQLException("Failed to get generated ID for article");
            }
        }
    }

    public Long insertCompleteNorma(Norma norma) throws SQLException {
        // Insert the norma first
        Long normaId = insertNorma(norma);

        // Insert structured divisions if present
        if (norma.getStructuredTextoNorma() != null &&
            norma.getStructuredTextoNorma().getDivisions() != null) {
            for (Division division : norma.getStructuredTextoNorma().getDivisions()) {
                insertDivision(normaId, division);
            }
        }

        if (norma.getStructuredTextoNormaActualizado() != null &&
            norma.getStructuredTextoNormaActualizado().getDivisions() != null) {
            for (Division division : norma.getStructuredTextoNormaActualizado().getDivisions()) {
                insertDivision(normaId, division);
            }
        }

        return normaId;
    }

    public InsertionResult insertCompleteNormaWithPks(Norma norma) throws SQLException {
        InsertionResult result = new InsertionResult();

        // Insert the norma first
        Long normaId = insertNorma(norma);
        result.setNormaId(normaId);

        // Insert structured divisions if present
        if (norma.getStructuredTextoNorma() != null &&
            norma.getStructuredTextoNorma().getDivisions() != null) {
            insertDivisionsWithPks(normaId, norma.getStructuredTextoNorma().getDivisions(), result, "texto_norma");
        }

        if (norma.getStructuredTextoNormaActualizado() != null &&
            norma.getStructuredTextoNormaActualizado().getDivisions() != null) {
            insertDivisionsWithPks(normaId, norma.getStructuredTextoNormaActualizado().getDivisions(), result, "texto_norma_actualizado");
        }

        return result;
    }

    private void insertDivisionsWithPks(Long normaId, List<Division> divisions, InsertionResult result, String source) throws SQLException {
        for (int i = 0; i < divisions.size(); i++) {
            Division division = divisions.get(i);
            Long divisionId = insertDivision(normaId, division);

            // Create a unique key for this division
            String divisionKey = String.format("%s_division_%d", source, i);
            result.addDivisionPk(divisionKey, divisionId);

            // Insert articles for this division
            if (division.getArticles() != null) {
                for (int j = 0; j < division.getArticles().size(); j++) {
                    Article article = division.getArticles().get(j);
                    Long articleId = insertArticle(divisionId, article);

                    // Create a unique key for this article
                    String articleKey = String.format("%s_division_%d_article_%d", source, i, j);
                    result.addArticlePk(articleKey, articleId);
                }
            }
        }
    }
}