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

    def s3_to_postgres(self, prefix: str = "", dry_run: bool = False, batch_size: int = 100):
        """
        Migrate JSON objects from S3 to Postgres normas table.

        Args:
            prefix: S3 key prefix to filter objects
            dry_run: If True, only show what would be migrated without inserting
            batch_size: Number of records to insert per batch
        """
        cursor = self.pg_conn.cursor()

        try:
            objects = list(self.bucket.objects.filter(Prefix=prefix))
            json_objects = [obj for obj in objects if obj.key.endswith('.json')]

            print(f"Found {len(json_objects)} JSON objects in S3")

            records_to_insert = []
            skipped = 0

            for obj in json_objects:
                try:
                    response = self.s3_client.get_object(Bucket=self.bucket_name, Key=obj.key)
                    content = response['Body'].read().decode('utf-8')
                    data = json.loads(content)

                    # Handle both single object and array of objects
                    items = data if isinstance(data, list) else [data]

                    for item in items:
                        if 'infoleg_id' not in item:
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

            if dry_run:
                print(f"\nDRY RUN: Would insert {len(records_to_insert)} records")
                print(f"Skipped: {skipped}")
                return

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

    def postgres_to_s3(self, prefix: str = "export/", format: str = "single", dry_run: bool = False):
        """
        Export Postgres normas table to S3 as JSON.

        Args:
            prefix: S3 key prefix for exported files
            format: 'single' (one file) or 'multiple' (one file per record)
            dry_run: If True, only show what would be exported without uploading
        """
        cursor = self.pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        try:
            cursor.execute("SELECT * FROM normas ORDER BY id")
            records = cursor.fetchall()

            print(f"Found {len(records)} records in Postgres")

            if dry_run:
                print(f"\nDRY RUN: Would export {len(records)} records to S3 with prefix '{prefix}'")
                return

            if format == "single":
                # Export all records to a single JSON file
                data = []
                for record in records:
                    item = dict(record)
                    # Serialize dates and handle jsonb
                    item['sancion'] = self._serialize_date(item.get('sancion'))
                    item['publicacion'] = self._serialize_date(item.get('publicacion'))
                    if isinstance(item.get('id_normas'), str):
                        item['id_normas'] = json.loads(item['id_normas'])
                    if isinstance(item.get('lista_normas_que_complementa'), str):
                        item['lista_normas_que_complementa'] = json.loads(item['lista_normas_que_complementa'])
                    if isinstance(item.get('lista_normas_que_la_complementan'), str):
                        item['lista_normas_que_la_complementan'] = json.loads(item['lista_normas_que_la_complementan'])
                    data.append(item)

                key = f"{prefix}normas_export_{datetime.now().isoformat()}.json"
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'),
                    ContentType='application/json'
                )
                print(f"Exported {len(records)} records to s3://{self.bucket_name}/{key}")

            else:  # multiple files
                exported = 0
                start_time = time.time()
                last_log_time = start_time

                for record in records:
                    try:
                        item = dict(record)
                        item['sancion'] = self._serialize_date(item.get('sancion'))
                        item['publicacion'] = self._serialize_date(item.get('publicacion'))
                        if isinstance(item.get('id_normas'), str):
                            item['id_normas'] = json.loads(item['id_normas'])
                        if isinstance(item.get('lista_normas_que_complementa'), str):
                            item['lista_normas_que_complementa'] = json.loads(item['lista_normas_que_complementa'])
                        if isinstance(item.get('lista_normas_que_la_complementan'), str):
                            item['lista_normas_que_la_complementan'] = json.loads(item['lista_normas_que_la_complementan'])

                        key = f"{prefix}{item['infoleg_id']}.json"
                        self.s3_client.put_object(
                            Bucket=self.bucket_name,
                            Key=key,
                            Body=json.dumps(item, indent=2, ensure_ascii=False).encode('utf-8'),
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
                print(f"\n✓ Exported {exported} records to s3://{self.bucket_name}/{prefix} in {elapsed_total:.1f}s")

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
    parser = argparse.ArgumentParser(
        description="S3 ↔ Postgres Migrator for normas table",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('direction', choices=['s3-to-pg', 'pg-to-s3'],
                        help='Migration direction')
    parser.add_argument('bucket', help='S3 bucket name')

    # Postgres config
    parser.add_argument('--pg-host', help='Postgres host')
    parser.add_argument('--pg-port', type=int, help='Postgres port')
    parser.add_argument('--pg-database', help='Postgres database')
    parser.add_argument('--pg-user', help='Postgres user')
    parser.add_argument('--pg-password', help='Postgres password')

    # S3 config
    parser.add_argument('--s3-endpoint', help='S3 endpoint URL')
    parser.add_argument('--s3-access-key', help='S3 access key')
    parser.add_argument('--s3-secret-key', help='S3 secret key')
    parser.add_argument('--s3-region', help='S3 region')

    # Operation config
    parser.add_argument('--prefix', default='', help='S3 key prefix')
    parser.add_argument('--format', choices=['single', 'multiple'], default='single',
                        help='Export format for pg-to-s3 (default: single)')
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Batch size for s3-to-pg (default: 100)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without executing')
    parser.add_argument('--no-config', action='store_true',
                        help='Do not load config.json')

    args = parser.parse_args()

    # Load config and merge with CLI args
    config = {} if args.no_config else load_config()

    pg_config = config.get('postgres', {})
    s3_config = config.get('s3', {})

    # Create migrator
    migrator = Migrator(
        pg_host=args.pg_host or pg_config.get('host', 'localhost'),
        pg_port=args.pg_port or pg_config.get('port', 5432),
        pg_database=args.pg_database or pg_config.get('database', 'simpla_rag'),
        pg_user=args.pg_user or pg_config.get('user', 'postgres'),
        pg_password=args.pg_password or pg_config.get('password', ''),
        s3_bucket=args.bucket,
        s3_endpoint=args.s3_endpoint or s3_config.get('endpoint'),
        s3_access_key=args.s3_access_key or s3_config.get('access_key'),
        s3_secret_key=args.s3_secret_key or s3_config.get('secret_key'),
        s3_region=args.s3_region or s3_config.get('region', 'us-east-1')
    )

    # Execute migration
    if args.direction == 's3-to-pg':
        migrator.s3_to_postgres(prefix=args.prefix, dry_run=args.dry_run, batch_size=args.batch_size)
    else:
        migrator.postgres_to_s3(prefix=args.prefix, format=args.format, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
