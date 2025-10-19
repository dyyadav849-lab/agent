def correct_env(env: str) -> str:
    if env in ["stg", "staging"]:
        return "stg"
    if env in ["prd", "prod", "production"]:
        return "prd"
    return "prd_stg"
