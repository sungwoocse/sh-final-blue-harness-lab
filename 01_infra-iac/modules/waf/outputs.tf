# ===========================================
# WAF Outputs
# ===========================================

output "web_acl_id" {
  description = "WAF Web ACL ID"
  value       = aws_wafv2_web_acl.cloudfront_waf.id
}

output "web_acl_arn" {
  description = "WAF Web ACL ARN"
  value       = aws_wafv2_web_acl.cloudfront_waf.arn
}

output "web_acl_name" {
  description = "WAF Web ACL Name"
  value       = aws_wafv2_web_acl.cloudfront_waf.name
}

output "web_acl_capacity" {
  description = "WAF Web ACL Capacity"
  value       = aws_wafv2_web_acl.cloudfront_waf.capacity
}
