

resource "aws_lambda_function" "db_seeder" {
  function_name    = "db-seeder-lambda"
  package_type     = "Image"
  image_uri        = var.db_seeder_image_uri
  role             = data.aws_iam_role.lab_role.arn
  timeout          = 120

  vpc_config {
    #TODO cambiar por for each
    subnet_ids         = [aws_subnet.private_1.id, aws_subnet.private_2.id, aws_subnet.private_3.id,aws_subnet.private_4.id]
    security_group_ids = [aws_security_group.private_sg.id]
  }


  depends_on       = [module.rds]
  environment {
    variables = {
      DB_HOST = module.rds.db_instance_address
      DB_PORT = var.postgres_port
      DB_USER = var.postgres_user
      DB_PASS = var.postgres_password
      DB_NAME = var.postgres_db
    }
  }
  
}
resource "aws_lambda_invocation" "db_seed" {
  function_name =aws_lambda_function.db_seeder.function_name
  input      = jsonencode({})
  depends_on = [aws_lambda_function.db_seeder]
}
output "lambda_output" {
  value = aws_lambda_invocation.db_seed.result
}
