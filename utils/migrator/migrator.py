#!/usr/bin/env python3
"""
S3 ↔ Postgres Migrator
Bidirectional sync utility for normas table data between S3 (JSON) and Postgres.
"""

import boto3
import psycopg2
import psycopg2.extras
import json
import argparse
import time
from pathlib import Path
from typing import List, Dict, Optional
from datetime import date, datetime
from botocore.exceptions import ClientError
import sys


class Migrator:
    def __init__(
        self,
        # Postgres config
        pg_host: str,
        pg_port: int,
        pg_database: str,
        pg_user: str,
        pg_password: str,
        # S3 config
        s3_bucket: str,
        s3_endpoint: Optional[str] = None,
        s3_access_key: Optional[str] = None,
        s3_secret_key: Optional[str] = None,
        s3_region: str = "us-east-1"
    ):
        # Initialize Postgres connection
        self.pg_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=pg_database,
            user=pg_user,
            password=pg_password
        )
        psycopg2.extras.register_default_jsonb(self.pg_conn)

        # Initialize S3 client
        session_kwargs = {'region_name': s3_region}
        if s3_access_key and s3_secret_key:
            session_kwargs['aws_access_key_id'] = s3_access_key
            session_kwargs['aws_secret_access_key'] = s3_secret_key

        session = boto3.Session(**session_kwargs)
        client_kwargs = {}
        if s3_endpoint:
            client_kwargs['endpoint_url'] = s3_endpoint

        self.s3_client = session.client('s3', **client_kwargs)
        self.s3_resource = session.resource('s3', **client_kwargs)
        self.bucket_name = s3_bucket
        self.bucket = self.s3_resource.Bucket(s3_bucket)

    def __del__(self):
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None
        if isinstance(date_str, date):
            return date_str
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            return None

    def _serialize_date(self, d: Optional[date]) -> Optional[str]:
        """Serialize date to ISO string."""
        if d is None:
            return None
        return d.isoformat() if isinstance(d, date) else str(d)

    def s3_to_postgres(self, batch_size: int = 100):
        """Migrate JSON objects from S3 norms/ to Postgres normas table."""
        cursor = self.pg_conn.cursor()

        try:
            objects = list(self.bucket.objects.filter(Prefix="norms/"))
            json_objects = [obj for obj in objects if obj.key.endswith('.json')]

            print(f"Found {len(json_objects)} JSON objects in S3")

            records_to_insert = []
            skipped = 0

            for obj in json_objects:
                try:
                    response = self.s3_client.get_object(Bucket=self.bucket_name, Key=obj.key)
                    content = response['Body'].read().decode('utf-8')
                    data = json.loads(content)

                    # Unwrap from cache format: data.scraping_data.infoleg_response
                    item = data.get('data', {}).get('scraping_data', {}).get('infoleg_response', {})

                    if not item or 'infoleg_id' not in item:
                        print(f"Warning: Skipping object without infoleg_id in {obj.key}")
                        skipped += 1
                        continue

                    record = (
                        item['infoleg_id'],
                        item.get('jurisdiccion'),
                        item.get('clase_norma'),
                        item.get('tipo_norma'),
                        self._parse_date(item.get('sancion')),
                        json.dumps(item.get('id_normas')) if item.get('id_normas') else None,
                        self._parse_date(item.get('publicacion')),
                        item.get('titulo_sumario'),
                        item.get('titulo_resumido'),
                        item.get('observaciones'),
                        item.get('nro_boletin'),
                        item.get('pag_boletin'),
                        item.get('texto_resumido'),
                        item.get('texto_norma'),
                        item.get('texto_norma_actualizado'),
                        item.get('estado'),
                        json.dumps(item.get('lista_normas_que_complementa')) if item.get('lista_normas_que_complementa') else None,
                        json.dumps(item.get('lista_normas_que_la_complementan')) if item.get('lista_normas_que_la_complementan') else None,
                    )
                    records_to_insert.append(record)

                except json.JSONDecodeError:
                    print(f"Warning: Failed to parse JSON from {obj.key}")
                    skipped += 1
                except Exception as e:
                    print(f"Error processing {obj.key}: {e}")
                    skipped += 1

            # Batch insert with conflict handling
            insert_query = """
                INSERT INTO normas (
                    infoleg_id, jurisdiccion, clase_norma, tipo_norma, sancion,
                    id_normas, publicacion, titulo_sumario, titulo_resumido,
                    observaciones, nro_boletin, pag_boletin, texto_resumido,
                    texto_norma, texto_norma_actualizado, estado,
                    lista_normas_que_complementa, lista_normas_que_la_complementan
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (infoleg_id) DO UPDATE SET
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
                    texto_norma = EXCLUDED.texto_norma,
                    texto_norma_actualizado = EXCLUDED.texto_norma_actualizado,
                    estado = EXCLUDED.estado,
                    lista_normas_que_complementa = EXCLUDED.lista_normas_que_complementa,
                    lista_normas_que_la_complementan = EXCLUDED.lista_normas_que_la_complementan
            """

            inserted = 0
            start_time = time.time()
            last_log_time = start_time

            for i in range(0, len(records_to_insert), batch_size):
                batch = records_to_insert[i:i + batch_size]
                cursor.executemany(insert_query, batch)
                inserted += len(batch)

                current_time = time.time()

                # Log every 10 seconds OR at milestones
                if (current_time - last_log_time >= 10) or (inserted % 10000 == 0) or (inserted == len(records_to_insert)):
                    elapsed = current_time - start_time
                    rate = inserted / elapsed if elapsed > 0 else 0
                    eta = (len(records_to_insert) - inserted) / rate if rate > 0 else 0
                    print(f"Progress: {inserted}/{len(records_to_insert)} ({inserted*100//len(records_to_insert)}%) | "
                          f"Rate: {rate:.1f} rec/s | Elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s")
                    last_log_time = current_time

            self.pg_conn.commit()
            elapsed_total = time.time() - start_time
            print(f"\n✓ Successfully migrated {inserted} records from S3 to Postgres in {elapsed_total:.1f}s")
            print(f"✗ Skipped: {skipped}")

        except Exception as e:
            self.pg_conn.rollback()
            print(f"Error during migration: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()

    def postgres_to_s3(self):
        """Export Postgres normas table to S3 norms/ as individual wrapped JSON files."""
        cursor = self.pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cursor.execute("SELECT * FROM normas ORDER BY id")
            records = cursor.fetchall()

            print(f"Found {len(records)} records in Postgres")

            exported = 0
            start_time = time.time()
            last_log_time = start_time

            for record in records:
                try:
                    item = dict(record)
                    # Remove auto-increment id field
                    item.pop('id', None)

                    item['sancion'] = self._serialize_date(item.get('sancion'))
                    item['publicacion'] = self._serialize_date(item.get('publicacion'))
                    if isinstance(item.get('id_normas'), str):
                        item['id_normas'] = json.loads(item['id_normas'])
                    if isinstance(item.get('lista_normas_que_complementa'), str):
                        item['lista_normas_que_complementa'] = json.loads(item['lista_normas_que_complementa'])
                    if isinstance(item.get('lista_normas_que_la_complementan'), str):
                        item['lista_normas_que_la_complementan'] = json.loads(item['lista_normas_que_la_complementan'])

                    # Wrap data in scraper's expected cache format
                    wrapped_data = {
                        "cached_at": datetime.now().isoformat(),
                        "cache_version": "1.0",
                        "data": {
                            "scraping_data": {
                                "infoleg_response": item,
                                "scraper_metadata": {
                                    "api_url": f"migrator://postgres/{item['infoleg_id']}",
                                    "scraper_version": "1.0",
                                    "has_full_text": bool(item.get('texto_norma')),
                                    "scraping_timestamp": datetime.now().isoformat(),
                                    "from_cache": False
                                }
                            }
                        }
                    }

                    key = f"norms/{item['infoleg_id']}.json"
                    self.s3_client.put_object(
                        Bucket=self.bucket_name,
                        Key=key,
                        Body=json.dumps(wrapped_data, indent=2, ensure_ascii=False).encode('utf-8'),
                        ContentType='application/json'
                    )
                    exported += 1

                    current_time = time.time()

                    # Log every 10 seconds OR at milestones
                    if (current_time - last_log_time >= 10) or (exported % 10000 == 0) or (exported == len(records)):
                        elapsed = current_time - start_time
                        rate = exported / elapsed if elapsed > 0 else 0
                        eta = (len(records) - exported) / rate if rate > 0 else 0
                        print(f"Progress: {exported}/{len(records)} ({exported*100//len(records)}%) | "
                              f"Rate: {rate:.1f} rec/s | Elapsed: {elapsed:.0f}s | ETA: {eta:.0f}s")
                        last_log_time = current_time

                except Exception as e:
                    print(f"Error exporting record {item.get('infoleg_id', 'unknown')}: {e}", file=sys.stderr)
                    continue

            elapsed_total = time.time() - start_time
            print(f"\n✓ Exported {exported} records to s3://{self.bucket_name}/norms/ in {elapsed_total:.1f}s")

        except Exception as e:
            print(f"Error during export: {e}", file=sys.stderr)
            raise
        finally:
            cursor.close()


def load_config() -> dict:
    """Load configuration from config.json if exists."""
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(description="S3 ↔ Postgres Migrator for normas table")
    parser.add_argument('direction', choices=['s3-to-pg', 'pg-to-s3'], help='Migration direction')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for s3-to-pg (default: 100)')

    args = parser.parse_args()
    config = load_config()

    pg_config = config.get('postgres', {})
    s3_config = config.get('s3', {})

    # Create migrator
    migrator = Migrator(
        pg_host=pg_config.get('host', 'localhost'),
        pg_port=pg_config.get('port', 5432),
        pg_database=pg_config.get('database', 'simpla'),
        pg_user=pg_config.get('user', 'postgres'),
        pg_password=pg_config.get('password', ''),
        s3_bucket=s3_config.get('bucket', 'simpla-scraper-storage'),
        s3_endpoint=s3_config.get('endpoint'),
        s3_access_key=s3_config.get('access_key'),
        s3_secret_key=s3_config.get('secret_key'),
        s3_region=s3_config.get('region', 'us-east-1')
    )

    # Execute migration
    if args.direction == 's3-to-pg':
        migrator.s3_to_postgres(batch_size=args.batch_size)
    else:
        migrator.postgres_to_s3()


if __name__ == "__main__":
    main()
