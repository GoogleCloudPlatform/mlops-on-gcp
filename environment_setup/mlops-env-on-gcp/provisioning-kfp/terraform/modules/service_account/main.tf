# Create the service account
resource "google_service_account" "service_account" {
    account_id = var.service_account_id
    display_name = var.service_account_display_name
}

# Create role bindings
resource "google_project_iam_member" "role_bindings" {
  for_each = toset(var.service_account_roles)
  member   = "serviceAccount:${google_service_account.service_account.email}"
  role     = "roles/${each.value}"
}