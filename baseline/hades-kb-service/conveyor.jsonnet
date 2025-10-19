# libsonnet: 1.23.0

local default = import 'defaults/defaults.jsonnet';

[
  {
    name: "hades-kb-service",
    group: [
	"ti-svc-hades-kb-service-owner",
	"ti-svc-hades-kb-service-editr",
      "Engineering-hades-kb-service",
      "Engineering-ti-support-bot",
    ],
    pipeline: default.pipelines(self, type='k8s'),
    kubernetes: {
      gitlab_project_id: "24291"
    }
  }
]
