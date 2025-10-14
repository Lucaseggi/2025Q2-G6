"""
Failed Processing Logger

Tracks failed infoleg_ids for later manual intervention.
This creates a simple log file that can be used to identify which
documents failed during processing and need human review.
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class FailedProcessingLogger:
    """Logs failed processing attempts with infoleg_ids for manual intervention"""

    def __init__(self, log_dir: str = "/app/logs", service_name: str = "unknown"):
        """
        Initialize the failed processing logger.

        Args:
            log_dir: Directory to store failed processing logs
            service_name: Name of the service (purifier/processor/embedder)
        """
        self.log_dir = log_dir
        self.service_name = service_name
        self.log_file = os.path.join(log_dir, f"failed_processing_{service_name}.jsonl")

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        logger.info(f"Failed processing logger initialized: {self.log_file}")

    def log_failure(
        self,
        infoleg_id: int,
        error_type: str,
        error_message: str,
        stage: str = "unknown",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a failed processing attempt.

        Args:
            infoleg_id: The infoleg ID of the failed document
            error_type: Type of error (e.g., 'llm_failure', 'purification_failure')
            error_message: Detailed error message
            stage: Processing stage where failure occurred
            additional_data: Any additional context data
        """
        try:
            failure_entry = {
                "timestamp": datetime.now().isoformat(),
                "service": self.service_name,
                "infoleg_id": infoleg_id,
                "error_type": error_type,
                "error_message": error_message,
                "stage": stage,
                "additional_data": additional_data or {}
            }

            # Append to JSONL file (one JSON object per line)
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(failure_entry, ensure_ascii=False) + '\n')

            logger.debug(f"Logged failure for infoleg_id={infoleg_id}, type={error_type}")

        except Exception as e:
            logger.error(f"Failed to log processing failure: {e}")

    def get_failed_ids(self) -> list[int]:
        """
        Get list of all failed infoleg_ids from the log file.

        Returns:
            List of unique infoleg_ids that failed
        """
        try:
            if not os.path.exists(self.log_file):
                return []

            failed_ids = set()
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        failed_ids.add(entry.get('infoleg_id'))
                    except json.JSONDecodeError:
                        continue

            return sorted(list(failed_ids))

        except Exception as e:
            logger.error(f"Failed to read failed processing log: {e}")
            return []

    def get_failures_by_type(self) -> Dict[str, list]:
        """
        Get failures grouped by error type.

        Returns:
            Dictionary mapping error_type to list of failure entries
        """
        try:
            if not os.path.exists(self.log_file):
                return {}

            failures_by_type = {}
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        error_type = entry.get('error_type', 'unknown')
                        if error_type not in failures_by_type:
                            failures_by_type[error_type] = []
                        failures_by_type[error_type].append(entry)
                    except json.JSONDecodeError:
                        continue

            return failures_by_type

        except Exception as e:
            logger.error(f"Failed to read failed processing log: {e}")
            return {}

    def export_failed_ids_txt(self, output_file: Optional[str] = None) -> str:
        """
        Export failed infoleg_ids to a simple text file (one ID per line).

        Args:
            output_file: Path to output file (default: failed_ids_{service}.txt)

        Returns:
            Path to the output file
        """
        if output_file is None:
            output_file = os.path.join(self.log_dir, f"failed_ids_{self.service_name}.txt")

        try:
            failed_ids = self.get_failed_ids()

            with open(output_file, 'w', encoding='utf-8') as f:
                for infoleg_id in failed_ids:
                    f.write(f"{infoleg_id}\n")

            logger.info(f"Exported {len(failed_ids)} failed IDs to {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Failed to export failed IDs: {e}")
            raise

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all failures.

        Returns:
            Dictionary with summary statistics
        """
        try:
            failures_by_type = self.get_failures_by_type()
            total_failures = sum(len(entries) for entries in failures_by_type.values())
            unique_ids = len(self.get_failed_ids())

            return {
                "service": self.service_name,
                "total_failures": total_failures,
                "unique_failed_ids": unique_ids,
                "failures_by_type": {
                    error_type: len(entries)
                    for error_type, entries in failures_by_type.items()
                }
            }

        except Exception as e:
            logger.error(f"Failed to get summary: {e}")
            return {}
