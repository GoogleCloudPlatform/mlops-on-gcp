# Required variables

variable "region" {
  description = "The region for subnetworks in the network"
  type        = string
}

variable "network_name" {
  description = "The network name"
  type        = string
}

variable "subnet_name" {
  description = "The subnte name"
  type        = string
}

# Optional variables

variable "subnet_ip_range" {
  description = "The IP address range for the subnet"
  default     = "10.128.0.0/14"
}
