output "bucket_name" {
  value = aws_s3_bucket.dumps.bucket
}

output "master_private_key_pem" {
  value     = tls_private_key.master-tls-key.private_key_pem
  sensitive = true
}