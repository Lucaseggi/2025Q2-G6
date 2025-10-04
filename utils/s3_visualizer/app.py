#!/usr/bin/env python3
"""
S3 Web Browser - Web interface for browsing and viewing S3 bucket contents.
"""

import boto3
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from botocore.exceptions import ClientError

app = Flask(__name__)

# Load configuration
def load_config():
    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

config = load_config()

# Initialize S3 client
s3_client = boto3.client(
    's3',
    endpoint_url=config.get('endpoint', 'http://localhost:4566'),
    aws_access_key_id=config.get('access_key', 'test'),
    aws_secret_access_key=config.get('secret_key', 'test'),
    region_name=config.get('region', 'us-east-1')
)

BUCKET_NAME = config.get('bucket', 'simpla-cache')


@app.route('/')
def index():
    """Main page - file browser."""
    return render_template('index.html', bucket_name=BUCKET_NAME)


@app.route('/api/list')
def list_objects():
    """API endpoint to list objects with optional prefix - returns paginated results."""
    prefix = request.args.get('prefix', '')
    bucket = request.args.get('bucket', BUCKET_NAME)
    continuation_token = request.args.get('continuation_token')
    max_keys = int(request.args.get('max_keys', 500))

    try:
        params = {
            'Bucket': bucket,
            'Prefix': prefix,
            'Delimiter': '/',
            'MaxKeys': max_keys
        }

        if continuation_token:
            params['ContinuationToken'] = continuation_token

        response = s3_client.list_objects_v2(**params)

        folders = []
        files = []

        # Get "folders" (common prefixes)
        if 'CommonPrefixes' in response:
            for prefix_obj in response['CommonPrefixes']:
                folder_name = prefix_obj['Prefix'].rstrip('/')
                if prefix:
                    folder_name = folder_name[len(prefix):].lstrip('/')

                folders.append({
                    'name': folder_name,
                    'type': 'folder',
                    'full_path': prefix_obj['Prefix']
                })

        # Get files
        if 'Contents' in response:
            for obj in response['Contents']:
                # Skip the prefix itself if it's returned
                if obj['Key'] == prefix or obj['Key'].endswith('/'):
                    continue

                file_name = obj['Key']
                if prefix:
                    file_name = file_name[len(prefix):].lstrip('/')

                files.append({
                    'name': file_name,
                    'type': 'file',
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'full_path': obj['Key']
                })

        return jsonify({
            'success': True,
            'prefix': prefix,
            'folders': folders,
            'files': files,
            'has_more': response.get('IsTruncated', False),
            'next_token': response.get('NextContinuationToken')
        })

    except ClientError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search')
def search_objects():
    """API endpoint to search for files using exact prefix matching."""
    query = request.args.get('query', '')
    current_prefix = request.args.get('prefix', '')
    bucket = request.args.get('bucket', BUCKET_NAME)
    max_keys = int(request.args.get('max_keys', 500))

    if not query:
        return jsonify({'success': False, 'error': 'Query parameter required'}), 400

    try:
        # Combine current prefix with search query for exact prefix matching
        search_prefix = current_prefix + query if current_prefix else query

        params = {
            'Bucket': bucket,
            'Prefix': search_prefix,
            'MaxKeys': max_keys
        }

        response = s3_client.list_objects_v2(**params)

        folders = []
        files = []

        # Get "folders" (common prefixes)
        if 'CommonPrefixes' in response:
            for prefix_obj in response['CommonPrefixes']:
                folder_name = prefix_obj['Prefix'].rstrip('/')
                if current_prefix:
                    folder_name = folder_name[len(current_prefix):].lstrip('/')

                folders.append({
                    'name': folder_name,
                    'type': 'folder',
                    'full_path': prefix_obj['Prefix']
                })

        # Get files
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith('/'):
                    continue

                file_name = obj['Key']
                if current_prefix:
                    file_name = file_name[len(current_prefix):].lstrip('/')

                files.append({
                    'name': file_name,
                    'type': 'file',
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'full_path': obj['Key']
                })

        return jsonify({
            'success': True,
            'query': query,
            'folders': folders,
            'files': files,
            'total_found': len(folders) + len(files),
            'has_more': response.get('IsTruncated', False)
        })

    except ClientError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/view')
def view_object():
    """API endpoint to view object content."""
    key = request.args.get('key')
    bucket = request.args.get('bucket', BUCKET_NAME)

    if not key:
        return jsonify({'success': False, 'error': 'No key provided'}), 400

    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')

        # Try to parse as JSON
        is_json = False
        if key.endswith('.json'):
            try:
                parsed = json.loads(content)
                content = json.dumps(parsed, indent=2, ensure_ascii=False)
                is_json = True
            except json.JSONDecodeError:
                pass

        return jsonify({
            'success': True,
            'key': key,
            'content': content,
            'is_json': is_json,
            'size': response['ContentLength'],
            'last_modified': response['LastModified'].isoformat()
        })

    except ClientError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
    except UnicodeDecodeError:
        return jsonify({
            'success': False,
            'error': 'File is not a text file'
        }), 400


if __name__ == '__main__':
    print(f"Starting S3 Web Browser for bucket: {BUCKET_NAME}")
    print(f"Endpoint: {config.get('endpoint', 'http://localhost:4566')}")
    print(f"Open http://localhost:5001 in your browser")
    app.run(host='0.0.0.0', port=5001, debug=True)
