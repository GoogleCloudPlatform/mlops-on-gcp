resource "google_sql_database_instance" "mysql" {
  name             = var.name
  region           = var.region  
  database_version = "MYSQL_5_7"

  settings {
    tier              = var.tier
    disk_size         = var.disk_size
  }
}