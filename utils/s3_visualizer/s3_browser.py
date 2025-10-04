#!/usr/bin/env python3
"""
S3 Browser - A utility for browsing and visualizing S3 bucket contents.
Supports both local (MinIO/LocalStack) and remote S3 connections.
"""

import boto3
import json
import argparse
import os
from pathlib import Path
from typing import Optional, List, Dict
from botocore.exceptions import ClientError
import sys


class S3Browser:
    def __init__(
        self,
        bucket_name: str,
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1"
    ):
        """
        Initialize S3 Browser.

        Args:
            bucket_name: Name of the S3 bucket
            endpoint_url: S3 endpoint URL (for local S3 like MinIO)
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region_name: AWS region name
        """
        self.bucket_name = bucket_name

        session_kwargs = {
            'region_name': region_name
        }

        if aws_access_key_id and aws_secret_access_key:
            session_kwargs['aws_access_key_id'] = aws_access_key_id
            session_kwargs['aws_secret_access_key'] = aws_secret_access_key

        session = boto3.Session(**session_kwargs)

        client_kwargs = {}
        if endpoint_url:
            client_kwargs['endpoint_url'] = endpoint_url

        self.s3_client = session.client('s3', **client_kwargs)
        self.s3_resource = session.resource('s3', **client_kwargs)
        self.bucket = self.s3_resource.Bucket(bucket_name)

    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[Dict]:
        """
        List objects in the bucket with optional prefix filter.

        Args:
            prefix: Filter objects by prefix
            max_keys: Maximum number of objects to return

        Returns:
            List of object metadata dictionaries
        """
        objects = []
        try:
            for obj in self.bucket.objects.filter(Prefix=prefix).limit(max_keys):
                objects.append({
                    'key': obj.key,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'storage_class': obj.storage_class
                })
        except ClientError as e:
            print(f"Error listing objects: {e}", file=sys.stderr)
            return []

        return objects

    def get_object_content(self, key: str) -> Optional[str]:
        """
        Get the content of an object from S3.

        Args:
            key: Object key

        Returns:
            Object content as string, or None if error
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
            content = response['Body'].read().decode('utf-8')
            return content
        except ClientError as e:
            print(f"Error getting object {key}: {e}", file=sys.stderr)
            return None
        except UnicodeDecodeError:
            print(f"Error: Object {key} is not a text file", file=sys.stderr)
            return None

    def display_object(self, key: str, format: str = "auto"):
        """
        Display object content with appropriate formatting.

        Args:
            key: Object key
            format: Display format (auto, json, text)
        """
        content = self.get_object_content(key)
        if content is None:
            return

        print(f"\n{'='*80}")
        print(f"Object: {key}")
        print(f"{'='*80}\n")

        # Auto-detect format
        if format == "auto":
            if key.endswith('.json'):
                format = "json"
            else:
                format = "text"

        # Display with formatting
        if format == "json":
            try:
                parsed = json.loads(content)
                print(json.dumps(parsed, indent=2, ensure_ascii=False))
            except json.JSONDecodeError:
                print("Warning: Failed to parse as JSON, displaying as text")
                print(content)
        else:
            print(content)

        print(f"\n{'='*80}\n")

    def scan(self, prefix: str = "", max_keys: int = 1000):
        """
        Scan and display all objects in the bucket.

        Args:
            prefix: Filter objects by prefix
            max_keys: Maximum number of objects to scan
        """
        objects = self.list_objects(prefix, max_keys)

        if not objects:
            print(f"No objects found in bucket '{self.bucket_name}' with prefix '{prefix}'")
            return

        print(f"\nFound {len(objects)} objects in bucket '{self.bucket_name}':")
        print(f"\n{'Index':<8} {'Key':<50} {'Size (bytes)':<15} {'Last Modified':<30}")
        print("-" * 103)

        for idx, obj in enumerate(objects, 1):
            size_str = f"{obj['size']:,}"
            print(f"{idx:<8} {obj['key']:<50} {size_str:<15} {obj['last_modified']:<30}")

        print(f"\nTotal objects: {len(objects)}")

    def interactive_browse(self, prefix: str = "", max_keys: int = 1000):
        """
        Interactive browsing mode.

        Args:
            prefix: Initial prefix filter
            max_keys: Maximum number of objects to display
        """
        while True:
            objects = self.list_objects(prefix, max_keys)

            if not objects:
                print(f"\nNo objects found with prefix '{prefix}'")
                prefix = input("Enter new prefix (or 'q' to quit): ").strip()
                if prefix.lower() == 'q':
                    break
                continue

            print(f"\n{'='*80}")
            print(f"Browsing bucket: {self.bucket_name} | Prefix: '{prefix}'")
            print(f"{'='*80}\n")
            print(f"{'Index':<8} {'Key':<50} {'Size (bytes)':<15}")
            print("-" * 73)

            for idx, obj in enumerate(objects, 1):
                size_str = f"{obj['size']:,}"
                key_display = obj['key'][:47] + "..." if len(obj['key']) > 50 else obj['key']
                print(f"{idx:<8} {key_display:<50} {size_str:<15}")

            print(f"\nTotal: {len(objects)} objects")
            print("\nCommands:")
            print("  [number] - View object by index")
            print("  p [prefix] - Change prefix filter")
            print("  r - Refresh")
            print("  q - Quit")

            command = input("\nEnter command: ").strip()

            if command.lower() == 'q':
                break
            elif command.lower() == 'r':
                continue
            elif command.lower().startswith('p '):
                prefix = command[2:].strip()
                continue
            elif command.isdigit():
                idx = int(command) - 1
                if 0 <= idx < len(objects):
                    self.display_object(objects[idx]['key'])
                    input("Press Enter to continue...")
                else:
                    print(f"Invalid index. Please enter a number between 1 and {len(objects)}")
                    input("Press Enter to continue...")
            else:
                print("Invalid command")
                input("Press Enter to continue...")


def load_config() -> dict:
    """Load configuration from config.json if it exists."""
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}


def main():
    parser = argparse.ArgumentParser(
        description="S3 Browser - Browse and visualize S3 bucket contents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Browse LocalStack bucket (uses config.json by default)
  python s3_browser.py my-bucket

  # Browse with custom endpoint
  python s3_browser.py my-bucket --endpoint http://localhost:9000 --access-key minioadmin --secret-key minioadmin

  # Browse AWS S3 bucket (uses AWS credentials from environment/config)
  python s3_browser.py my-bucket --no-config

  # Scan bucket with prefix filter
  python s3_browser.py my-bucket --prefix data/ --scan

  # View specific object
  python s3_browser.py my-bucket --view data/file.json

  # Interactive mode
  python s3_browser.py my-bucket --interactive
        """
    )

    parser.add_argument('bucket', help='S3 bucket name')
    parser.add_argument('--endpoint', help='S3 endpoint URL (for local S3)')
    parser.add_argument('--access-key', help='AWS access key ID')
    parser.add_argument('--secret-key', help='AWS secret access key')
    parser.add_argument('--region', help='AWS region')
    parser.add_argument('--no-config', action='store_true', help='Do not load config.json')
    parser.add_argument('--prefix', default='', help='Object key prefix filter')
    parser.add_argument('--max-keys', type=int, default=1000, help='Maximum objects to list (default: 1000)')

    # Operation modes
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--scan', action='store_true', help='Scan and list all objects')
    mode_group.add_argument('--view', metavar='KEY', help='View specific object content')
    mode_group.add_argument('--interactive', '-i', action='store_true', help='Interactive browsing mode')

    parser.add_argument('--format', choices=['auto', 'json', 'text'], default='auto',
                        help='Display format for object content (default: auto)')

    args = parser.parse_args()

    # Load config and merge with command line args
    config = {} if args.no_config else load_config()

    endpoint = args.endpoint or config.get('endpoint')
    access_key = args.access_key or config.get('access_key')
    secret_key = args.secret_key or config.get('secret_key')
    region = args.region or config.get('region', 'us-east-1')

    # Create browser instance
    browser = S3Browser(
        bucket_name=args.bucket,
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )

    # Execute requested operation
    if args.view:
        browser.display_object(args.view, args.format)
    elif args.scan:
        browser.scan(args.prefix, args.max_keys)
    elif args.interactive:
        browser.interactive_browse(args.prefix, args.max_keys)
    else:
        # Default to interactive mode
        browser.interactive_browse(args.prefix, args.max_keys)


if __name__ == "__main__":
    main()
