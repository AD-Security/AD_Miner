from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import time_since


@register_control
class krb_last_change(Control):  # TODO change the class name
    "Docstring of my control"  # TODO small documentation here

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "kerberos"
        self.control_key = "krb_last_change"

        self.title = "Old KRBTGT password"
        self.description = "Last change of password for KRBTGT account."
        self.risk = "The more regularly these passwords are changed, the better. If KRBTGT account is compromised, the whole infrastructure is as well."
        self.poa = "Check that KRBTGT accounts had their passwords changed recently."

        self.users_krb_pwd_last_set = requests_results["krb_pwd_last_change"]

    def run(self):
        if self.users_krb_pwd_last_set is None:
            return
        page = Page(
            self.arguments.cache_prefix,
            "krb_last_change",
            "KRBTGT account",
            self.get_dico_description(),
        )
        grid = Grid("KRBTGT account")
        grid.setheaders(
            ["domain", "name", "Last password change", "Account Creation Date"]
        )

        data = []
        for dict in self.users_krb_pwd_last_set:
            tmp_data = {"domain": '<i class="bi bi-globe2"></i>' + dict["domain"]}
            tmp_data["name"] = (
                '<i class="bi bi-ticket-perforated-fill"></i>' + dict["name"]
            )
            tmp_data["Last password change"] = days_format(dict["pass_last_change"])
            tmp_data["Account Creation Date"] = days_format(dict["accountCreationDate"])
            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = max(
            [dict["pass_last_change"] for dict in self.users_krb_pwd_last_set],
            default=0,
        )

        self.name_description = f"krbtgt not updated in > {self.data} days"

    def get_rating(self) -> int:
        return time_since(
            max(
                [dict["pass_last_change"] for dict in self.users_krb_pwd_last_set],
                default=None,
            ),
            age=1 * 365,
            criticity=2,
        )
