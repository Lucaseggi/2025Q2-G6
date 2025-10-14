data "aws_ami" "ecs" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

resource "tls_private_key" "master-tls-key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "master-key" {
  key_name   = "master-key"
  public_key = tls_private_key.master-tls-key.public_key_openssh
}

resource "aws_instance" "api-rest" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.public1.id
  security_groups             = [aws_security_group.public_sg.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.api_rest_name
  }

  # # Update frontend .env file with API IP and port
  # provisioner "local-exec" {
  #   command = "echo VITE_API_URL=http://${self.public_ip}:8000 > ../frontend/.env"
  # }

  # # Update CORS settings in API with S3 bucket URL
  # provisioner "local-exec" {
  #   command = "sed -i 's|http://simpla-cloud-frontend-[^/]*\\.s3-website-[^/]*\\.amazonaws\\.com/|http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}/|g' ../api/simpla_api/settings.py"
  # }

  depends_on = [aws_s3_bucket_website_configuration.frontend]
}

resource "aws_instance" "scraper" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.scraper_name
  }
}

resource "aws_instance" "processor" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.processor_name
  }
}

resource "aws_instance" "embedder" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.embedder_name
  }
}

resource "aws_instance" "inserter" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.inserter_name
  }
}

resource "aws_instance" "relational-guard" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.relational_guard_name
  }
}

resource "aws_instance" "vectorial-guard" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.vectorial_guard_name
  }
}

resource "aws_instance" "queue" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private1.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.queue_name
  }
}

resource "aws_instance" "vector-db" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.private2.id
  security_groups             = [aws_security_group.vdb_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.vdb_name
  }
}

resource "aws_instance" "relational-db" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = var.default_instance_type
  subnet_id                   = aws_subnet.private2.id
  security_groups             = [aws_security_group.private_sg.id]
  associate_public_ip_address = false
  key_name                    = aws_key_pair.master-key.key_name

  tags = {
    Name = var.relational_db_name
  }
}
