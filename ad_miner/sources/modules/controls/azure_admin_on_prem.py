from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class azure_admin_on_prem(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_permissions"
        self.control_key = "azure_admin_on_prem"

        self.title = "Privileged accounts on both on-prem and Entra ID"
        self.description = (
            "All accounts that are privileged both on Entra ID and on premise"
        )
        self.risk = "Admin accounts should not be shared between cloud and on premise environments, as it means that the compromission of one leads to the compromission of the other one."
        self.poa = "Review these privileged accounts and opt into differents admin accounts for cloud and on premise environments"

        self.azure_admin_on_prem = requests_results["azure_admin_on_prem"]

    def run(self):
        if self.azure_admin_on_prem is None:
            self.azure_admin_on_prem = []

        page = Page(
            self.arguments.cache_prefix,
            "azure_admin_on_prem",
            "Entra ID & On premise Admins",
            self.get_dico_description(),
        )
        grid = Grid("Entra ID & On premise Admins")

        data = []
        for user in self.azure_admin_on_prem:
            data.append({"Name": '<i class="bi bi-gem"></i>' + user["Name"]})

        grid.setheaders(["Name"])

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_admin_on_prem)
        self.name_description = (
            f"{len(self.azure_admin_on_prem)} admins on Entra ID and on premise"
        )

    def get_rating(self) -> int:
        return presence_of(self.azure_admin_on_prem, 1)
