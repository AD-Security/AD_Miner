from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify

from ad_miner.sources.modules.common_analysis import presence_of

from urllib.parse import quote


@register_control
class TestControle1(Control):
    "This is my control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)
        self.azure_or_onprem = "on_premise"
        self.control_key = "users_shadow_credentials_to_non_admins"
        self.category = "kerberos"

        self.title = "Shadow Credentials on regular accounts"
        self.description = "Users that can perform a shadow credentials attack and impersonate unprivileged accounts. It allows user to use a key for authentication."
        self.interpretation = ""
        self.risk = "This feature can be used by malicious actors to stealthily setup a persistant access."
        self.poa = "Review these privileges and it is advised to check if no malicious actors have used this feature for a previous attack."

        self.users_shadow_credentials_to_non_admins = requests_results[
            "users_shadow_credentials_to_non_admins"
        ]

    def run(self):
        if self.users_shadow_credentials_to_non_admins is None:
            return

        data = {}
        for path in self.users_shadow_credentials_to_non_admins:
            try:
                data[path.nodes[-1]]["paths"].append(path)
            except KeyError:
                data[path.nodes[-1]] = {
                    "domain": path.nodes[-1].domain,
                    "target": path.nodes[-1].name,
                    "paths": [path],
                }
        grid_data = []
        max_paths = 0
        for target in data.keys():
            nb_paths = len(data[target]["paths"])
            max_paths = max(max_paths, nb_paths)
            sortClass = str(nb_paths).zfill(6)
            grid_data.append(
                {
                    "domain": '<i class="bi bi-globe2"></i>' + data[target]["domain"],
                    "target": '<i class="bi bi-bullseye"></i>' + data[target]["target"],
                    "paths": grid_data_stringify(
                        {
                            "value": f"{nb_paths} paths to target",
                            "link": f"users_shadow_credentials_to_non_admins_to_{quote(str(data[target]['target']))}.html",
                            "before_link": f"<i class='bi bi-sign-turn-right {sortClass}' aria-hidden='true'></i>",
                        }
                    ),
                }
            )
            graph_page = Page(
                self.arguments.cache_prefix,
                f"users_shadow_credentials_to_non_admins_to_{data[target]['target']}",
                "List of targets that can be compromised through shadow credentials",
                self.get_dico_description(),
            )
            graph = Graph()
            graph.setPaths(data[target]["paths"])
            graph_page.addComponent(graph)
            graph_page.render()

        if self.users_shadow_credentials_to_non_admins != None:
            self.max_number_users_shadow_credentials_to_non_admins = max_paths
        else:
            self.max_number_users_shadow_credentials_to_non_admins = 0

        page = Page(
            self.arguments.cache_prefix,
            "users_shadow_credentials_to_non_admins",
            "List of targets that can be compromised through shadow credentials",
            self.get_dico_description(),
        )
        grid = Grid("Users")
        grid.setheaders(["domain", "target", "paths"])
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = (
            self.max_number_users_shadow_credentials_to_non_admins
            if self.max_number_users_shadow_credentials_to_non_admins
            else 0
        )
        self.name_description = f"{self.data} users can impersonate other accounts"

    def get_rating(self) -> int:
        return presence_of(self.users_shadow_credentials_to_non_admins, criticity=2)
