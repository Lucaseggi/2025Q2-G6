project_name = "proyecto-goblin"

tags = {
  Environment = "dev"
  Owner       = "Simpla SRL"
}

vpc_tags = {
  Name = "simpla-vpc"
}

vpc_cidr              = "10.1.0.0/16"
public_subnet_1_cidr  = "10.1.1.0/24"
public_subnet_2_cidr  = "10.1.2.0/24"
private_subnet_1_cidr = "10.1.3.0/24"
private_subnet_2_cidr = "10.1.4.0/24"
private_subnet_3_cidr = "10.1.5.0/24"
private_subnet_4_cidr = "10.1.6.0/24"

api_sg_name = "api-sg"
priv_sg_name = "priv-sg"
vdb_sg_name = "vdb-sg"

api_rest_name = "api-rest"
scrapper_ms_name = "scrapper-ms"
processing_ms_name = "processing-ms"
embedding_ms_name = "embedding-ms"
inserter_ms_name = "inserter-ms"
queue_name = "queue"

default_instance_type = "t2.micro"