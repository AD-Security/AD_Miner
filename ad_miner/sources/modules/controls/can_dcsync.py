from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of, createGraphPage

from urllib.parse import quote


@register_control
class can_dcsync(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "can_dcsync"

        self.title = "Inadequate access to DCSync privileges"
        self.description = "All these domain objects are granted DCSync privileges and can, as such, dump all data from Active Directory"
        self.risk = "Only servers that require DCSync should have this privilege. A misconfiguration of DCSync privilege could result in the dump of all data in the AD (including, users and password hashes)."
        self.poa = "Review this list and check for any anomaly."

        self.dico_name_description_can_dcsync_graph = {
            "description": "List of paths to a dcsync account.",
            "risk": "These paths lead to accounts that have DCSync privileges. If one of these paths is exploited, the attacker will be able to dump all data from Active Directory (including users and machines password hashes). ",
            "poa": "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface.",
        }

        self.objects_to_dcsync = requests_results["objects_to_dcsync"]
        self.dcsync_list = requests_results["dcsync_list"]
        self.users_nb_domain_admins = requests_results["nb_domain_admins"]

        self.dcsync_paths = (
            requests_results["set_dcsync1"] + requests_results["set_dcsync2"]
        )
        end_nodes = []

        # Check if dcsync path is activated or not
        if self.objects_to_dcsync == None:
            # Placeholder to fill the list for the rating
            self.can_dcsync_nodes = ["1"] * len(self.dcsync_list)
        else:
            for p in self.objects_to_dcsync:
                end_nodes.append(p.nodes[-1])  # Get last node of the path
            end_nodes = list(set(end_nodes))

            self.can_dcsync_nodes = end_nodes

    def run(self):
        if self.objects_to_dcsync == None:
            self.genNodesDCsyncLightPage()
        else:
            self.genFullDCSync()

        self.data = len(self.can_dcsync_nodes) if self.can_dcsync_nodes else 0

        self.name_description = f"{self.data} non DA/DC objects have DCSync privileges"

    def genFullDCSync(self):

        data = []
        for n in self.can_dcsync_nodes:
            # Graph path to DCSync

            paths_left = []
            for path in self.objects_to_dcsync:
                if path.nodes[-1].name == n.name:
                    paths_left.append(path)

            createGraphPage(
                self.arguments.cache_prefix,
                f"path_to_{n.name}_with_dcsync",
                f"DCsync path for {n.name}",
                self.dico_name_description_can_dcsync_graph,
                paths_left,
                self.requests_results,
            )

            # Graph DCSync detail
            page = Page(
                self.arguments.cache_prefix,
                f"dcsync_from_{n.name}",
                f"DCSync detail for {n.name}",
                self.dico_name_description_can_dcsync_graph,
            )
            graph = Graph()

            paths_right = []
            for path in self.dcsync_paths:
                if path.nodes[0].name == n.name:
                    paths_right.append(path)

            graph.setPaths(paths_right)
            page.addComponent(graph)
            page.render()

            if n.labels.lower() == "user":
                type_icon = '<i class="bi bi-person-fill"></i>'
            elif n.labels.lower() == "group":
                type_icon = '<i class="bi bi-people-fill"></i>'
            else:
                type_icon = '<i class="bi bi-question-circle-fill"></i>'

            if n.name in self.users_nb_domain_admins:
                name_icon = '<i class="bi bi-gem stats-icon"></i>'
            else:
                name_icon = type_icon

            sortClass = str(len(paths_left)).zfill(6)
            data.append(
                {
                    "domain": '<i class="bi bi-globe2"></i>' + n.domain,
                    "type": type_icon + " " + n.labels,
                    "name": name_icon + " " + n.name,
                    "path to account": grid_data_stringify(
                        {
                            "link": "path_to_%s_with_dcsync.html" % quote(str(n.name)),
                            "value": f"{len(paths_left)} paths",
                            "before_link": f"<i class='bi bi-sign-turn-right {sortClass}' aria-hidden='true'></i>",
                        }
                    ),
                    "path to dcsync": grid_data_stringify(
                        {
                            "link": "dcsync_from_%s.html" % quote(str(n.name)),
                            "value": f"DCSync path",
                            "before_link": f"<i class='bi bi-sign-turn-right {sortClass}' aria-hidden='true'></i>",
                        }
                    ),
                }
            )

        page = Page(
            self.arguments.cache_prefix,
            "can_dcsync",
            "Inadequate access to DCSync privileges",
            self.get_dico_description(),
        )
        grid = Grid("DCsync objects")
        headers = ["domain", "type", "name", "path to account", "path to dcsync"]
        grid.setheaders(headers)
        grid.setData(data)
        page.addComponent(grid)
        page.render()

    def genNodesDCsyncLightPage(self, neo4j):
        page = Page(
            self.arguments.cache_prefix,
            "can_dcsync",
            "Inadequate access to DCSync privileges",
            self.get_dico_description(),
        )
        paths = (
            neo4j.all_requests["set_dcsync1"]["result"]
            + neo4j.all_requests["set_dcsync2"]["result"]
        )
        raw_data = {}
        for e in self.dcsync_list:
            raw_data[e["name"]] = {
                "domain": e["domain"],
                "name": e["name"],
                "target graph": {},
                "paths": [],
            }
        for path in paths:
            try:
                raw_data[path.nodes[0].name]["paths"].append(path)
            except KeyError:
                continue
        data = []
        # print(raw_data)
        for k in raw_data.keys():
            graph_page = Page(
                self.arguments.cache_prefix,
                f"can_dcsync_from_{raw_data[k]['name']}",
                f"DCSync from {raw_data[k]['name']}",
                self.get_dico_description(),
            )
            graph = Graph()
            graph.setPaths(raw_data[k]["paths"])
            graph_page.addComponent(graph)
            graph_page.render()
            sortClass = str(len(raw_data[k]["paths"])).zfill(6)
            raw_data[k]["target graph"][
                "link"
            ] = f"can_dcsync_from_{quote(str(raw_data[k]['name']))}.html"
            raw_data[k]["target graph"][
                "value"
            ] = f"<i class='bi bi-sign-turn-right {sortClass}' aria-hidden='true'></i>View paths ({len(raw_data[k]['paths'])})"
            data.append(
                {
                    "domain": raw_data[k]["domain"],
                    "name": raw_data[k]["name"],
                    "target graph": raw_data[k]["target graph"],
                }
            )
        grid = Grid("DCsync objects")
        headers = ["domain", "name", "target graph"]
        grid.setheaders(headers)
        grid.setData(data)
        page.addComponent(grid)
        page.render()

    def get_rating(self) -> int:
        return presence_of(self.can_dcsync_nodes)
