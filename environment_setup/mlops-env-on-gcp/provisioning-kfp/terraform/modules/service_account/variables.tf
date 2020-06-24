
variable "service_account_id" {
    description = "The ID of the service account"
    type        = string
}

variable "service_account_display_name" {
    description = "The display name of the service account"
    type        = string
}

variable "service_account_roles" {
    description = "The roles to assigne to the service account"
    type        = list(string)
}