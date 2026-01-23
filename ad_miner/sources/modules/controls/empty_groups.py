from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid


@register_control
class empty_groups(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "empty_groups"

        self.title = "Groups without any member"
        self.description = "These groups do not contain any user, computer or any other group, which probably means they are not used anymore."
        self.risk = "As unused groups still retain their privilege but are less monitored, an attacker could exploit one of these to gain further access to the information system."
        self.poa = "Review these groups and check wether they should have lesser privilege or be deleted."

        self.empty_groups = requests_results["get_empty_groups"]
        self.groups = requests_results["nb_groups"]

    def run(self):
        page = Page(
            self.arguments.cache_prefix,
            "empty_groups",
            "Groups with no object",
            self.get_dico_description(),
        )
        grid = Grid("Groups without any object in it")
        headers = ["Empty group", "Full Reference"]

        for d in self.empty_groups:
            d["Empty group"] = '<i class="bi bi-people-fill"></i>' + d["Empty group"]

        grid.setheaders(headers)
        grid.setData(self.empty_groups)

        page.addComponent(grid)
        page.render()

        self.data = len(self.empty_groups)
        self.name_description = f"{self.data} groups without any member"

    def get_rating(self) -> int:
        if len(self.groups) > 0:
            return (
                2
                if len(self.empty_groups) / len(self.groups) > 0.40
                else 3 if len(self.empty_groups) / len(self.groups) > 0.20 else 5
            )
        return -1
