# OAuth Client Outputs
output "oauth_client_id" {
  description = "The OAuth client ID (manually provided)"
  value       = var.oauth_client_id
  sensitive   = false
}

output "oauth_client_secret" {
  description = "The OAuth client secret (manually provided)"
  value       = var.oauth_client_secret
  sensitive   = true
}

output "oauth_client_name" {
  description = "The OAuth client display name"
  value       = var.agent_display_name
  sensitive   = false
}

# Deployment Information
output "deployment_project_id" {
  description = "Google Cloud Project ID used for deployment"
  value       = var.google_cloud_project
  sensitive   = false
}

output "deployment_location" {
  description = "Google Cloud location used for deployment"
  value       = var.google_cloud_location
  sensitive   = false
}

output "agent_display_name" {
  description = "Display name of the deployed agent"
  value       = var.agent_display_name
  sensitive   = false
}

output "agentspace_app_id" {
  description = "AgentSpace Application ID"
  value       = var.app_id
  sensitive   = false
}

# URLs and References
output "agentspace_url" {
  description = "URL to access AgentSpace for this project"
  value       = "https://agentspace.google.com/studio/${var.google_cloud_project}"
  sensitive   = false
}

output "oauth_redirect_uri" {
  description = "The configured OAuth redirect URI"
  value       = "https://vertexaisearch.cloud.google.com/oauth-redirect"
  sensitive   = false
}

# Terraform State Information
output "random_suffix" {
  description = "Random suffix used for resource naming"
  value       = random_id.suffix.hex
  sensitive   = false
}
