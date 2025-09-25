from django.db import models


class NormaStructured(models.Model):
    """Main table for structured normas with all metadata"""

    # Basic norm information
    infoleg_id = models.IntegerField(unique=True, db_index=True)
    jurisdiccion = models.CharField(max_length=255, null=True, blank=True)
    clase_norma = models.CharField(max_length=255, null=True, blank=True)
    tipo_norma = models.CharField(max_length=255, null=True, blank=True)
    sancion = models.DateField(null=True, blank=True)
    id_normas = models.JSONField(null=True, blank=True)
    publicacion = models.DateField(null=True, blank=True)
    titulo_sumario = models.TextField(null=True, blank=True)
    titulo_resumido = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    nro_boletin = models.CharField(max_length=255, null=True, blank=True)
    pag_boletin = models.CharField(max_length=255, null=True, blank=True)
    texto_resumido = models.TextField(null=True, blank=True)
    texto_norma = models.TextField(null=True, blank=True)
    texto_norma_actualizado = models.TextField(null=True, blank=True)
    estado = models.CharField(max_length=255, null=True, blank=True)
    lista_normas_que_complementa = models.JSONField(null=True, blank=True)
    lista_normas_que_la_complementan = models.JSONField(null=True, blank=True)

    # Processed text fields
    purified_texto_norma = models.TextField(null=True, blank=True)
    purified_texto_norma_actualizado = models.TextField(null=True, blank=True)

    # Embedding metadata (no vectors stored here)
    embedding_model = models.CharField(max_length=255, null=True, blank=True)
    embedding_source = models.CharField(max_length=255, null=True, blank=True)
    embedded_at = models.DateTimeField(null=True, blank=True)
    embedding_type = models.CharField(max_length=255, null=True, blank=True)

    # LLM processing metadata
    llm_model_used = models.CharField(max_length=255, null=True, blank=True)
    llm_models_used = models.JSONField(null=True, blank=True)
    llm_tokens_used = models.IntegerField(null=True, blank=True)
    llm_processing_time = models.FloatField(null=True, blank=True)
    llm_similarity_score = models.FloatField(null=True, blank=True)

    # System timestamps
    inserted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'normas_structured'
        indexes = [
            models.Index(fields=['infoleg_id']),
            models.Index(fields=['inserted_at']),
            models.Index(fields=['embedding_type']),
        ]

    def __str__(self):
        return f"Norma {self.infoleg_id} - {self.titulo_resumido or 'Sin título'}"


class Division(models.Model):
    """Divisions within a norma - can be recursive"""

    norma = models.ForeignKey(NormaStructured, on_delete=models.CASCADE, related_name='divisions')
    parent_division = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_divisions')

    name = models.CharField(max_length=255, null=True, blank=True)
    ordinal = models.CharField(max_length=50, null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    body = models.TextField(null=True, blank=True)
    order_index = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'divisions'
        indexes = [
            models.Index(fields=['norma', 'order_index']),
            models.Index(fields=['parent_division']),
        ]
        ordering = ['order_index']

    def __str__(self):
        return f"{self.name or 'División'} - {self.ordinal or 'S/N'}"


class Article(models.Model):
    """Articles within divisions - can also be recursive"""

    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='articles')
    parent_article = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_articles')

    ordinal = models.CharField(max_length=50, null=True, blank=True)
    body = models.TextField()
    order_index = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'articles'
        indexes = [
            models.Index(fields=['division', 'order_index']),
            models.Index(fields=['parent_article']),
        ]
        ordering = ['order_index']

    def __str__(self):
        return f"Art. {self.ordinal or 'S/N'}"