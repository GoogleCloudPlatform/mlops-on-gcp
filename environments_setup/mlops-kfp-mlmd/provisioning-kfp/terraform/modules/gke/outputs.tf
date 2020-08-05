output "name" {
    value = google_container_cluster.gke_cluster.name
}

output "cluster_endpoint" {
    value = google_container_cluster.gke_cluster.endpoint
}
