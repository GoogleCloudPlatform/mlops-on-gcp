variable "name" {
    description = "The name of the GKE cluster"
    type        = string
}

variable "description" {
    description = "The cluster's description"
    type        = string
}

variable "location" {
    description = "The of the GKE cluster"
    type        = string
}

variable "sa_full_id" {
    description = "The cluster's service account full ID"
}

variable "network" {
    description = "The name of the network to which the cluster is connected"
}

variable "subnetwork" {
    description = "The name of the subnetwork to which the cluster is connected"
}


variable "node_count" {
    description = "The cluster's node count"
    default     = 3
}

variable "node_type" {
    description = "The cluster's node type"
    default     = "n1-standard-1"
}


