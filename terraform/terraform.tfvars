project_name = "simpla-cloud"

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
scraper_name = "scraper"
processor_name = "processor"
embedder_name = "embedder"
inserter_name = "inserter"
relational_guard_name = "relational"
vectorial_guard_name = "vectorial"
queue_name = "queue"
vdb_name = "vector-db"
relational_db_name = "relational-db"

default_instance_type = "t2.micro"