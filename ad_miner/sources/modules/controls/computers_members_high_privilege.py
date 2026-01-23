from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class computers_members_high_privilege(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "computers_members_high_privilege"

        self.title = "Machine accounts with inadequate privileges"
        self.description = "List of computers with high privileges."
        self.risk = "Ideally, this list should be reduced to the minimum required. If these machines are compromised by an attacker, they will provide them with the corresponding privileges, which could be very dangerous."
        self.poa = "Check for any anomaly in this list."

        self.computers_members_high_privilege = requests_results[
            "computers_members_high_privilege"
        ]
        if self.computers_members_high_privilege is None:
            self.computers_members_high_privilege_uniq = None
        else:
            self.computers_members_high_privilege_uniq = list(
                dict.fromkeys(
                    d["computer"] for d in self.computers_members_high_privilege
                )
            )

    def run(self):
        if self.computers_members_high_privilege is None:
            return
        page = Page(
            self.arguments.cache_prefix,
            "computers_members_high_privilege",
            "Machine accounts with inadequate privileges",
            self.get_dico_description(),
        )
        grid = Grid("List of computer admins")
        for d in self.computers_members_high_privilege:
            d["domain"] = '<i class="bi bi-globe2"></i>' + d["domain"]
            d["computer"] = '<i class="bi bi-pc-display"></i>' + d["computer"]
            d["group"] = '<i class="bi bi-people-fill"></i>' + d["group"]
        grid.setheaders(["domain", "computer", "group"])
        grid.setData(self.computers_members_high_privilege)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.computers_members_high_privilege_uniq)
            if self.computers_members_high_privilege_uniq
            else 0
        )

        self.name_description = f"{self.data} computers with high privs."

    def get_rating(self) -> int:
        return presence_of(self.computers_members_high_privilege_uniq)
