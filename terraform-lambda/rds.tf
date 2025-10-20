module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "~> 6.0" 

  identifier = replace(lower(var.relational_db_name), "_", "-")

  
  engine            = var.rds_engine
  engine_version    = var.rds_engine_version
  instance_class    = var.rds_instance_class
  allocated_storage = 50
  
  manage_master_user_password = false
  username = var.postgres_user
  password = var.postgres_password
  port     = var.postgres_port

  vpc_security_group_ids = [aws_security_group.rdb_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name

  family               = "postgres16"
  major_engine_version = var.rds_engine_version  
  tags = {
    Name = var.relational_db_name
  }
}

