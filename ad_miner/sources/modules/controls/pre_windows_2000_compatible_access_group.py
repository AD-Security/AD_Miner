from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules import generic_formating


@register_control
class pre_windows_2000_compatible_access_group(Control):
    "Docstring of my control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "pre_windows_2000_compatible_access_group"

        self.title = '"Pre-Windows 2000 Compatible Access" group'
        self.description = (
            'Inadequate object in "Pre-Windows 2000 Compatible Access" group.'
        )
        self.risk = 'Membership of the "Pre-Windows 2000 Compatible Access" group allows to enumerate elements of the Active Directory.'
        self.poa = 'The Pre-Windows 2000 Compatible Access group must contain only "Authenticated Users".'

        self.pre_windows_2000_compatible_access_group = requests_results[
            "pre_windows_2000_compatible_access_group"
        ]

    def run(self):
        if self.pre_windows_2000_compatible_access_group is None:
            self.pre_windows_2000_compatible_access_group = []

        page = Page(
            self.arguments.cache_prefix,
            "pre_windows_2000_compatible_access_group",
            "Pre-Windows 2000 Compatible Access group",
            self.get_dico_description(),
        )
        grid = Grid("Pre-Windows 2000 Compatible Access")
        grid.setheaders(["Domain", "Name", "Rating"])

        # Sort accounts with anonymous accounts first
        sorted_list = [
            dni
            for dni in self.pre_windows_2000_compatible_access_group
            if "1-5-7" in dni[2]
        ]
        sorted_list += [
            dni
            for dni in self.pre_windows_2000_compatible_access_group
            if "1-5-7" not in dni[2]
        ]

        data = []

        for domain, account_name, objectid, type_list in sorted_list:
            tmp_data = {"Domain": '<i class="bi bi-globe2"></i>' + domain}

            type_clean = generic_formating.clean_label(type_list)

            tmp_data["Name"] = (
                f"{generic_formating.get_label_icon(type_clean)} {account_name}"
            )

            tmp_data["Rating"] = (
                '<i class="bi bi-star-fill" style="color: orange"></i><i class="bi bi-star-fill" style="color: orange"></i><i class="bi bi-star" style="color: orange"></i>'
                if "1-5-7" not in objectid
                else '<i class="bi bi-star-fill" style="color: red"></i><i class="bi bi-star-fill" style="color: red"></i><i class="bi bi-star-fill" style="color: red"></i> Anonymous'
            )
            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.pre_windows_2000_compatible_access_group)
        self.name_description = f"{len(self.pre_windows_2000_compatible_access_group)} inadequate membership users in Pre-Win $2000$ Compatible Access group"

    def get_rating(self) -> int:
        if self.pre_windows_2000_compatible_access_group is None:
            return -1
        if True in [
            "1-5-7" in dni[2] for dni in self.pre_windows_2000_compatible_access_group
        ]:
            return 2
        elif len(self.pre_windows_2000_compatible_access_group) > 0:
            return 3
        else:
            return 5
