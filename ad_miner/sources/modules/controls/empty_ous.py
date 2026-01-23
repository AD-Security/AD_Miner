from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid


@register_control
class empty_ous(Control):  # TODO change the class name
    "Docstring of my control"  # TODO small documentation here

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "empty_ous"

        self.title = "OUs without any member"
        self.description = "These OUs do not contain any user, computer or any other group, which probably means they are not used anymore."
        self.risk = "As unused OUs still retain their privilege but are less monitored, an attacker could exploit one of these to gain further access to the information system."
        self.poa = "Review these OUs and check wether they should have lesser privilege or be deleted."

        self.empty_ous = requests_results["get_empty_ous"]
        self.groups = requests_results["nb_groups"]

    def run(self):
        page = Page(
            self.arguments.cache_prefix,
            "empty_ous",
            "OUs with no object",
            self.get_dico_description(),
        )
        grid = Grid("OUs without any object in it")
        headers = ["Empty Organizational Unit", "Full Reference"]

        for d in self.empty_ous:
            d["Empty Organizational Unit"] = (
                '<i class="bi bi-building"></i>' + d["Empty Organizational Unit"]
            )

        grid.setheaders(headers)
        grid.setData(self.empty_ous)

        page.addComponent(grid)
        page.render()

        self.data = len(self.empty_ous)
        self.name_description = f"{self.data} OUs without any member"

    def get_rating(self) -> int:
        if len(self.groups) > 0:
            return (
                2
                if len(self.empty_ous) / len(self.groups) > 0.40
                else 3 if len(self.empty_ous) / len(self.groups) > 0.20 else 5
            )
        return -1
