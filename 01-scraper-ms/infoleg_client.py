import requests
import time
import logging
from datetime import date, datetime
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class InfolegConfig:
    base_url: str = "https://servicios.infoleg.gob.ar/infolegInternet/api/v2.0"
    rate_limit_delay: float = 1.0  # seconds between requests
    max_retries: int = 3
    timeout: int = 30

class InfolegClient:
    def __init__(self, config: InfolegConfig = None):
        self.config = config or InfolegConfig()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'InfoLeg-Data-Extraction/1.0',
            'Accept': 'application/json'
        })
        # Disable SSL verification for testing (not recommended for production)
        self.session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make rate-limited request with retries"""
        for attempt in range(self.config.max_retries):
            try:
                time.sleep(self.config.rate_limit_delay)
                logger.info(f"Making request to: {url}")
                
                response = self.session.get(
                    url, 
                    params=params,
                    timeout=self.config.timeout
                )
                response.raise_for_status()
                
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}")
                if attempt == self.config.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff
    
    def get_normas_by_year(self, year: int, limit: int = 50) -> Generator[Dict[str, Any], None, None]:
        """Get all normas for a specific year with pagination"""
        offset = 1
        
        while True:
            url = f"{self.config.base_url}/nacionales/normativos/legislaciones"
            params = {
                'sancion': year,
                'limit': limit,
                'offset': offset
            }
            
            try:
                data = self._make_request(url, params)
                
                if not data.get('results'):
                    break
                    
                logger.info(f"Retrieved {len(data['results'])} normas (offset {offset})")
                
                for norma in data['results']:
                    yield norma
                
                # Check if we've reached the end
                metadata = data.get('metadata', {}).get('resultset', {})
                count = metadata.get('count', 0)
                
                if count < limit:
                    break
                    
                offset += limit
                
            except Exception as e:
                logger.error(f"Error retrieving normas for year {year}, offset {offset}: {e}")
                break
    
    def get_norma_details(self, norma_id: int) -> Optional[Dict[str, Any]]:
        """Get full details for a specific norma"""
        url = f"{self.config.base_url}/nacionales/normativos"
        params = {'id': norma_id}
        
        try:
            return self._make_request(url, params)
        except Exception as e:
            logger.error(f"Error retrieving details for norma {norma_id}: {e}")
            return None
    
    def parse_norma_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse API response to match our database schema"""
        
        def parse_date(date_str: str) -> Optional[date]:
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None
        
        return {
            'infoleg_id': api_response.get('id'),
            'jurisdiccion': api_response.get('jurisdiccion'),
            'clase_norma': api_response.get('claseNorma'),
            'tipo_norma': api_response.get('tipoNorma'),
            'sancion': parse_date(api_response.get('sancion')),
            'id_normas': api_response.get('idNormas', []),
            'publicacion': parse_date(api_response.get('publicacion')),
            'titulo_sumario': api_response.get('tituloSumario'),
            'titulo_resumido': api_response.get('tituloResumido'),
            'observaciones': api_response.get('observaciones'),
            'nro_boletin': api_response.get('nroBoletin'),
            'pag_boletin': api_response.get('pagBoletin'),
            'texto_resumido': api_response.get('textoResumido'),
            'texto_norma': api_response.get('textoNorma'),
            'texto_norma_actualizado': api_response.get('textoNormaActualizado'),
            'estado': api_response.get('estado'),
            'lista_normas_que_complementa': api_response.get('listaNormasQueComplementa', []),
            'lista_normas_que_la_complementan': api_response.get('listaNormasQueLaComplementan', [])
        }