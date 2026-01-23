from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.utils import days_format


@register_control
class computers_without_laps(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "passwords"
        self.control_key = "computers_without_laps"

        self.title = "Computers without LAPS"
        self.description = "Microsoft Local Administrator Password Solution (LAPS) allows local admnistrators to manage different passwords on local administrator accounts."
        self.risk = "The more computers are configured with LAPS, the better, especially on critical servers/machines. Without LAPS, it becomes tedious to have different passwords on local administrator for different computers, resulting in reuse of passwords and a risk of lateral movement."
        self.poa = "LAPS is a good tool to use, consider installing it or expanding its usage to more computers."

        self.computers_nb_has_laps = requests_results["nb_computers_laps"]
        self.list_total_computers = requests_results["nb_computers"]

    def run(self):
        if self.computers_nb_has_laps is None:
            return

        if len(self.list_total_computers) != 0:
            stat_LAPS = round(100 * len([computer_has_laps for computer_has_laps in self.computers_nb_has_laps if "ENABLED" in computer_has_laps["LAPS"].upper() or "TRUE" in computer_has_laps["LAPS"].upper()]) / (len(self.computers_nb_has_laps) + 0.001))

        else:
            stat_LAPS = 0
        self.stat_laps = 100 - stat_LAPS

        page = Page(
            self.arguments.cache_prefix,
            "computers_without_laps",
            "Computers' LAPS status",
            self.get_dico_description(),
        )
        grid = Grid("Computers with LAPS")
        grid.setheaders(["domain", "name", "LAPS", "Last logon"])

        cleaned_data = []
        for computer in self.computers_nb_has_laps:
            tmp_dict = {}
            # If value is None
            if not "lastLogon" in computer.keys():
                continue
            # Exclude ghost computers (last logon > 90 days)
            if computer["lastLogon"] < 90:
                tmp_dict["domain"] = '<i class="bi bi-globe2"></i>' + computer["domain"]
                tmp_dict["Last logon"] = days_format(computer["lastLogon"])
                tmp_dict["name"] = '<i class="bi bi-pc-display"></i>' + computer["name"]
                if computer["LAPS"] == "false":
                    tmp_dict["LAPS"] = '<i class="bi bi-unlock-fill text-danger"></i>Disabled'
                else:
                    tmp_dict["LAPS"] = '<i class="bi bi-lock-fill text-success"></i>Enabled'
                cleaned_data.append(tmp_dict)
        self.computers_nb_has_laps = cleaned_data
        grid.setData(cleaned_data)
        page.addComponent(grid)
        page.render()

        self.data = self.stat_laps if self.stat_laps else 0

        self.name_description = f"{self.data} % computers without LAPS"

    def get_rating(self) -> int:
        return 4 if self.stat_laps < 20 else 3
