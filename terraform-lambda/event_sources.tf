# SQS Event Source Mappings for Lambda Functions
# These configure Lambda to automatically poll SQS queues and trigger the functions

# Purifier Lambda - triggered by messages in purifying queue
resource "aws_lambda_event_source_mapping" "purifier_sqs" {
  event_source_arn = aws_sqs_queue.purifying.arn
  function_name    = aws_lambda_function.purifier.arn

  # Batch settings
  batch_size                         = 1  # Process 1 message at a time for heavy processing
  maximum_batching_window_in_seconds = 0  # No batching window

  # Error handling
  function_response_types = ["ReportBatchItemFailures"]

  # Scaling configuration
  scaling_config {
    maximum_concurrency = 10  # Max concurrent executions for this trigger
  }

}

# Processor Lambda - triggered by messages in processing queue
resource "aws_lambda_event_source_mapping" "processor_sqs" {
  event_source_arn = aws_sqs_queue.processing.arn
  function_name    = aws_lambda_function.processor.arn

  # Batch settings - process one at a time due to LLM processing time
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0

  # Error handling
  function_response_types = ["ReportBatchItemFailures"]

  # Scaling configuration - limit concurrency due to heavy LLM usage
  scaling_config {
    maximum_concurrency = 5  # Lower concurrency for expensive LLM operations
  }

}

# Embedder Lambda - triggered by messages in embedding queue
resource "aws_lambda_event_source_mapping" "embedder_sqs" {
  event_source_arn = aws_sqs_queue.embedding.arn
  function_name    = aws_lambda_function.embedder.arn

  # Batch settings - can process multiple embeddings in parallel
  batch_size                         = 5  # Process up to 5 at once
  maximum_batching_window_in_seconds = 5  # Wait up to 5 seconds to gather batch

  # Error handling
  function_response_types = ["ReportBatchItemFailures"]

  # Scaling configuration
  scaling_config {
    maximum_concurrency = 20  # Higher concurrency for embeddings
  }

}

# Inserter Lambda - triggered by messages in inserting queue
resource "aws_lambda_event_source_mapping" "inserter_sqs" {
  event_source_arn = aws_sqs_queue.inserting.arn
  function_name    = aws_lambda_function.inserter.arn

  # Batch settings - batch inserts for efficiency
  batch_size                         = 10  # Process up to 10 at once
  maximum_batching_window_in_seconds = 10  # Wait up to 10 seconds to gather batch

  # Error handling
  function_response_types = ["ReportBatchItemFailures"]

  # Scaling configuration
  scaling_config {
    maximum_concurrency = 15  # Moderate concurrency for database writes
  }

}
