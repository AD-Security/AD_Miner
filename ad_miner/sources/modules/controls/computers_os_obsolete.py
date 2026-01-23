from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import manageComputersOs, presence_of


@register_control
class computers_os_obsolete(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "computers_os_obsolete"

        self.title = "Computers with obsolete OS"
        self.description = "List of computers with obsolete OS"
        self.risk = "The bigger this list, the more exposed to critical exploits your infrastructure is. Obsolete OS are not maintained anymore by their manufacturers and are often vulnerable to public exploits"
        self.poa = "Switch to a more up-to-date OS on these computers"

        self.list_computers_os_obsolete, all_os = manageComputersOs(
            requests_results["os"]
        )

    def run(self):
        if self.list_computers_os_obsolete is None:
            return
        page = Page(
            self.arguments.cache_prefix,
            "computers_os_obsolete",
            "Obsolete operating systems",
            self.get_dico_description(),
        )
        grid = Grid("Computers obsolete operating systems")
        cleaned_data = []
        for computer in self.list_computers_os_obsolete:
            if computer["Last logon in days"] < 90:  # remove ghost computers
                computer["Domain"] = (
                    '<i class="bi bi-globe2"></i>' + computer["Domain"]
                )
                computer["Last logon"] = days_format(computer["Last logon in days"])
                if (
                    "2008" in computer["Operating system"]
                    or "2003" in computer["Operating system"]
                    or "2012" in computer["Operating system"]
                    or "WINDOWS EMBEDDED STANDARD SERVICE PACK 1" in computer["Operating system"].upper()
                ):  # Add icons whether it's a computer or a server
                    computer["Operating system"] = (
                        '<i class="bi bi-server"></i>' + computer["Operating system"]
                    )
                    computer["name"] = (
                        '<i class="bi bi-server"></i>' + computer["name"]
                    )
                if (
                    "2000" in computer["Operating system"]
                    or "XP" in computer["Operating system"].upper()
                    or "WINDOWS 7" in computer["Operating system"].upper()
                    or "VISTA" in computer["Operating system"].upper()
                ):
                    computer["Operating system"] = (
                        '<i class="bi bi-pc-display"></i>'
                        + computer["Operating system"]
                    )
                    computer["name"] = (
                        '<i class="bi bi-pc-display"></i>' + computer["name"]
                    )

                cleaned_data.append(computer)
        grid.setheaders(["Domain", "name", "Operating system", "Last logon"])
        grid.setData(cleaned_data)
        page.addComponent(grid)
        page.render()
        self.list_computers_os_obsolete = cleaned_data

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = (
            len(self.list_computers_os_obsolete)
            if self.list_computers_os_obsolete
            else 0
        )

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.data} computers with obsolete OS"

    def get_rating(self) -> int:
        return presence_of(self.list_computers_os_obsolete, criticity=2)
