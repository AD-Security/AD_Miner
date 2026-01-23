from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import percentage_superior


@register_control
class computers_last_connexion(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "computers_last_connexion"

        # TODO define the control page title and texts
        self.title = "Ghost computers"
        self.description = "Enabled computer last logon to help identify computer objects that still exist in the domain but were most likely decommissioned."
        self.risk = "Computers with a last logon larger than 60 days are considered ghost and are most likely to correspond to computers that have been improperly terminated. Although these computers may no longer exist physically, privileges that they may have been granted may still be abused in attack path. For example, if the machine account of a ghost computer A has local administration privileges over computer B and if current ACEs allow writing over that ghost computer's msDs-KeyCredentialLink attribute, then this can be abused to obtain admin access over computer B."
        self.poa = "Confirm that listed ghost computers no longer exist and delete corresponding objects from Active Directory."

        self.computers_with_last_connection_date = requests_results[
            "computers_not_connected_since"
        ]
        self.computers_not_connected_since_60 = list(
            filter(
                lambda computer: int(computer["days"]) > 60,
                self.computers_with_last_connection_date,
            )
        )
        self.list_total_computers = requests_results["nb_computers"]

    def run(self):
        if self.computers_with_last_connection_date is None:
            return
        page = Page(
            self.arguments.cache_prefix,
            "computers_last_connexion",
            "Ghost computers",
            self.get_dico_description(),
        )

        data = []
        for c in self.computers_not_connected_since_60:
            data.append(
                {
                    "name": '<i class="bi bi-pc-display"></i>' + c["name"],
                    "Last logon": days_format(c["days"]),
                    "Last password set": days_format(c["pwdlastset"]),
                    "Enabled": '<i class="bi bi-check2-square text-danger"></i>'
                    + str(c["enabled"]),
                }
            )
        grid = Grid("Computers not connected since")
        grid.setheaders(["name", "Last logon", "Last password set", "Enabled"])
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.computers_not_connected_since_60)
            if self.computers_not_connected_since_60
            else 0
        )

        self.name_description = f"{self.data} ghost computers"

    def get_rating(self) -> int:
        return percentage_superior(
            self.computers_not_connected_since_60,
            self.list_total_computers,
            criticity=2,
            percentage=0.5,
            presence=True,
        )
