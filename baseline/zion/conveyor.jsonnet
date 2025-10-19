# libsonnet: 1.18.0

local default = import 'defaults/defaults.jsonnet';

[
  {
    name: "zion",
    group: [
      "ti-svc-zion-owner",
      "ti-svc-zion-editr",
      "Engineering-zion",
      "Engineering-zion",
    ],
    pipeline: default.pipelines(self, type='k8s'),
    kubernetes: {
      gitlab_project_id: "22173"
    }
  }
]
