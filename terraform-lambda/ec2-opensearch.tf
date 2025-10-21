data "aws_ami" "ecs" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-ecs-hvm-*-x86_64-ebs"]
  }
}

resource "tls_private_key" "master_tls_key" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "aws_key_pair" "master_key" {
  key_name   = "master-key"
  public_key = tls_private_key.master_tls_key.public_key_openssh
}

resource "aws_instance" "vector_db" {
  ami                         = data.aws_ami.ecs.id
  instance_type               = "t3.medium"
  subnet_id                   = aws_subnet.public_1.id
  security_groups             = [aws_security_group.vdb_sg.id, aws_security_group.public_sg.id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.master_key.key_name

  tags = {
    Name = var.vdb_name
  }
}
