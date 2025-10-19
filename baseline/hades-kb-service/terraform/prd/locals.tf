locals {
  pod_security_group_id = "sg-0d6aa7923c8ad01a1" # obtained from Managed EKS team during service onboarding; use this to whitelist at various upstream dependencies e.g. DB
  lb_security_group_id = "sg-06d09d55e0856b542" # obtained from Managed EKS team during service onboarding
  service_name = "hades-kb-service"
  short_env = "prd"
}
