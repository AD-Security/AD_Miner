from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import percentage_superior

from urllib.parse import quote


@register_control
class computers_list_of_rdp_users(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "computers_list_of_rdp_users"

        self.title = "RDP access (computers)"
        self.description = (
            "Computers which can be accessed with Remote Desktop Protocol (RDP)."
        )
        self.risk = "For each computer, the lower the number, the better. Overall, the total number of computers with RDP access should be as low as possible. RDP access allows attackers to pivot in the network."
        self.poa = (
            "Review this list to ensure RDP access is legitimate on these machines."
        )

        self.users_rdp_access = requests_results["rdp_access"]
        self.users_rdp_access_2 = (
            dict(
                sorted(
                    self.parseRDPdataByHosts(self.users_rdp_access).items(),
                    key=lambda x: len(x[1]),
                    reverse=True,
                )
            )
            if self.users_rdp_access is not None
            else None
        )
        self.users = requests_results["nb_enabled_accounts"]

    def run(self):
        if self.users_rdp_access_2 is None:
            return
        # headers = ["Computers", "Number of users", "Users"]
        # formated_data = generic_formating.formatGridValues3Columns(
        #    generic_formating.formatFor3Col(self.users_rdp_access_2, headers),
        #    headers,
        #    "computers_list_of_rdp_users",
        # )
        headers = ["Computers", "Users"]
        formated_data = []
        for key in self.users_rdp_access_2:
            sortClass = str(len(self.users_rdp_access_2[key])).zfill(6)
            d = {
                "Computers": '<i class="bi bi-pc-display"></i>' + key,
                "Users": grid_data_stringify(
                    {
                        "value": f"{len(self.users_rdp_access_2[key])} Users <p style='display: none;'>{self.users_rdp_access_2[key]}</p>",
                        "link": f"computers_list_of_rdp_users.html?parameter={quote(str(key))}",
                        "before_link": f'<i class="bi bi-person-fill {sortClass}"></i>',
                    }
                ),
            }
            formated_data.append(d)
        page = Page(
            self.arguments.cache_prefix,
            "computers_list_of_rdp_users",
            "Computers that can be accessed through RDP",
            self.get_dico_description(),
        )
        grid = Grid("Computers' lists of RDP users")
        grid.setheaders(headers)
        grid.setData(formated_data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.users_rdp_access_2) if self.users_rdp_access_2 else 0
        self.name_description = f"{self.data} computers with RDP access"

    def get_rating(self) -> int:
        return percentage_superior(
            self.users_rdp_access_2, self.users, criticity=3, percentage=0.5
        )

    def parseRDPdataByHosts(self, list_of_dict):
        final_dict = {}
        for dict in list_of_dict:
            if dict["computer"] in final_dict.keys():
                final_dict[dict["computer"]] += [dict["user"]]
            else:
                final_dict[dict["computer"]] = [dict["user"]]
        return final_dict
