locals {
  pod_security_group_id = "sg-0edba4d80b6721c23" # obtained from Managed EKS team during service onboarding; use this to whitelist at various upstream dependencies e.g. DB
  lb_security_group_id = "sg-03256ba84d3ca90bb" # obtained from Managed EKS team during service onboarding
  service_name = "hades-kb-service"
  short_env = "stg"
}
