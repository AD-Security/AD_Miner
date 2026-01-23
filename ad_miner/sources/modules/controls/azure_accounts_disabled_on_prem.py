from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class azure_accounts_disabled_on_prem(Control):  # TODO change the class name
    "Docstring of my control"  # TODO small documentation here

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "ms_graph"
        self.control_key = "azure_accounts_disabled_on_prem"

        self.title = "Synced accounts with disabled twin account"
        self.description = (
            "Synced Entra ID accounts with different enabled status as the on premise one"
        )
        self.risk = "This anomaly probably means that unused accounts are still enabled on the Entra ID or on premise environment. An account which has not been used for a long time but is still enabled may be used by attackers as they keep their privilege."
        self.poa = "Ensure that these accounts should still be enabled."

        self.azure_accounts_disabled_on_prem = requests_results[
            "azure_accounts_disabled_on_prem"
        ]

    def run(self):
        if self.azure_accounts_disabled_on_prem is None:
            self.azure_accounts_disabled_on_prem = []

        page = Page(
            self.arguments.cache_prefix,
            "azure_accounts_disabled_on_prem",
            "Synced Entra ID accounts with different enabled status",
            self.get_dico_description(),
        )
        grid = Grid("Synced Entra ID accounts with different enabled status")

        data = []
        for user in self.azure_accounts_disabled_on_prem:
            data.append(
                {
                    "Entra ID name": '<i class="bi bi-person-fill"></i>'
                    + user["Azure name"],
                    "Enabled on Entra ID": (
                        '<i class="bi bi-check-square"></i>'
                        if user["Enabled on Azure"] is True
                        else '<i class="bi bi-square"></i>'
                    ),
                    "On premise name": '<i class="bi bi-person"></i>'
                    + user["On premise name"],
                    "Enabled on premise": (
                        '<i class="bi bi-check-square"></i>'
                        if user["Enabled on premise"] is True
                        else '<i class="bi bi-square"></i>'
                    ),
                }
            )

        grid.setheaders(
            ["Entra ID name", "Enabled on Entra ID", "On premise name", "Enabled on premise"]
        )

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_accounts_disabled_on_prem)
        self.name_description = f"{len(self.azure_accounts_disabled_on_prem)} Entra ID accounts are disabled on prem."

    def get_rating(self) -> int:
        return presence_of(self.azure_accounts_disabled_on_prem, 3)
