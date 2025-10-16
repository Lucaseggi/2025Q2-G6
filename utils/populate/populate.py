#!/usr/bin/env python3
"""
Populate Script - Process Norms by titulo_sumario
Queries the Postgres database for norms matching specific titulo_sumario values
and processes them through the RAG pipeline.
"""

import psycopg2
import psycopg2.extras
import requests
import time
import argparse
import sys
from typing import List, Optional
from datetime import datetime


class NormProcessor:
    """Process norms from Postgres database through the API pipeline."""

    # Target titulo_sumario values to process
    TARGET_TITULOS = [
        'ADUANAS',
        'IMPORTACIONES',
        'COMERCIO EXTERIOR',
        'SERVICIOS ADUANEROS',
        'SERVICIO EXTERIOR',
        'TARIFAS',
        'EXPORTACIONES',
        'ARANCELES'
    ]

    def __init__(
        self,
        api_url: str = "http://localhost:8003/process",
        pg_host: str = "localhost",
        pg_port: int = 5432,
        pg_database: str = "simpla_rag",
        pg_user: str = "postgres",
        pg_password: str = "postgres",
        delay: int = 10,
        force: bool = False
    ):
        self.api_url = api_url
        self.delay = delay
        self.force = force

        # Initialize Postgres connection
        try:
            self.pg_conn = psycopg2.connect(
                host=pg_host,
                port=pg_port,
                database=pg_database,
                user=pg_user,
                password=pg_password
            )
            print(f"✓ Connected to Postgres at {pg_host}:{pg_port}/{pg_database}")
        except Exception as e:
            print(f"✗ Failed to connect to Postgres: {e}", file=sys.stderr)
            sys.exit(1)

    def __del__(self):
        if hasattr(self, 'pg_conn'):
            self.pg_conn.close()

    def fetch_norms_by_titulo_sumario(self) -> List[tuple]:
        """
        Query normas table for norms matching target titulo_sumario values.
        Returns list of (infoleg_id, titulo_sumario) tuples.
        """
        cursor = self.pg_conn.cursor()

        try:
            # Build query with parameterized placeholders
            placeholders = ','.join(['%s'] * len(self.TARGET_TITULOS))
            query = f"""
                SELECT infoleg_id, titulo_sumario, tipo_norma
                FROM normas
                WHERE titulo_sumario IN ({placeholders})
                ORDER BY infoleg_id
            """

            cursor.execute(query, self.TARGET_TITULOS)
            results = cursor.fetchall()

            print(f"✓ Found {len(results)} norms matching target titulo_sumario values")
            return results

        except Exception as e:
            print(f"✗ Error querying database: {e}", file=sys.stderr)
            return []
        finally:
            cursor.close()

    def process_norm(self, infoleg_id: int) -> tuple[bool, int, Optional[str]]:
        """
        Process a single norm through the API.
        Returns (success, http_code, response_text).
        """
        try:
            response = requests.post(
                self.api_url,
                json={"infoleg_id": infoleg_id, "force": self.force},
                headers={"Content-Type": "application/json"},
                timeout=300  # 5 minute timeout
            )

            success = response.status_code == 200
            return success, response.status_code, response.text

        except requests.exceptions.Timeout:
            return False, 0, "Request timed out"
        except requests.exceptions.ConnectionError:
            return False, 0, "Connection error"
        except Exception as e:
            return False, 0, str(e)

    def run(self):
        """Main processing loop."""
        print("=" * 80)
        print("Processing Norms by titulo_sumario")
        print("=" * 80)
        print(f"API Endpoint:    {self.api_url}")
        print(f"Force reprocess: {self.force}")
        print(f"Delay:           {self.delay}s between requests")
        print(f"Target titles:   {', '.join(self.TARGET_TITULOS)}")
        print()

        # Fetch norms from database
        norms = self.fetch_norms_by_titulo_sumario()

        if not norms:
            print("No norms found to process.")
            return

        print()
        print("=" * 80)
        print("Starting Processing")
        print("=" * 80)
        print()

        # Statistics
        total = len(norms)
        success = 0
        failed = 0
        start_time = time.time()

        # Process each norm
        for idx, (infoleg_id, titulo_sumario, tipo_norma) in enumerate(norms, 1):
            print(f"[{idx}/{total}] Processing norm {infoleg_id} "
                  f"({tipo_norma or 'N/A'} - {titulo_sumario})... ", end='', flush=True)

            is_success, http_code, response_text = self.process_norm(infoleg_id)

            if is_success:
                print("✓ SUCCESS")
                success += 1
            else:
                print(f"✗ FAILED (HTTP {http_code})")
                if response_text and len(response_text) < 200:
                    print(f"   Error: {response_text}")
                failed += 1

            # Delay between requests (except on last one)
            if idx < total:
                time.sleep(self.delay)

        # Print summary
        elapsed_time = time.time() - start_time
        elapsed_minutes = int(elapsed_time // 60)
        elapsed_seconds = int(elapsed_time % 60)

        print()
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total:        {total}")
        print(f"Success:      {success}")
        print(f"Failed:       {failed}")
        print(f"Success rate: {(success/total)*100:.2f}%")
        print(f"Time elapsed: {elapsed_minutes}m {elapsed_seconds}s")
        print(f"Avg per norm: {elapsed_time/total:.1f}s")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Process norms from Postgres database by titulo_sumario"
    )

    # API configuration
    parser.add_argument(
        '--api-url',
        default='http://localhost:8003/process',
        help='Process API endpoint (default: http://localhost:8003/process)'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=10,
        help='Delay in seconds between API requests (default: 10)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing of already processed norms'
    )

    # Postgres configuration
    parser.add_argument(
        '--pg-host',
        default='localhost',
        help='Postgres host (default: localhost)'
    )
    parser.add_argument(
        '--pg-port',
        type=int,
        default=5432,
        help='Postgres port (default: 5432)'
    )
    parser.add_argument(
        '--pg-database',
        default='simpla_rag',
        help='Postgres database (default: simpla_rag)'
    )
    parser.add_argument(
        '--pg-user',
        default='postgres',
        help='Postgres user (default: postgres)'
    )
    parser.add_argument(
        '--pg-password',
        default='postgres',
        help='Postgres password (default: postgres)'
    )

    args = parser.parse_args()

    # Create processor and run
    processor = NormProcessor(
        api_url=args.api_url,
        pg_host=args.pg_host,
        pg_port=args.pg_port,
        pg_database=args.pg_database,
        pg_user=args.pg_user,
        pg_password=args.pg_password,
        delay=args.delay,
        force=args.force
    )

    processor.run()


if __name__ == "__main__":
    main()
