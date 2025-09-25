from django.urls import path
from . import views

app_name = 'data_ingestion'

urlpatterns = [
    path('ingest/', views.ingest_norma, name='ingest_norma'),
    path('norma/<int:infoleg_id>/', views.delete_norma, name='delete_norma'),
    path('status/', views.ingestion_status, name='status'),
    # Debug endpoints
    path('debug/opensearch/', views.debug_opensearch_documents, name='debug_opensearch_documents'),
    path('debug/opensearch/stats/', views.debug_opensearch_stats, name='debug_opensearch_stats'),
    path('debug/opensearch/document/<str:document_id>/', views.debug_opensearch_document, name='debug_opensearch_document'),
]