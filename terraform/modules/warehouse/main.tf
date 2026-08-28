resource "snowflake_warehouse" "this" {
  name                                = var.name
  warehouse_type                      = "STANDARD"
  warehouse_size                      = var.warehouse_size
  auto_suspend                        = var.auto_suspend_seconds
  auto_resume                         = "true"
  initially_suspended                 = true
  comment                             = var.comment
  statement_timeout_in_seconds        = var.statement_timeout_seconds
  statement_queued_timeout_in_seconds = var.statement_queued_timeout_seconds
}
