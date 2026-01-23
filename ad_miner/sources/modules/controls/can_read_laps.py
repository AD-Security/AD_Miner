from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import get_interest

from urllib.parse import quote


@register_control
class can_read_laps(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "passwords"
        self.control_key = "can_read_laps"

        self.title = "Access to LAPS passwords"
        self.description = "Accounts that can read LAPS local administrator passwords."
        self.risk = "These objects can read LAPS local administrator passwords. Objects with rights to read LAPS passwords are a potential threat as they can read the password of the local administrator account."
        self.poa = (
            "Review the accounts and make sure that their privileges are legitimate."
        )

        self.can_read_laps = requests_results["can_read_laps"]
        self.users_nb_domain_admins = requests_results["nb_domain_admins"]

    def run(self):
        if self.can_read_laps is None:
            return

        self.max_max_interest = 0

        page = Page(
            self.arguments.cache_prefix,
            "can_read_laps",
            "Objects able to read LAPS password",
            self.get_dico_description(),
        )
        grid = Grid("Objects able to LAPS passwords")
        grid.setheaders(["domain", "name", "computers", "interest"])
        data = []

        icon_dict = {
            "Group": "bi-people-fill",
            "User": "bi-person-fill",
            "Computer": "bi-hdd-network",
        }

        dicts_per_source = {}

        for d in self.can_read_laps:
            source_name = d["source_name"]
            label = [e for e in d["source_labels"] if "Base" not in e][0]

            key = source_name + "|" + label
            if key not in dicts_per_source:
                dicts_per_source[key] = []
            dicts_per_source[key].append(d)

        for key in dicts_per_source:
            tmp_data = {}
            first_dict = dicts_per_source[key][0]
            label = [e for e in first_dict["source_labels"] if "Base" not in e][0]

            tmp_data["domain"] = (
                '<i class="bi bi-globe2"></i>' + first_dict["source_domain"]
            )
            tmp_data["name"] = (
                f'<i class="bi {icon_dict[label]}"></i>' + first_dict["source_name"]
            )
            tmp_data["computers"] = grid_data_stringify(
                {
                    "link": f"can_read_laps_from_{quote(key)}.html",
                    "value": f'{len(dicts_per_source[key])} computer{"s" if len(dicts_per_source[key]) > 1 else ""}',
                    "before_link": f"<i class='<i bi bi-hdd-network {str(len(dicts_per_source[key])).zfill(6)}'></i>",
                }
            )
            subpage = Page(
                self.arguments.cache_prefix,
                f"can_read_laps_from_{key}",
                f'Objects whose LAPS password can be read by {first_dict["source_name"]}',
                self.get_dico_description(),
            )
            subgrid = Grid(
                f'Objects whose LAPS password can be read by {first_dict["source_name"]}'
            )
            subgrid.setheaders(["domain", "name", "interest"])

            subdata = []
            max_interest = 0

            for d in dicts_per_source[key]:
                tmp_subdata = {}
                tmp_subdata["domain"] = (
                    '<i class="bi bi-globe2"></i>' + d["target_domain"]
                )
                tmp_subdata["name"] = (
                    '<i class="bi bi-hdd-network"></i>' + d["target_name"]
                )
                interest = get_interest(
                    self.requests_results, "Computer", d["target_name"]
                )
                max_interest = max(max_interest, interest)
                color = {3: "red", 2: "orange", 1: "yellow"}.get(interest, "green")
                tmp_subdata["interest"] = (
                    f"<span class='{interest}'></span><i class='bi bi-star-fill' style='color: {color}'></i>"
                    * interest
                    + f"<i class='bi bi-star' style='color: {color}'></i>"
                    * (3 - interest)
                )

                subdata.append(tmp_subdata)

            subgrid.setData(subdata)
            subpage.addComponent(subgrid)
            subpage.render()

            self.max_max_interest = max(self.max_max_interest, max_interest)
            color = {3: "red", 2: "orange", 1: "yellow"}.get(max_interest, "green")
            tmp_data["interest"] = (
                f"<span class='{max_interest}'></span><i class='bi bi-star-fill' style='color: {color}'></i>"
                * max_interest
                + f"<i class='bi bi-star' style='color: {color}'></i>"
                * (3 - max_interest)
            )
            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(dicts_per_source.keys())

        self.name_description = f"{self.data} objects can read LAPS passwords"
        # )

    def get_rating(self) -> int:
        if self.data == 0:
            return 5
        elif self.max_max_interest < 1:
            return 3
        elif self.max_max_interest < 3:
            return 2
        return 1
