## Zion Public Common Plugin List

There are a list of common plugins that allow for usage across Zion Agents/channels. Depending on the environment (staging/production), the plugin released might differ as well.
You may view the full list of common plugins by visiting our TI Bot Config Portal.

Do note that all plugins that are marked as `common` are open for all agents to be used.

| Environment | URL Link |
| --- | --- |
| Staging | https://ti-bot-configuration.grab.com/plugins |
| Production | https://ti-bot-configuration.stg-myteksi.com/plugins |

### Plugin Usages

To make use of a Plugin when calling the Zion API, you may specify it under the `agent_config`

Example:

```
{
    "input": {
        "agent_config": {
            "plugins": [
                {
                    "name": "universal_search",
                    "type": "common"
                }
            ]
        }
    }

```
