from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class azure_accounts_not_found_on_prem(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "ms_graph"
        self.control_key = "azure_accounts_not_found_on_prem"

        self.title = "Entra ID accounts not synced on-prem"
        self.description = (
            "ENtra ID accounts that are synced to an non-existing on premise account"
        )
        self.risk = "This anomaly may indicate a misconfiguration in the synchronization of accounts."
        self.poa = (
            "Ensure that this situation is not a symptom of a bigger misconfiguration."
        )

        self.azure_accounts_not_found_on_prem = requests_results[
            "azure_accounts_not_found_on_prem"
        ]

    def run(self):
        if self.azure_accounts_not_found_on_prem is None:
            self.azure_accounts_not_found_on_prem = []

        page = Page(
            self.arguments.cache_prefix,
            "azure_accounts_not_found_on_prem",
            "Entra ID accounts that are synced to non-existing on premise account",
            self.get_dico_description(),
        )
        grid = Grid("Entra ID accounts that are synced to non-existing on premise account")

        data = []
        for user in self.azure_accounts_not_found_on_prem:
            data.append(
                {
                    "Name": '<i class="bi bi-person-fill"></i>' + user["Name"],
                    "Synced to on premise": '<i class="bi bi-check-square"></i>',
                    "Synced account": '<i class="bi bi-question-lg"></i>',
                }
            )

        grid.setheaders(["Name", "Synced to on premise", "Synced account"])

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_accounts_not_found_on_prem)
        self.name_description = f"{len(self.azure_accounts_not_found_on_prem)} Entra ID accounts are non-existant on-prem"

    def get_rating(self) -> int:
        return presence_of(self.azure_accounts_not_found_on_prem, 3)
