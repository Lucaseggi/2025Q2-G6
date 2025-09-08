output "bucket_name" {
  value = aws_s3_bucket.dumps.bucket
}

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

output "scrapper_ms_private_ip" {
  value = aws_instance.scrapper-ms.private_ip
}

output "processing_ms_private_ip" {
  value = aws_instance.processing-ms.private_ip
}

output "embedding_ms_private_ip" {
  value = aws_instance.embedding-ms.private_ip
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