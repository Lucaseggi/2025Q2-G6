import sys
import os
import logging
import requests
import time
from datetime import date, datetime
from typing import Optional, Dict, Any

# Add shared modules to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))
from models import InfolegApiResponse

from ..interfaces.norm_provider_interface import NormProviderInterface
from ..config.settings import Settings

logger = logging.getLogger(__name__)


class InfolegNormProvider(NormProviderInterface):
    """InfoLeg API norm provider implementation"""

    def __init__(self, settings: Settings):
        """Initialize InfoLeg data source"""
        self.settings = settings

        # Initialize HTTP session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': settings.infoleg_api.user_agent,
            'Accept': 'application/json'
        })
        self.session.verify = settings.infoleg_api.verify_ssl

        if not settings.infoleg_api.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _make_request(self, url: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """Make rate-limited request with retries"""
        for attempt in range(self.settings.infoleg_api.max_retries):
            try:
                time.sleep(self.settings.infoleg_api.rate_limit_delay)
                logger.debug(f"Making request to: {url}")

                response = self.session.get(
                    url, params=params, timeout=self.settings.infoleg_api.timeout
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}/{self.settings.infoleg_api.max_retries}): {e}")
                if attempt == self.settings.infoleg_api.max_retries - 1:
                    return None
                time.sleep(2**attempt)  # Exponential backoff

        return None

    def _parse_norm_response(self, api_response: Dict[str, Any]) -> InfolegApiResponse:
        """Parse API response to create InfolegApiResponse with Spanish field names"""
        def parse_date(date_str: str) -> Optional[date]:
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return None

        # Create InfolegApiResponse with Spanish field names from API
        return InfolegApiResponse(
            infoleg_id=api_response.get('id'),
            jurisdiccion=api_response.get('jurisdiccion'),
            clase_norma=api_response.get('claseNorma'),
            tipo_norma=api_response.get('tipoNorma'),
            sancion=parse_date(api_response.get('sancion')),
            id_normas=api_response.get('idNormas', []),
            publicacion=parse_date(api_response.get('publicacion')),
            titulo_sumario=api_response.get('tituloSumario'),
            titulo_resumido=api_response.get('tituloResumido'),
            observaciones=api_response.get('observaciones'),
            nro_boletin=api_response.get('nroBoletin'),
            pag_boletin=api_response.get('pagBoletin'),
            texto_resumido=api_response.get('textoResumido'),
            texto_norma=api_response.get('textoNorma'),
            texto_norma_actualizado=api_response.get('textoNormaActualizado'),
            estado=api_response.get('estado'),
            lista_normas_que_complementa=api_response.get('listaNormasQueComplementa', []),
            lista_normas_que_la_complementan=api_response.get('listaNormasQueLaComplementan', [])
        )

    def get_norm_by_id(self, norm_id: int) -> Optional[InfolegApiResponse]:
        """Retrieve a specific norm by its ID"""
        try:
            logger.debug(f"Fetching norm {norm_id} from InfoLeg API")

            # Get detailed information for this specific norm
            url = f"{self.settings.infoleg_api.base_url}{self.settings.infoleg_api.endpoints.norm_details}"
            params = {'id': norm_id}

            detailed_norm = self._make_request(url, params)
            if not detailed_norm:
                logger.error(f"Could not retrieve details for norm {norm_id}")
                return None

            # Parse the norm data (now returns InfolegApiResponse directly)
            norm = self._parse_norm_response(detailed_norm)
            if not norm:
                logger.error(f"Could not parse norm data for norm {norm_id}")
                return None

            logger.debug(f"Successfully retrieved norm {norm_id}")
            return norm

        except Exception as e:
            logger.error(f"Error retrieving norm {norm_id} from InfoLeg: {e}")
            return None

    def is_available(self) -> bool:
        """Check if the data source is available"""
        try:
            # Try a simple API call to check availability
            url = f"{self.settings.infoleg_api.base_url}{self.settings.infoleg_api.endpoints.norm_details}"
            response = self.session.get(url, timeout=5)
            return response.status_code < 500  # Server errors indicate unavailability
        except Exception as e:
            logger.error(f"InfoLeg data source not available: {e}")
            return False