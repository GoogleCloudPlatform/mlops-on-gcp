output "cluster_name" {
    value = module.kfp_gke_cluster.name
}

output "cluster_zone" {
    value = var.zone
}

output "kfp_sa_email" {
    value =module.kfp_service_account.service_account.email
}

output "gke_sa_name" {
    value = module.gke_service_account.service_account.email
}

output "sql_name" {
    value = module.ml_metadata_mysql.mysql_instance.name
}

output "sql_connection_name" {
    value = module.ml_metadata_mysql.mysql_instance.connection_name
}

output "artifact_store_bucket" {
    value = google_storage_bucket.artifact_store.name
}

#output "caip_notebook" {
#    value = module.caip_notebook.name
#}