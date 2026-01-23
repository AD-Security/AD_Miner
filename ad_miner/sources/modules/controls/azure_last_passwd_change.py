from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class azure_last_passwd_change(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_passwords"
        self.control_key = "azure_last_passwd_change"

        self.title = "Incoherent last password change"
        self.description = (
            "Users whose password change date is different between Entra ID and on premise"
        )
        self.risk = "A difference between the timestamps of the last password change between Entra ID and on premise environment could mean that a synchronization did not occur and could lead to an exposed account on one of the environment"
        self.poa = "Check if the desynchronization is normal."

        self.azure_last_passwd_change = requests_results["azure_last_passwd_change"]

    def run(self):
        if self.azure_last_passwd_change is None:
            self.azure_last_passwd_change = []

        page = Page(
            self.arguments.cache_prefix,
            "azure_last_passwd_change",
            "Incoherent last password change both on Entra ID and on premise",
            self.get_dico_description(),
        )
        grid = Grid("Incoherent last password change both on Entra ID and on premise")

        data = []
        self.azure_last_passwd_change_strange = []
        for user in self.azure_last_passwd_change:
            onprem = user["Last password set on premise"]
            onazure = user["Last password set on Azure"]
            diff = int(abs(onprem - onazure))
            if diff > 1:
                self.azure_last_passwd_change_strange.append(user)
                data.append(
                    {
                        "Name": '<i class="bi bi-person-fill"></i>' + user["Name"],
                        "Last password set on premise": days_format(onprem),
                        "Last password set on Entra ID": days_format(onazure),
                        "Difference": days_format(diff),
                    }
                )

        grid.setheaders(
            [
                "Name",
                "Last password set on premise",
                "Last password set on Entra ID",
                "Difference",
            ]
        )

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_last_passwd_change_strange)
        self.name_description = f"{len(self.azure_last_passwd_change_strange)} users have unusual last password change"

    def get_rating(self) -> int:
        return presence_of(self.azure_last_passwd_change_strange, 3)
