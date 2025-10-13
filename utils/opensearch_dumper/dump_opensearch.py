#!/usr/bin/env python3
"""
OpenSearch Vector Database Dumper

Exports ALL documents from OpenSearch including embeddings to various formats:
- NDJSON (newline-delimited JSON) - best for full data with vectors
- CSV (embeddings as JSON strings) - for spreadsheet analysis
- Parquet - compressed columnar format for large datasets

Usage:
    python dump_opensearch.py --format ndjson --output dump.ndjson
    python dump_opensearch.py --format csv --output dump.csv
    python dump_opensearch.py --format parquet --output dump.parquet
"""

import argparse
import json
import csv
import sys
import time
from typing import Iterator, Dict, Any
from datetime import datetime

try:
    from opensearchpy import OpenSearch
    from opensearchpy.helpers import scan
except ImportError:
    print("ERROR: opensearch-py not installed")
    print("Install with: pip install opensearch-py")
    sys.exit(1)


class OpenSearchDumper:
    """Dumps OpenSearch indices to various formats"""

    def __init__(self, host: str = "localhost", port: int = 9200, index: str = "documents"):
        """Initialize OpenSearch connection"""
        self.index = index
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            timeout=60,
            max_retries=3,
            retry_on_timeout=True
        )

    def test_connection(self) -> bool:
        """Test if OpenSearch is reachable"""
        try:
            info = self.client.info()
            print(f"✓ Connected to OpenSearch {info['version']['number']}")

            # Check if index exists
            if not self.client.indices.exists(index=self.index):
                print(f"✗ ERROR: Index '{self.index}' does not exist")
                return False

            # Get document count
            count = self.client.count(index=self.index)['count']
            print(f"✓ Index '{self.index}' has {count:,} documents")
            return True

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False

    def iter_all_documents(self) -> Iterator[Dict[str, Any]]:
        """
        Iterate over ALL documents using scroll API.
        This is memory-efficient and works with millions of documents.
        """
        print(f"\n⏳ Starting document export from '{self.index}'...")
        start_time = time.time()
        count = 0

        try:
            # Use scroll API to efficiently iterate over all documents
            for hit in scan(
                self.client,
                index=self.index,
                query={"query": {"match_all": {}}},
                scroll='5m',  # Keep scroll context alive for 5 minutes
                size=1000,    # Fetch 1000 docs per batch
                preserve_order=False  # Faster without ordering
            ):
                count += 1

                # Combine metadata and source
                doc = {
                    '_id': hit['_id'],
                    '_index': hit['_index'],
                    **hit['_source']
                }

                yield doc

                # Progress indicator
                if count % 1000 == 0:
                    elapsed = time.time() - start_time
                    rate = count / elapsed
                    print(f"  Exported {count:,} documents ({rate:.1f} docs/sec)")

        except Exception as e:
            print(f"\n✗ ERROR during export: {e}")
            raise

        finally:
            elapsed = time.time() - start_time
            print(f"\n✓ Export complete: {count:,} documents in {elapsed:.1f}s ({count/elapsed:.1f} docs/sec)")

    def dump_to_ndjson(self, output_file: str):
        """
        Export to newline-delimited JSON (NDJSON).
        Best format for preserving all data including vectors.
        Can be imported back to OpenSearch using bulk API.
        """
        print(f"\n📝 Dumping to NDJSON: {output_file}")

        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in self.iter_all_documents():
                # Write each document as a single JSON line
                json.dump(doc, f, ensure_ascii=False)
                f.write('\n')

        print(f"✓ NDJSON export complete: {output_file}")

    def dump_to_csv(self, output_file: str):
        """
        Export to CSV format.
        Embeddings are serialized as JSON strings.
        Good for analysis in Excel/spreadsheets (for smaller datasets).
        """
        print(f"\n📊 Dumping to CSV: {output_file}")

        first_doc = True
        fieldnames = None

        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = None

            for doc in self.iter_all_documents():
                # Flatten nested structures and serialize embeddings
                flat_doc = self._flatten_document(doc)

                # Initialize CSV writer with fieldnames from first document
                if first_doc:
                    fieldnames = list(flat_doc.keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    first_doc = False

                # Write row (missing fields will be empty)
                writer.writerow(flat_doc)

        print(f"✓ CSV export complete: {output_file}")

    def dump_to_parquet(self, output_file: str):
        """
        Export to Apache Parquet format.
        Highly compressed columnar format, excellent for large datasets.
        Requires pyarrow: pip install pyarrow
        """
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except ImportError:
            print("✗ ERROR: pyarrow not installed")
            print("Install with: pip install pyarrow")
            return

        print(f"\n🗜️  Dumping to Parquet: {output_file}")

        # Collect all documents (for large datasets, use batching)
        documents = []
        for doc in self.iter_all_documents():
            flat_doc = self._flatten_document(doc)
            documents.append(flat_doc)

        # Convert to PyArrow Table and write
        table = pa.Table.from_pylist(documents)
        pq.write_table(table, output_file, compression='snappy')

        file_size_mb = open(output_file, 'rb').seek(0, 2) / (1024 * 1024)
        print(f"✓ Parquet export complete: {output_file} ({file_size_mb:.1f} MB)")

    def _flatten_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested document structure for CSV/Parquet.
        Converts lists/dicts to JSON strings.
        """
        flat = {}

        for key, value in doc.items():
            if isinstance(value, (list, dict)):
                # Serialize complex types to JSON strings
                flat[key] = json.dumps(value, ensure_ascii=False)
            elif value is None:
                flat[key] = ''
            else:
                flat[key] = value

        return flat


def main():
    parser = argparse.ArgumentParser(
        description='Export OpenSearch vector database to file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export to NDJSON (recommended for full data preservation)
  python dump_opensearch.py --format ndjson --output embeddings_dump.ndjson

  # Export to CSV (for spreadsheet analysis)
  python dump_opensearch.py --format csv --output embeddings_dump.csv

  # Export to Parquet (compressed, best for large datasets)
  python dump_opensearch.py --format parquet --output embeddings_dump.parquet

  # Custom OpenSearch connection
  python dump_opensearch.py --host opensearch --port 9200 --index documents --format ndjson --output dump.ndjson
        """
    )

    parser.add_argument('--host', default='localhost', help='OpenSearch host (default: localhost)')
    parser.add_argument('--port', type=int, default=9200, help='OpenSearch port (default: 9200)')
    parser.add_argument('--index', default='documents', help='Index name (default: documents)')
    parser.add_argument('--format', choices=['ndjson', 'csv', 'parquet'], required=True,
                       help='Output format')
    parser.add_argument('--output', required=True, help='Output file path')

    args = parser.parse_args()

    print("=" * 80)
    print("OpenSearch Vector Database Dumper")
    print("=" * 80)
    print(f"Host: {args.host}:{args.port}")
    print(f"Index: {args.index}")
    print(f"Format: {args.format}")
    print(f"Output: {args.output}")
    print("=" * 80)

    # Initialize dumper
    dumper = OpenSearchDumper(host=args.host, port=args.port, index=args.index)

    # Test connection
    if not dumper.test_connection():
        sys.exit(1)

    # Perform dump
    try:
        if args.format == 'ndjson':
            dumper.dump_to_ndjson(args.output)
        elif args.format == 'csv':
            dumper.dump_to_csv(args.output)
        elif args.format == 'parquet':
            dumper.dump_to_parquet(args.output)

        print("\n" + "=" * 80)
        print("✓ EXPORT SUCCESSFUL")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n✗ Export cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
