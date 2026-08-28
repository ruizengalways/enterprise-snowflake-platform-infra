# Materialized into a Terraform root at runtime by terraform/scripts/select-backend.sh.
# Bucket, region and credentials are supplied externally.
terraform {
  backend "s3" {
    encrypt      = true
    use_lockfile = true
  }
}
