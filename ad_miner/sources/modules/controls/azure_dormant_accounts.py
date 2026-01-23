from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class azure_dormant_accounts(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_misc"
        self.control_key = "azure_dormant_accounts"

        self.title = "Entra ID dormant accounts"
        self.description = "Users who did not login for 3 months"
        self.risk = "An account which has not been used for a long time but is still enabled may be used by attackers as they keep their privilege."
        self.poa = (
            "Dormant accounts should be disabled when confirmed as not used anymore."
        )

        self.azure_dormant_accounts = requests_results["azure_dormant_accounts"]

    def run(self):
        if self.azure_dormant_accounts is None:
            return

        page = Page(
            self.arguments.cache_prefix,
            "azure_dormant_accounts",
            "Users that did not log in for 3 months",
            self.get_dico_description(),
        )
        grid = Grid("Users that did not log in for 3 months")

        data = []
        self.azure_dormant_accounts_90_days = []
        for user in self.azure_dormant_accounts:
            if user["lastlogon"] > 90:
                self.azure_dormant_accounts_90_days.append(user)
                data.append(
                    {
                        "Name": '<i class="bi bi-person-fill"></i>' + user["Name"],
                        "Last logon": days_format(user["lastlogon"]),
                        "Creation date": days_format(user["whencreated"]),
                    }
                )

        grid.setheaders(["Name", "Last logon", "Creation date"])

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_dormant_accounts_90_days)
        self.name_description = f"{self.data} dormant accounts"

    def get_rating(self) -> int:
        return presence_of(self.azure_dormant_accounts, 3)
