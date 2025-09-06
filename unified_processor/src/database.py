"""Database management"""

import asyncio
import asyncpg
import logging
import json
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager

from .config import Config


class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.raw_pool: Optional[asyncpg.Pool] = None
        self.structured_pool: Optional[asyncpg.Pool] = None
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        """Initialize database connection pools"""
        self.logger.info("Initializing database connections...")
        
        # Wait for databases to be ready
        await self._wait_for_db('raw')
        await self._wait_for_db('structured')
        
        # Create connection pools
        raw_config = self.config.databases['raw']
        self.raw_pool = await asyncpg.create_pool(
            host=raw_config.host,
            port=raw_config.port,
            database=raw_config.dbname,
            user=raw_config.user,
            password=raw_config.password,
            min_size=5,
            max_size=20
        )
        
        structured_config = self.config.databases['structured']
        self.structured_pool = await asyncpg.create_pool(
            host=structured_config.host,
            port=structured_config.port,
            database=structured_config.dbname,
            user=structured_config.user,
            password=structured_config.password,
            min_size=5,
            max_size=20
        )
        
        self.logger.info("Database connections initialized")
    
    async def close(self):
        """Close database connection pools"""
        if self.raw_pool:
            await self.raw_pool.close()
        if self.structured_pool:
            await self.structured_pool.close()
    
    async def _wait_for_db(self, db_name: str, max_retries: int = 30):
        """Wait for database to be ready"""
        config = self.config.databases[db_name]
        
        for i in range(max_retries):
            try:
                conn = await asyncpg.connect(
                    host=config.host,
                    port=config.port,
                    database=config.dbname,
                    user=config.user,
                    password=config.password
                )
                await conn.close()
                self.logger.info(f"Database '{db_name}' is ready")
                return
            except Exception as e:
                self.logger.info(f"Waiting for database '{db_name}' (attempt {i+1}/{max_retries})")
                await asyncio.sleep(2)
        
        raise Exception(f"Could not connect to database '{db_name}' after {max_retries} attempts")
    
    @asynccontextmanager
    async def get_raw_connection(self):
        """Get connection from raw database pool"""
        async with self.raw_pool.acquire() as conn:
            yield conn
    
    @asynccontextmanager
    async def get_structured_connection(self):
        """Get connection from structured database pool"""
        async with self.structured_pool.acquire() as conn:
            yield conn
    
    async def get_unprocessed_norms(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get unprocessed norms from raw database"""
        # Get processed IDs from structured database
        processed_ids = set()
        try:
            async with self.get_structured_connection() as structured_conn:
                processed_query = """
                    SELECT source_id FROM processing_status 
                    WHERE status IN ('completed', 'failed_permanently')
                """
                processed_rows = await structured_conn.fetch(processed_query)
                processed_ids = {row['source_id'] for row in processed_rows}
        except Exception as e:
            # If structured DB is not ready or table doesn't exist, continue without filtering
            self.logger.warning(f"Could not check processing status: {e}")
        
        # Get norms from raw database, excluding processed ones and NULL text
        async with self.get_raw_connection() as conn:
            if processed_ids and len(processed_ids) < 1000:  # Avoid very large IN clauses
                # Create a safe NOT IN clause with explicit values
                processed_ids_list = list(processed_ids)
                placeholders = ','.join(['$' + str(i+3) for i in range(len(processed_ids_list))])
                query = f"""
                    SELECT * FROM normas 
                    WHERE id NOT IN ({placeholders})
                    AND (
                        (texto_norma IS NOT NULL AND texto_norma != '' AND LENGTH(texto_norma) <= 10000) 
                        OR 
                        (texto_norma_actualizado IS NOT NULL AND texto_norma_actualizado != '' AND LENGTH(texto_norma_actualizado) <= 10000)
                    )
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                """
                params = [limit, offset] + processed_ids_list
                rows = await conn.fetch(query, *params)
            else:
                # If no processed IDs or too many, get all norms with text content
                query = """
                    SELECT * FROM normas 
                    WHERE (
                        (texto_norma IS NOT NULL AND texto_norma != '' AND LENGTH(texto_norma) <= 10000) 
                        OR 
                        (texto_norma_actualizado IS NOT NULL AND texto_norma_actualizado != '' AND LENGTH(texto_norma_actualizado) <= 10000)
                    )
                    ORDER BY id
                    LIMIT $1 OFFSET $2
                """
                rows = await conn.fetch(query, limit, offset)
            
            return [dict(row) for row in rows]
    
    async def save_purified_norm(self, purified_data: Dict[str, Any]) -> bool:
        """Save purified norm data to raw database with all original fields"""
        async with self.get_raw_connection() as conn:
            query = """
                INSERT INTO normas_purified (
                    source_id, infoleg_id, jurisdiccion, clase_norma, tipo_norma,
                    sancion, id_normas, publicacion, titulo_sumario, titulo_resumido,
                    observaciones, nro_boletin, pag_boletin, estado,
                    lista_normas_que_complementa, lista_normas_que_la_complementan,
                    texto_resumido, texto_norma, texto_norma_actualizado,
                    purified_main_text, purified_updated_text, combined_text, 
                    text_length, ocr_fixes_applied,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 
                    $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, NOW(), NOW()
                )
                ON CONFLICT (source_id) 
                DO UPDATE SET
                    infoleg_id = EXCLUDED.infoleg_id,
                    jurisdiccion = EXCLUDED.jurisdiccion,
                    clase_norma = EXCLUDED.clase_norma,
                    tipo_norma = EXCLUDED.tipo_norma,
                    sancion = EXCLUDED.sancion,
                    id_normas = EXCLUDED.id_normas,
                    publicacion = EXCLUDED.publicacion,
                    titulo_sumario = EXCLUDED.titulo_sumario,
                    titulo_resumido = EXCLUDED.titulo_resumido,
                    observaciones = EXCLUDED.observaciones,
                    nro_boletin = EXCLUDED.nro_boletin,
                    pag_boletin = EXCLUDED.pag_boletin,
                    estado = EXCLUDED.estado,
                    lista_normas_que_complementa = EXCLUDED.lista_normas_que_complementa,
                    lista_normas_que_la_complementan = EXCLUDED.lista_normas_que_la_complementan,
                    texto_resumido = EXCLUDED.texto_resumido,
                    texto_norma = EXCLUDED.texto_norma,
                    texto_norma_actualizado = EXCLUDED.texto_norma_actualizado,
                    purified_main_text = EXCLUDED.purified_main_text,
                    purified_updated_text = EXCLUDED.purified_updated_text,
                    combined_text = EXCLUDED.combined_text,
                    text_length = EXCLUDED.text_length,
                    ocr_fixes_applied = EXCLUDED.ocr_fixes_applied,
                    updated_at = NOW()
            """
            
            await conn.execute(
                query,
                purified_data['source_id'],
                str(purified_data.get('infoleg_id')) if purified_data.get('infoleg_id') is not None else None,
                purified_data.get('jurisdiccion'),
                purified_data.get('clase_norma'),
                purified_data.get('tipo_norma'),
                purified_data.get('sancion'),
                json.dumps(purified_data.get('id_normas')),
                purified_data.get('publicacion'),
                purified_data.get('titulo_sumario'),
                purified_data.get('titulo_resumido'),
                purified_data.get('observaciones'),
                str(purified_data.get('nro_boletin')) if purified_data.get('nro_boletin') is not None else None,
                str(purified_data.get('pag_boletin')) if purified_data.get('pag_boletin') is not None else None,
                purified_data.get('estado'),
                json.dumps(purified_data.get('lista_normas_que_complementa')),
                json.dumps(purified_data.get('lista_normas_que_la_complementan')),
                purified_data.get('texto_resumido'),
                purified_data.get('texto_norma'),
                purified_data.get('texto_norma_actualizado'),
                purified_data.get('purified_main_text'),
                purified_data.get('purified_updated_text'),
                purified_data.get('combined_text'),
                purified_data.get('text_length', 0),
                purified_data.get('ocr_fixes_applied', [])
            )
            return True
    
    async def get_purified_norm(self, source_id: int) -> Optional[Dict[str, Any]]:
        """Get purified norm data"""
        async with self.get_raw_connection() as conn:
            query = "SELECT * FROM normas_purified WHERE source_id = $1"
            row = await conn.fetchrow(query, source_id)
            return dict(row) if row else None
    
    async def get_processing_status(self, source_id: int) -> Optional[Dict[str, Any]]:
        """Get processing status for a norm"""
        async with self.get_structured_connection() as conn:
            query = "SELECT * FROM processing_status WHERE source_id = $1"
            row = await conn.fetchrow(query, source_id)
            return dict(row) if row else None
    
    async def update_processing_status(
        self, 
        source_id: int, 
        status: str, 
        model_used: str = None, 
        attempts: int = 1,
        error_message: str = None,
        processing_time: float = None
    ):
        """Update processing status"""
        async with self.get_structured_connection() as conn:
            query = """
                INSERT INTO processing_status 
                (source_id, status, model_used, attempts, error_message, processing_time, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (source_id) 
                DO UPDATE SET
                    status = EXCLUDED.status,
                    model_used = EXCLUDED.model_used,
                    attempts = EXCLUDED.attempts,
                    error_message = EXCLUDED.error_message,
                    processing_time = EXCLUDED.processing_time,
                    updated_at = EXCLUDED.updated_at
            """
            await conn.execute(
                query, source_id, status, model_used, attempts, 
                error_message, processing_time
            )
    
    async def save_structured_norm(self, structured_data: Dict[str, Any]):
        """Save structured norm to database with all original metadata and quality control data"""
        async with self.get_structured_connection() as conn:
            # Convert the structured data to the database format
            query = """
                INSERT INTO normas_structured (
                    source_id, infoleg_id, jurisdiccion, clase_norma, tipo_norma,
                    sancion, id_normas, publicacion, titulo_sumario, titulo_resumido,
                    observaciones, nro_boletin, pag_boletin, texto_resumido, estado,
                    lista_normas_que_complementa, lista_normas_que_la_complementan,
                    texto_norma, texto_norma_actualizado,
                    purified_texto_norma, purified_texto_norma_actualizado,
                    ocr_fixes_applied,
                    llm_structured_json, text_similarity_score, content_diff,
                    quality_control_passed, human_intervention_required,
                    models_used, final_model_used, processing_notes,
                    created_at, updated_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, 
                    $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, NOW(), NOW()
                )
                ON CONFLICT (source_id) 
                DO UPDATE SET
                    infoleg_id = EXCLUDED.infoleg_id,
                    jurisdiccion = EXCLUDED.jurisdiccion,
                    clase_norma = EXCLUDED.clase_norma,
                    tipo_norma = EXCLUDED.tipo_norma,
                    sancion = EXCLUDED.sancion,
                    id_normas = EXCLUDED.id_normas,
                    publicacion = EXCLUDED.publicacion,
                    titulo_sumario = EXCLUDED.titulo_sumario,
                    titulo_resumido = EXCLUDED.titulo_resumido,
                    observaciones = EXCLUDED.observaciones,
                    nro_boletin = EXCLUDED.nro_boletin,
                    pag_boletin = EXCLUDED.pag_boletin,
                    texto_resumido = EXCLUDED.texto_resumido,
                    estado = EXCLUDED.estado,
                    lista_normas_que_complementa = EXCLUDED.lista_normas_que_complementa,
                    lista_normas_que_la_complementan = EXCLUDED.lista_normas_que_la_complementan,
                    texto_norma = EXCLUDED.texto_norma,
                    texto_norma_actualizado = EXCLUDED.texto_norma_actualizado,
                    purified_texto_norma = EXCLUDED.purified_texto_norma,
                    purified_texto_norma_actualizado = EXCLUDED.purified_texto_norma_actualizado,
                    ocr_fixes_applied = EXCLUDED.ocr_fixes_applied,
                    llm_structured_json = EXCLUDED.llm_structured_json,
                    text_similarity_score = EXCLUDED.text_similarity_score,
                    content_diff = EXCLUDED.content_diff,
                    quality_control_passed = EXCLUDED.quality_control_passed,
                    human_intervention_required = EXCLUDED.human_intervention_required,
                    models_used = EXCLUDED.models_used,
                    final_model_used = EXCLUDED.final_model_used,
                    processing_notes = EXCLUDED.processing_notes,
                    updated_at = NOW()
            """
            
            await conn.execute(
                query,
                structured_data['source_id'],
                str(structured_data.get('infoleg_id')) if structured_data.get('infoleg_id') is not None else None,
                structured_data.get('jurisdiccion'),
                structured_data.get('clase_norma'),
                structured_data.get('tipo_norma'),
                structured_data.get('sancion'),
                json.dumps(structured_data.get('id_normas')),
                structured_data.get('publicacion'),
                structured_data.get('titulo_sumario'),
                structured_data.get('titulo_resumido'),
                structured_data.get('observaciones'),
                str(structured_data.get('nro_boletin')) if structured_data.get('nro_boletin') is not None else None,
                str(structured_data.get('pag_boletin')) if structured_data.get('pag_boletin') is not None else None,
                structured_data.get('texto_resumido'),
                structured_data.get('estado'),
                json.dumps(structured_data.get('lista_normas_que_complementa')),
                json.dumps(structured_data.get('lista_normas_que_la_complementan')),
                # Original and purified text fields
                structured_data.get('texto_norma'),
                structured_data.get('texto_norma_actualizado'),
                structured_data.get('purified_texto_norma'),
                structured_data.get('purified_texto_norma_actualizado'),
                # Purification metadata
                structured_data.get('ocr_fixes_applied', []),
                # LLM and quality control fields
                json.dumps(structured_data.get('llm_structured_json')),
                structured_data.get('text_similarity_score'),
                structured_data.get('content_diff'),
                structured_data.get('quality_control_passed', False),
                structured_data.get('human_intervention_required', False),
                structured_data.get('models_used', []),
                structured_data.get('final_model_used'),
                structured_data.get('processing_notes', '')
            )
    
    async def get_processing_stats(self) -> Dict[str, int]:
        """Get processing statistics"""
        try:
            async with self.get_structured_connection() as conn:
                query = """
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM processing_status
                    GROUP BY status
                """
                rows = await conn.fetch(query)
                stats = {row['status']: row['count'] for row in rows}
        except Exception as e:
            # If structured DB is not ready or table doesn't exist, start with empty stats
            self.logger.warning(f"Could not get processing status stats: {e}")
            stats = {}
        
        # Get total count from raw database
        try:
            async with self.get_raw_connection() as raw_conn:
                total_query = "SELECT COUNT(*) as total FROM normas"
                total_row = await raw_conn.fetchrow(total_query)
                total_count = total_row['total'] if total_row else 0
        except Exception as e:
            self.logger.warning(f"Could not get total norm count: {e}")
            total_count = 0
        
        # Calculate derived statistics
        stats['total'] = total_count
        processed_count = sum(stats.get(status, 0) for status in ['completed', 'failed_permanently', 'processing', 'failed'])
        stats['pending'] = max(0, total_count - processed_count)
        
        # Ensure we have default values for key metrics
        stats.setdefault('completed', 0)
        stats.setdefault('failed', 0)
        stats.setdefault('processing', 0)
        stats.setdefault('failed_permanently', 0)
        
        return stats