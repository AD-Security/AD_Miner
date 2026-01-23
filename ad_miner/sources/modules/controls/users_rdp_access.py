from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import percentage_superior

from urllib.parse import quote


@register_control
class users_rdp_access(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "users_rdp_access"

        self.title = "RDP access (users)"
        self.description = "Users who are allowed to access computers through Remote Desktop Protocol (RDP)."
        self.risk = "With this privilege, a user can remotely spawn an graphical interactive session on a machine. RDP access allows attackers to pivot in the network."
        self.poa = "Review this list to ensure RDP access is legitimate."

        self.users_rdp_access = requests_results["rdp_access"]
        self.users_rdp_access_1 = (
            dict(
                sorted(
                    self.parseRDPData(self.users_rdp_access).items(),
                    key=lambda x: len(x[1]),
                    reverse=True,
                )
            )
            if self.users_rdp_access is not None
            else None
        )

        self.users = requests_results["nb_enabled_accounts"]

    def run(self):
        if self.users_rdp_access_1 is None:
            return
        headers = ["Users", "Computers"]
        formated_data = []
        for key in self.users_rdp_access_1:
            sortClass = str(len(self.users_rdp_access_1[key])).zfill(6)
            d = {
                "Users": '<i class="bi bi-person-fill"></i>' + key,
                "Computers": grid_data_stringify(
                    {
                        "value": f"{len(self.users_rdp_access_1[key])} Computers <p style='display: none;'>{self.users_rdp_access_1[key]}</p>",
                        "link": f"users_rdp_access.html?parameter={quote(str(key))}",
                        "before_link": f'<i class="bi bi-pc-display {sortClass}"></i>',
                    }
                ),
            }
            formated_data.append(d)
        page = Page(
            self.arguments.cache_prefix,
            "users_rdp_access",
            "Users with RDP access",
            self.get_dico_description(),
        )
        grid = Grid("Users with RDP access")
        grid.setheaders(headers)
        grid.setData(formated_data)
        page.addComponent(grid)
        page.render()

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = len(self.users_rdp_access_1) if self.users_rdp_access_1 else 0

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.data} users with RDP access"

    def get_rating(self) -> int:
        # TODO define the rating function.
        # You can use common rating functions define in ad_miner.sources.modules.common_analysis like presenceof, percentage_superior, etc.
        # -1 = grey, 1 = red, 2 = orange, 3 = yellow, 4 =green, 5 = green,
        return percentage_superior(
            self.users_rdp_access_1, self.users, criticity=3, percentage=0.5
        )

    def parseRDPData(self, list_of_dict):
        final_dict = {}
        for dict in list_of_dict:
            if dict["user"] in final_dict.keys():
                final_dict[dict["user"]] += [dict["computer"]]
            else:
                final_dict[dict["user"]] = [dict["computer"]]
        return final_dict
