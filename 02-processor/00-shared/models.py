from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import date
import json

@dataclass
class InfolegNorma:
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
    purified_texto_norma: Optional[str]
    purified_texto_norma_actualizado: Optional[str]
    structured_texto_norma: Optional[Dict[str, Any]]
    structured_texto_norma_actualizado: Optional[Dict[str, Any]]
    # LLM processing metadata
    llm_model_used: Optional[str] = None
    llm_models_used: Optional[List[str]] = None
    llm_tokens_used: Optional[int] = None
    llm_processing_time: Optional[float] = None
    llm_similarity_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert dates to ISO format strings
        if data.get('sancion'):
            data['sancion'] = data['sancion'].isoformat()
        if data.get('publicacion'):
            data['publicacion'] = data['publicacion'].isoformat()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InfolegNorma':
        # Convert date strings back to date objects if needed
        if isinstance(data.get('sancion'), str):
            data['sancion'] = date.fromisoformat(data['sancion'])
        if isinstance(data.get('publicacion'), str):
            data['publicacion'] = date.fromisoformat(data['publicacion'])
        return cls(**data)

@dataclass
class ScrapedData:
    norma: InfolegNorma
    api_url: str
    metadata: Dict[str, Any]
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert the norma to a dict with proper date handling
        if hasattr(self, 'norma') and self.norma:
            data['norma'] = self.norma.to_dict()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScrapedData':
        if 'norma' in data and isinstance(data['norma'], dict):
            data['norma'] = InfolegNorma.from_dict(data['norma'])
        return cls(**data)

@dataclass
class ProcessedData:
    norma: InfolegNorma
    processing_timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert the norma to a dict with proper date handling
        if hasattr(self, 'norma') and self.norma:
            data['norma'] = self.norma.to_dict()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessedData':
        if 'norma' in data and isinstance(data['norma'], dict):
            data['norma'] = InfolegNorma.from_dict(data['norma'])
        return cls(**data)

@dataclass 
class EmbeddedData:
    norma: InfolegNorma
    embedding: List[float]
    embedding_model: str
    embedded_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert the norma to a dict with proper date handling
        if hasattr(self, 'norma') and self.norma:
            data['norma'] = self.norma.to_dict()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddedData':
        if 'norma' in data and isinstance(data['norma'], dict):
            data['norma'] = InfolegNorma.from_dict(data['norma'])
        return cls(**data)