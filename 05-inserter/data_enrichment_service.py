"""Service for enriching data with IDs from relational database responses."""

import json
import copy
from datetime import datetime


class MissingIdError(Exception):
    """Custom exception when a division or article has no ID."""
    pass


class DataEnrichmentService:
    """Service for enriching norma data with database IDs and validating completeness."""

    @staticmethod
    def enrich_data_with_ids(data, pk_mapping_json):
        """
        Enrich the data with IDs from pk_mapping_json.
        Adds 'id' field to each article and division based on the relational DB IDs.
        Handles nested divisions and articles recursively.
        Format: {"normaId": int, "divisionPks": {key: id}, "articlePks": {key: id}}
        Keys like "d5_a1_a2" represent article 2 within article 1 within division 5.
        """
        if not pk_mapping_json:
            print(f"[{datetime.now()}] - No pk_mapping_json provided, skipping ID enrichment")
            return data

        try:
            pk_mapping = json.loads(pk_mapping_json) if isinstance(pk_mapping_json, str) else pk_mapping_json

            if isinstance(data, str):
                data_obj = json.loads(data)
            else:
                data_obj = copy.deepcopy(data)

            structured_norma = (
                data_obj
                .get("data", {})
                .get("norma", {})
                .get("structured_texto_norma", None)
            )

            if 'normaId' in pk_mapping:
                if structured_norma is not None:
                    structured_norma['norma_id'] = pk_mapping['normaId']
                    print(f"[{datetime.now()}] - Enriched norma with ID: {pk_mapping['normaId']}")
                else:
                    print(f"[{datetime.now()}] - WARNING: structured_texto_norma not found, norma_id not inserted")

            division_pks = pk_mapping.get('divisionPks', {})
            article_pks = pk_mapping.get('articlePks', {})

            if structured_norma and 'divisions' in structured_norma:
                DataEnrichmentService._enrich_divisions_recursive(structured_norma['divisions'], division_pks, article_pks)
                DataEnrichmentService._validate_ids_recursive(structured_norma['divisions'])

            return data_obj

        except json.JSONDecodeError as e:
            print(f"[{datetime.now()}] - Error parsing data for enrichment: {e}")
            return data
        except Exception as e:
            print(f"[{datetime.now()}] - Error enriching data with IDs: {e}")
            return data

    @staticmethod
    def _enrich_divisions_recursive(divisions, division_pks, article_pks, parent_key=""):
        """
        Recursively enrich divisions and their nested articles/divisions with IDs.
        Uses 'order' field to build the hierarchical key.
        """
        if not divisions:
            return

        for division in divisions:
            division_order = division.get('order')
            if division_order is not None:
                division_key = f"{parent_key}d{division_order}" if parent_key == "" else f"{parent_key}d{division_order}"

                if division_key in division_pks:
                    division['id'] = division_pks[division_key]
                    print(f"[{datetime.now()}] - Enriched division (order={division_order}) with key '{division_key}' and ID: {division['id']}")

                if 'articles' in division and division['articles']:
                    DataEnrichmentService._enrich_articles_recursive(division['articles'], article_pks, division_key)

                if 'divisions' in division and division['divisions']:
                    DataEnrichmentService._enrich_divisions_recursive(division['divisions'], division_pks, article_pks, division_key + "_")

    @staticmethod
    def _enrich_articles_recursive(articles, article_pks, parent_key=""):
        """
        Recursively enrich articles and their nested articles with IDs.
        Uses 'order' field to build the hierarchical key.
        """
        if not articles:
            return

        for article in articles:
            article_order = article.get('order')
            if article_order is not None:
                article_key = f"{parent_key}_a{article_order}"

                if article_key in article_pks:
                    article['id'] = article_pks[article_key]
                    print(f"[{datetime.now()}] - Enriched article (order={article_order}) with key '{article_key}' and ID: {article['id']}")

                if 'articles' in article and article['articles']:
                    DataEnrichmentService._enrich_articles_recursive(article['articles'], article_pks, article_key)

    @staticmethod
    def _validate_ids_recursive(divisions, parent_path="root"):
        """
        Recursively validate that every division and article has an 'id'.
        Raises MissingIdError if any 'id' is missing.
        """
        if not divisions:
            return

        for division in divisions:
            division_order = division.get('order', 'unknown')
            division_path = f"{parent_path}.division(order={division_order})"

            if 'id' not in division or division['id'] is None:
                raise MissingIdError(
                    f"Missing ID in {division_path}"
                )

            # Validate articles under this division
            if 'articles' in division and division['articles']:
                for article in division['articles']:
                    article_order = article.get('order', 'unknown')
                    article_path = f"{division_path}.article(order={article_order})"

                    if 'id' not in article or article['id'] is None:
                        raise MissingIdError(
                            f"Missing ID in {article_path}"
                        )

                    # Recurse into nested articles
                    if 'articles' in article and article['articles']:
                        DataEnrichmentService._validate_articles_recursive(article['articles'], article_path)

            # Validate nested divisions
            if 'divisions' in division and division['divisions']:
                DataEnrichmentService._validate_ids_recursive(division['divisions'], parent_path=division_path)

    @staticmethod
    def _validate_articles_recursive(articles, parent_path="article"):
        """
        Recursively validate that every nested article has an 'id'.
        """
        if not articles:
            return

        for article in articles:
            article_order = article.get('order', 'unknown')
            article_path = f"{parent_path}.article(order={article_order})"

            if 'id' not in article or article['id'] is None:
                raise MissingIdError(
                    f"Missing ID in {article_path}"
                )

            if 'articles' in article and article['articles']:
                DataEnrichmentService._validate_articles_recursive(article['articles'], parent_path=article_path)

    @staticmethod
    def remove_embedding(obj):
        """
        Recursively remove 'embedding' keys from dicts or lists.
        """
        if isinstance(obj, dict):
            obj.pop("embedding", None)
            for v in obj.values():
                DataEnrichmentService.remove_embedding(v)
        elif isinstance(obj, list):
            for v in obj:
                DataEnrichmentService.remove_embedding(v)
        return obj
