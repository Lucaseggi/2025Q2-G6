output "master_private_key_pem" {
  value     = tls_private_key.master-tls-key.private_key_pem
  sensitive = true
}

output "api_rest_public_ip" {
  value = aws_instance.api-rest.public_ip
}

output "api_rest_private_ip" {
  value = aws_instance.api-rest.private_ip
}

output "scraper_ms_private_ip" {
  value = aws_instance.scraper-ms.private_ip
}

output "processor_ms_private_ip" {
  value = aws_instance.processor-ms.private_ip
}

output "embedder_ms_private_ip" {
  value = aws_instance.embedder-ms.private_ip
}

output "inserter_ms_private_ip" {
  value = aws_instance.inserter-ms.private_ip
}

output "queue_private_ip" {
  value = aws_instance.queue.private_ip
}

output "vector_db_private_ip" {
  value = aws_instance.vector-db.private_ip
}

# Frontend S3 bucket outputs
output "frontend_bucket_name" {
  description = "Name of the S3 bucket hosting the frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "frontend_bucket_website_endpoint" {
  description = "Website endpoint for the frontend S3 bucket"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "frontend_website_url" {
  description = "Complete URL to access the frontend website"
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}