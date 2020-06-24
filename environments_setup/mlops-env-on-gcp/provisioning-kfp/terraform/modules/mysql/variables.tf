variable "region" {
  description = "The region of the instance"
  type        = string
}

variable "name" {
  description = "The instance name"
  type        = string
}

variable "disk_size" {
  description = "The size of data disk"
  default     = 100
}

variable "tier" {
  description = "The machine type to use"
  default     = "db-n1-standard-8"
}