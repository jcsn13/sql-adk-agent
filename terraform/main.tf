# Enable required Google Cloud APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "aiplatform.googleapis.com",      # Vertex AI API
    "discoveryengine.googleapis.com", # Discovery Engine API
    "storage.googleapis.com",         # Cloud Storage API
    "iam.googleapis.com",             # IAM API
    "compute.googleapis.com",         # Compute Engine API
  ])

  project = var.google_cloud_project
  service = each.value

  # Don't disable the service if the resource is destroyed
  disable_on_destroy = false
}

# Wait for APIs to propagate
resource "time_sleep" "api_propagation" {
  depends_on      = [google_project_service.required_apis]
  create_duration = "60s"
}

# Data source to get project number
data "google_project" "project" {
  project_id = var.google_cloud_project
}

# IAM bindings for Compute Engine default service account
resource "google_project_iam_member" "compute_service_account_roles" {
  for_each = toset([
    "roles/iam.serviceAccountUser",
    "roles/aiplatform.user",
    "roles/storage.objectUser",
  ])

  project = var.google_cloud_project
  role    = each.value
  member  = "serviceAccount:${data.google_project.project.number}-compute@developer.gserviceaccount.com"

  depends_on = [time_sleep.api_propagation]
}

# IAM bindings for AI Platform Reasoning Engine service account
resource "google_project_iam_member" "reasoning_engine_service_account_roles" {
  for_each = toset([
    "roles/discoveryengine.admin",
    "roles/aiplatform.user",
  ])

  project = var.google_cloud_project
  role    = each.value
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"

  depends_on = [time_sleep.api_propagation]
}

# Random suffix for unique resource naming
resource "random_id" "suffix" {
  byte_length = 4
}

# No OAuth client creation - using manually created credentials via variables

# Deployment automation using null_resource
resource "null_resource" "deploy_agent" {
  # Triggers for re-deployment
  triggers = {
    oauth_client_id    = var.oauth_client_id
    agent_display_name = var.agent_display_name
    project_id         = var.google_cloud_project
    app_id             = var.app_id
  }

  # Deploy the agent using existing deploy.py script
  provisioner "local-exec" {
    command     = "python3 deployment/deploy.py"
    working_dir = ".."

    environment = {
      # OAuth credentials from manually created client
      CLIENT_ID     = var.oauth_client_id
      CLIENT_SECRET = var.oauth_client_secret

      # Terraform Management Flag
      TERRAFORM_MANAGED = "true"

      # Google Cloud Platform
      GOOGLE_CLOUD_PROJECT        = var.google_cloud_project
      GOOGLE_CLOUD_PROJECT_NUMBER = var.google_cloud_project_number
      GOOGLE_CLOUD_LOCATION       = var.google_cloud_location
      GOOGLE_CLOUD_STORAGE_BUCKET = var.google_cloud_storage_bucket

      # AgentSpace Configuration
      APP_ID             = var.app_id
      AGENT_DISPLAY_NAME = var.agent_display_name
      TOOL_DESCRIPTION   = var.tool_description
      AGENT_ICON_URI     = var.agent_icon_uri

      # Agent Model Configuration
      ROOT_AGENT_MODEL      = var.root_agent_model
      ANALYTICS_AGENT_MODEL = var.analytics_agent_model
      BASELINE_NL2SQL_MODEL = var.baseline_nl2sql_model
      BIGQUERY_AGENT_MODEL  = var.bigquery_agent_model
      CHASE_NL2SQL_MODEL    = var.chase_nl2sql_model

      # BigQuery Configuration
      BQ_DATASET_ID = var.bq_dataset_id
      BQ_PROJECT_ID = var.bq_project_id

      # Agent Configuration
      AUTH_ID       = var.auth_id
      NL2SQL_METHOD = var.nl2sql_method
    }
  }

  # Cleanup on destroy
  provisioner "local-exec" {
    when        = destroy
    command     = "python3 deployment/undeploy.py"
    working_dir = ".."
    on_failure  = continue
  }

  depends_on = [
    google_project_iam_member.compute_service_account_roles,
    google_project_iam_member.reasoning_engine_service_account_roles,
    time_sleep.api_propagation
  ]
}
