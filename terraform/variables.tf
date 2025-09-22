# Google Cloud Platform Configuration
variable "google_cloud_project" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "google_cloud_project_number" {
  description = "Google Cloud Project Number"
  type        = string
}

variable "google_cloud_location" {
  description = "Google Cloud Location/Region"
  type        = string
  default     = "us-central1"
}

variable "google_cloud_storage_bucket" {
  description = "Google Cloud Storage bucket name for staging"
  type        = string
}

# AgentSpace Configuration
variable "app_id" {
  description = "AgentSpace Application ID"
  type        = string
}

variable "agent_display_name" {
  description = "Display name for the SQL ADK Agent"
  type        = string
  default     = "SQL ADK Agent"
}

variable "tool_description" {
  description = "Description of the agent's capabilities"
  type        = string
  default     = "SQL analysis and BigQuery agent for data insights"
}

variable "agent_icon_uri" {
  description = "URI for the agent icon"
  type        = string
  default     = "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols/database/default/48px.svg"
}

variable "support_email" {
  description = "Support email for OAuth brand (required for OAuth client creation)"
  type        = string
  default     = "support@example.com"
}

# OAuth Client Credentials (manually created)
variable "oauth_client_id" {
  description = "OAuth client ID (manually created in Google Cloud Console)"
  type        = string
}

variable "oauth_client_secret" {
  description = "OAuth client secret (manually created in Google Cloud Console)"
  type        = string
  sensitive   = true
}

# Agent Model Configuration
variable "root_agent_model" {
  description = "Model for the root agent"
  type        = string
  default     = "gemini-2.5-flash"
}

variable "analytics_agent_model" {
  description = "Model for the analytics agent"
  type        = string
  default     = "gemini-2.5-flash"
}

variable "baseline_nl2sql_model" {
  description = "Model for baseline NL2SQL"
  type        = string
  default     = "gemini-2.5-flash"
}

variable "bigquery_agent_model" {
  description = "Model for the BigQuery agent"
  type        = string
  default     = "gemini-2.5-flash"
}

variable "chase_nl2sql_model" {
  description = "Model for CHASE NL2SQL"
  type        = string
  default     = "gemini-2.5-flash"
}

# BigQuery Configuration
variable "bq_dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
}

variable "bq_project_id" {
  description = "BigQuery project ID"
  type        = string
}

# Agent Configuration
variable "auth_id" {
  description = "Authentication ID for the agent"
  type        = string
}

variable "nl2sql_method" {
  description = "Natural language to SQL method"
  type        = string
  default     = "CHASE"
}
