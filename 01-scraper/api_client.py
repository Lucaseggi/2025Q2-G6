import os
import requests
import time
import logging
from datetime import date, datetime
from typing import Dict, Any, Optional, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ApiClientConfig:
    """Configuration for the API client"""

    base_url: str
    rate_limit_delay: float
    max_retries: int
    timeout: int
    user_agent: str
    verify_ssl: bool = True

    @classmethod
    def from_env(cls):
        """Create configuration from environment variables"""
        return cls(
            base_url=os.getenv('INFOLEG_BASE_URL'),
            rate_limit_delay=float(os.getenv('API_RATE_LIMIT_DELAY', '1.5')),
            max_retries=int(os.getenv('API_MAX_RETRIES', '3')),
            timeout=int(os.getenv('API_TIMEOUT', '30')),
            user_agent=os.getenv('API_USER_AGENT', 'InfoLeg-Data-Extraction/2.0'),
            verify_ssl=os.getenv('API_VERIFY_SSL', 'true').lower() == 'true',
        )


class ApiClient:
    """Generic API client for InfoLEG services with configurable endpoints"""

    def __init__(self, config: ApiClientConfig = None):
        self.config = config or ApiClientConfig.from_env()
        self.session = requests.Session()
        self.session.headers.update(
            {'User-Agent': self.config.user_agent, 'Accept': 'application/json'}
        )

        # Configure SSL verification
        self.session.verify = self.config.verify_ssl
        if not self.config.verify_ssl:
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Load URL endpoints from environment
        self._load_endpoints()

    def _load_endpoints(self):
        """Load API endpoints from environment variables"""
        self.endpoints = {
            'norms_by_year': os.getenv(
                'INFOLEG_NORMS_BY_YEAR_ENDPOINT', '/nacionales/normativos/legislaciones'
            ),
            'norm_details': os.getenv(
                'INFOLEG_NORM_DETAILS_ENDPOINT', '/nacionales/normativos'
            ),
        }

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make rate-limited request with retries"""
        for attempt in range(self.config.max_retries):
            try:
                time.sleep(self.config.rate_limit_delay)
                logger.info(f"Making request to: {url}")

                response = self.session.get(
                    url, params=params, timeout=self.config.timeout
                )
                response.raise_for_status()

                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Request failed (attempt {attempt + 1}/{self.config.max_retries}): {e}"
                )
                if attempt == self.config.max_retries - 1:
                    raise
                time.sleep(2**attempt)  # Exponential backoff

    def get_norms_by_year(
        self, year: int, limit: int = 50
    ) -> Generator[Dict[str, Any], None, None]:
        """Get all norms for a specific year with pagination"""
        offset = 1

        while True:
            url = f"{self.config.base_url}{self.endpoints['norms_by_year']}"
            params = {'sancion': year, 'limit': limit, 'offset': offset}

            try:
                data = self._make_request(url, params)

                if not data.get('results'):
                    break

                logger.info(f"Retrieved {len(data['results'])} norms (offset {offset})")

                for norm in data['results']:
                    yield norm

                # Check if we've reached the end
                metadata = data.get('metadata', {}).get('resultset', {})
                count = metadata.get('count', 0)

                if count < limit:
                    break

                offset += limit

            except Exception as e:
                logger.error(
                    f"Error retrieving norms for year {year}, offset {offset}: {e}"
                )
                break

    def get_norm_details(self, norm_id: int) -> Optional[Dict[str, Any]]:
        """Get full details for a specific norm"""
        url = f"{self.config.base_url}{self.endpoints['norm_details']}"
        params = {'id': norm_id}

        try:
            return self._make_request(url, params)
        except Exception as e:
            logger.error(f"Error retrieving details for norm {norm_id}: {e}")
            return None

    def parse_norm_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
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
            'lista_normas_que_complementa': api_response.get(
                'listaNormasQueComplementa', []
            ),
            'lista_normas_que_la_complementan': api_response.get(
                'listaNormasQueLaComplementan', []
            ),
        }

    def get_config_info(self) -> Dict[str, Any]:
        """Get current configuration information"""
        return {
            'base_url': self.config.base_url,
            'rate_limit_delay': self.config.rate_limit_delay,
            'max_retries': self.config.max_retries,
            'timeout': self.config.timeout,
            'user_agent': self.config.user_agent,
            'verify_ssl': self.config.verify_ssl,
            'endpoints': self.endpoints,
        }
