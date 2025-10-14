from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import date
import json

@dataclass
class InfolegApiResponse:
    infoleg_id: int
    jurisdiccion: Optional[str]
    clase_norma: Optional[str]
    tipo_norma: Optional[str]
    sancion: Optional[date]
    id_normas: Optional[List[Dict[str, Any]]]
    publicacion: Optional[date]
    titulo_sumario: Optional[str]
    titulo_resumido: Optional[str]
    observaciones: Optional[str]
    nro_boletin: Optional[str]
    pag_boletin: Optional[str]
    texto_resumido: Optional[str]
    texto_norma: Optional[str]
    texto_norma_actualizado: Optional[str]
    estado: Optional[str]
    lista_normas_que_complementa: Optional[List[Dict[str, Any]]]
    lista_normas_que_la_complementan: Optional[List[Dict[str, Any]]]

@dataclass
class ScraperMetadata:
    api_url: str
    scraper_version: str
    has_full_text: bool
    scraping_timestamp: str
    from_cache: bool

@dataclass
class ScrapingData:
    infoleg_response: InfolegApiResponse
    scraper_metadata: ScraperMetadata

@dataclass
class ProcessorMetadata:
    model_used: str
    tokens_used: int
    processing_timestamp: str

@dataclass
class EmbedderMetadata:
    embedding_model_used: str
    embedding_tokens_used: int
    embedding_timestamp: str

@dataclass
class ParsedText:
    structured_data: Optional[Dict[str, Any]]
    embeddings: Optional[List[float]] = None

@dataclass
class ProcessingData:
    purifications: Dict[str, str]  # {"original_text": "...", "updated_text": "..."}
    parsings: Dict[str, ParsedText]  # {"original_text": ParsedText, "updated_text": ParsedText}
    processor_metadata: ProcessorMetadata
    embedder_metadata: Optional[EmbedderMetadata] = None

@dataclass
class ProcessedData:
    scraping_data: ScrapingData
    processing_data: Optional[ProcessingData] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert dates to ISO format strings in InfolegApiResponse
        if 'scraping_data' in data and data['scraping_data']:
            if 'infoleg_response' in data['scraping_data']:
                response = data['scraping_data']['infoleg_response']
                if response.get('sancion'):
                    response['sancion'] = response['sancion'].isoformat()
                if response.get('publicacion'):
                    response['publicacion'] = response['publicacion'].isoformat()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedData':
        # Handle nested structures
        if 'scraping_data' in data and isinstance(data['scraping_data'], dict):
            scraping_data = data['scraping_data']

            # Handle InfolegApiResponse dates
            if 'infoleg_response' in scraping_data and isinstance(scraping_data['infoleg_response'], dict):
                response_data = scraping_data['infoleg_response']
                if isinstance(response_data.get('sancion'), str):
                    response_data['sancion'] = date.fromisoformat(response_data['sancion'])
                if isinstance(response_data.get('publicacion'), str):
                    response_data['publicacion'] = date.fromisoformat(response_data['publicacion'])
                scraping_data['infoleg_response'] = InfolegApiResponse(**response_data)

            # Handle ScraperMetadata
            if 'scraper_metadata' in scraping_data and isinstance(scraping_data['scraper_metadata'], dict):
                scraping_data['scraper_metadata'] = ScraperMetadata(**scraping_data['scraper_metadata'])

            data['scraping_data'] = ScrapingData(**scraping_data)

        # Handle ProcessingData
        if 'processing_data' in data and isinstance(data['processing_data'], dict):
            processing_data = data['processing_data']

            # Handle ParsedText objects
            if 'parsings' in processing_data and isinstance(processing_data['parsings'], dict):
                for key, value in processing_data['parsings'].items():
                    if isinstance(value, dict):
                        processing_data['parsings'][key] = ParsedText(**value)

            # Handle ProcessorMetadata
            if 'processor_metadata' in processing_data and isinstance(processing_data['processor_metadata'], dict):
                processing_data['processor_metadata'] = ProcessorMetadata(**processing_data['processor_metadata'])

            # Handle EmbedderMetadata
            if 'embedder_metadata' in processing_data and isinstance(processing_data['embedder_metadata'], dict):
                processing_data['embedder_metadata'] = EmbedderMetadata(**processing_data['embedder_metadata'])

            data['processing_data'] = ProcessingData(**processing_data)

        return cls(**data)

