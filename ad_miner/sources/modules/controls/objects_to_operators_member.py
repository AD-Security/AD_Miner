from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of

from urllib.parse import quote


@register_control
class objects_to_operators_member(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "objects_to_operators_member"

        self.title = "Paths to Operators Groups"
        self.description = "Objects with a compromission path to an Operator Group."
        self.risk = "As Oprator Groups have high privilege, a compromission path to one is a major threat to the security of the domain."
        self.poa = "Review all these paths and try to remove as many dangerous links as possible."

        self.objects_to_operators_member = requests_results[
            "objects_to_operators_member"
        ]
        self.objects_to_operators_groups = requests_results[
            "objects_to_operators_groups"
        ]

    def run(self):
        page = Page(
            self.arguments.cache_prefix,
            "objects_to_operators_member",
            "Paths to Operators Groups",
            self.get_dico_description(),
        )
        # Build raw data from requests
        data = {}
        for path in self.objects_to_operators_groups:
            try:
                data[path.nodes[0].name]["paths"].append(path)
                if path.nodes[-1].name not in data[path.nodes[0].name]["target"]:
                    data[path.nodes[0].name]["target"].append(path.nodes[-1].name)
            except KeyError:
                data[path.nodes[0].name] = {
                    "domain": '<i class="bi bi-globe2"></i>' + path.nodes[-1].domain,
                    "name": '<i class="bi bi-people-fill"></i>' + path.nodes[0].name,
                    "link": quote(str(path.nodes[0].name)),
                    "target": [path.nodes[-1].name],
                    "paths": [path],
                }
        # print(data)
        for path in self.objects_to_operators_member:
            try:
                data[path.nodes[-1].name]["paths"].append(path)
            except (
                KeyError
            ):  # Really **should not** happen, but to prevent crash in case of corrupted cache/db
                data[path.nodes[-1].name] = {
                    "domain": '<i class="bi bi-globe2"></i>' + path.nodes[-1].domain,
                    "name": '<i class="bi bi-people-fill"></i>' + path.nodes[-1].name,
                    "link": quote(str(path.nodes[-1].name)),
                    "target": [""],
                    "paths": [path],
                }

        # Build grid data
        grid_data = []
        for d in data.values():
            sortClass = str(len(d["paths"])).zfill(6)
            tmp_grid_data = {
                "domain": d["domain"],
                "name": d["name"],
                "paths": grid_data_stringify(
                    {
                        "value": f"{len(d['paths'])} paths target{'s' if len(d['target'])>1 else ''}",
                        "link": f"objects_to_operators_{quote(str(d['link']))}.html",
                        "before_link": f"<i class='{sortClass} bi bi-sign-turn-right' aria-hidden='true'></i>",
                    }
                ),
                "targets": ",".join(d["target"]),
            }
            grid_data.append(tmp_grid_data)
            # Build graph data
            page_graph = Page(
                self.arguments.cache_prefix,
                f"objects_to_operators_{d['link']}",
                f"Paths to Operator group using {d['name']}",
                self.get_dico_description(),
            )
            graph = Graph()
            graph.setPaths(d["paths"])
            page_graph.addComponent(graph)
            page_graph.render()

        self.objects_to_operators_member = data.keys()
        grid = Grid("Objects with path to Operator Groups")
        grid.setheaders(["domain", "name", "paths", "targets"])
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.objects_to_operators_member)
            if len(self.objects_to_operators_member)
            else 0
        )
        self.name_description = f"{self.data} paths to Operators Groups"

    def get_rating(self) -> int:
        return presence_of(self.objects_to_operators_member)
