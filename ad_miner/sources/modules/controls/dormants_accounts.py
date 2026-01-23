from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import percentage_superior


@register_control
class dormants_accounts(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "dormants_accounts"

        self.title = "Dormant accounts"
        self.description = "List of all users who have their accounts unused for a long period of time."
        self.risk = "As dormant accounts represent an anomaly, this list should be reduced as much as possible. Unused accounts are a vector of attack as they keep their privilege."
        self.poa = (
            "Dormant accounts should be disabled when confirmed as not used anymore."
        )

        self.users = requests_results["nb_enabled_accounts"]

        self.users_dormant_accounts = requests_results["dormant_accounts"]
        self.users_not_connected_for_3_months = (
            [user["name"] for user in self.users_dormant_accounts if user["days"] > 90]
            if self.users_dormant_accounts is not None
            else None
        )
        self.admin_list = requests_results["admin_list"]

    def run(self):
        if self.users_dormant_accounts is None:
            return

        page = Page(
            self.arguments.cache_prefix,
            "dormants_accounts",
            "Dormant accounts",
            self.get_dico_description(),
        )
        grid = Grid("Dormants accounts")
        grid.setheaders(["domain", "name", "display name", "last logon", "Account Creation Date", "distinguished name"])

        data = []
        for dict in self.users_dormant_accounts:
            tmp_data = {"domain": '<i class="bi bi-globe2"></i>' + dict["domain"]}

            tmp_data["name"] = (
                (
                    '<i class="bi bi-gem" title="This user is domain admin"></i>'
                    + dict["name"]
                )
                if dict["name"] in self.admin_list
                else '<i class="bi bi-person-fill"></i>' + dict["name"]
            )
            tmp_data["display name"] = dict["displayname"] if dict["displayname"] else 'N/A'
            tmp_data["last logon"] = days_format(dict["days"])
            tmp_data["Account Creation Date"] = days_format(dict["accountCreationDate"])
            tmp_data["distinguished name"] = dict["distinguishedname"]

            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.users_dormant_accounts) if self.users_dormant_accounts else 0
        )

        self.name_description = f"{self.data} dormant accounts"

    def get_rating(self) -> int:
        return percentage_superior(
            self.users_dormant_accounts,
            self.users,
            criticity=2,
            percentage=0.5,
            presence=True,
        )
