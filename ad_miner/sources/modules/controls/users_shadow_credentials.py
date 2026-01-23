from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.graph_class import Graph

from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of

from urllib.parse import quote


@register_control
class users_shadow_credentials(Control):  # TODO change the class name
    "Legacy control"  # TODO small documentation here

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "kerberos"
        self.control_key = "users_shadow_credentials"

        self.title = "Shadow Credentials on privileged accounts"
        self.description = "The following list shows users having sufficient privileges to perform shadow credentials on target privileged users."
        self.risk = "This list should be strictly empty, as it otherwise represents a major security flaw. This attack allows impersonnation of privileged users. Performing this attack relies on a particular kerberos authentication mode and would not be noticed by victims."
        self.poa = "All these users should have their privilege reduced so that this attack is not possible anymore."

        self.users_shadow_credentials = requests_results["users_shadow_credentials"]
        self.users_shadow_credentials_uniq = []

    def run(self):
        if self.users_shadow_credentials is None:
            return
        page = Page(
            self.arguments.cache_prefix,
            "users_shadow_credentials",
            "List of non-privileged users that can perform shadow credentials on privileged accounts",
            self.get_dico_description(),
        )
        # Build raw data from requests
        data = {}
        for path in self.users_shadow_credentials:
            try:
                data[path.nodes[0]]["paths"].append(path)
                if path.nodes[-1].name not in data[path.nodes[0]]["target"]:
                    data[path.nodes[0]]["target"].append(path.nodes[-1].name)
            except KeyError:
                data[path.nodes[0]] = {
                    "domain": path.nodes[0].domain,
                    "name": path.nodes[0].name,
                    "target": [path.nodes[-1].name],
                    "paths": [path],
                }

        # Build grid data
        grid_data = []
        for d in data.values():
            sortClass = str(len(d["paths"])).zfill(6)
            tmp_grid_data = {
                "domain": '<i class="bi bi-globe2"></i>' + d["domain"],
                "name": '<i class="bi bi-person-fill"></i>' + d["name"],
                "target": grid_data_stringify(
                    {
                        "value": f"{len(d['paths'])} paths to {len(d['target'])} target{'s' if len(d['target'])>1 else ''}",
                        "link": f"users_shadow_credentials_from_{quote(str(d['name']))}.html",
                        "before_link": f"<i class='{sortClass} bi bi-sign-turn-right' aria-hidden='true'></i>",
                    }
                ),
            }
            grid_data.append(tmp_grid_data)
            # Build graph data
            page_graph = Page(
                self.arguments.cache_prefix,
                f"users_shadow_credentials_from_{d['name']}",
                f"{d['name']} shadow credentials attack paths on privileged accounts",
                self.get_dico_description(),
            )
            graph = Graph()
            graph.setPaths(d["paths"])
            page_graph.addComponent(graph)
            page_graph.render()

        self.users_shadow_credentials_uniq = data.keys()
        grid = Grid("Shadow credentials")
        grid.setheaders(["domain", "name", "target"])
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.users_shadow_credentials_uniq)
            if self.users_shadow_credentials_uniq
            else 0
        )

        self.name_description = f"{self.data} users can impersonate privileged accounts"

    def get_rating(self) -> int:
        return presence_of(self.users_shadow_credentials)
