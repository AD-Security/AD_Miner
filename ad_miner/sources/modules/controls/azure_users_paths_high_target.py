from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.common_analysis import presence_of, createGraphPage


@register_control
class azure_users_paths_high_target(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_permissions"
        self.control_key = "azure_users_paths_high_target"

        self.title = "Entra ID users with path high value targets"
        self.description = "All Entra ID users that can compromise a high value target"
        self.risk = "Some of these paths could lead to a partial or full compromission of the tenant"
        self.poa = "Review and clean up the privileges of these accounts to lower the risk of compromission"

        self.azure_users_paths_high_target = requests_results[
            "azure_users_paths_high_target"
        ]

    def run(self):
        if self.azure_users_paths_high_target is None:
            self.azure_users_paths_high_target = []
        createGraphPage(
            self.arguments.cache_prefix,
            "azure_users_paths_high_target",
            "Entra ID Users with paths to high target",
            self.get_dico_description(),
            self.azure_users_paths_high_target,
            self.requests_results,
        )
        self.data = len(self.azure_users_paths_high_target)
        self.name_description = f"{len(self.azure_users_paths_high_target)} Users with a Path to High Value Targets"

    def get_rating(self) -> int:
        return presence_of(self.azure_users_paths_high_target, 3)
