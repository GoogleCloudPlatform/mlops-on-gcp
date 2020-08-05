terraform {
  required_version = ">= 0.12"
}

resource "google_compute_network" "network" {
  name                    = var.network_name
  auto_create_subnetworks = "false"
  routing_mode            = "REGIONAL"
}

resource "google_compute_subnetwork" "subnetwork" {
  name                     = var.subnet_name
  region                   = var.region
  network                  = google_compute_network.network.self_link
  ip_cidr_range            = var.subnet_ip_range
  private_ip_google_access = true
}
