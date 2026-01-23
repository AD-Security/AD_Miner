from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.graph_class import Graph

from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of

from urllib.parse import quote


@register_control
class objects_to_adcs(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"

        # Do NOT change existing control_key, as it will break evolution with older ad miner versions
        self.control_key = "objects_to_adcs"

        self.title = "Non-tier 0 local admin privs on ADCS"
        self.description = "ADCS (Active Directory Certificate Services) is a Windows Server feature that provides a customizable certification authority (CA) for issuing and managing digital certificates. Digital certificates are used to authenticate and secure communication between devices, servers, and users on a network."
        self.interpretation = ""
        self.risk = "These ADCS servers can be compromised, which means that an attacker can issue fraudulent certificates, which can be used to impersonate legitimate users or servers on the network. This can lead to unauthorized access to sensitive information, data theft, or network disruption."
        self.poa = "Ensure that the existing privileges on these ADCS servers are legitimate and limit them to administrators optimaly."

        self.objects_to_adcs = requests_results["objects_to_adcs"]

        self.path_to_adcs_name_description = {
            "title": "Non-tier 0 local admin privs on ADCS",
            "description": "Non-tier 0 local admin privs on ADCS",
            "risk": "This ADCS server can be compromised, which means that an attacker can issue fraudulent certificates, which can be used to impersonate legitimate users or servers on the network. This can lead to unauthorized access to sensitive information, data theft, or network disruption.",
            "poa": "Ensure that the existing privileges on this ADCS server are legitimate and limit them to administrators optimaly.",
        }

    def run(self):
        if self.objects_to_adcs is None:
            return

        self.total_paths = 0

        page = Page(
            self.arguments.cache_prefix,
            "objects_to_adcs",
            "Non-tier 0 local admin privs on ADCS",
            self.get_dico_description(),
        )
        grid = Grid("Objects to ADCS servers")
        grid.setheaders(["Domain", "Name", "Path to ADCS"])

        self.ADCS_path_sorted = {}
        self.ADCS_entry_point = []
        self.unique_starting_points = {}

        for path in self.objects_to_adcs:
            self.unique_starting_points[path.nodes[0].id] = True
            self.ADCS_entry_point.append(path.nodes[0].name)
            try:
                self.ADCS_path_sorted[path.nodes[-1].name].append(path)
            except KeyError:
                self.ADCS_path_sorted[path.nodes[-1].name] = [path]

        self.ADCS_entry_point = list(set(self.ADCS_entry_point))

        cleaned_data = []

        for key, paths in self.ADCS_path_sorted.items():
            tmp_data = {}
            tmp_data["Domain"] = (
                '<i class="bi bi-globe2"></i>' + paths[0].nodes[-1].domain
            )
            tmp_data["Name"] = '<i class="bi bi-server"></i>' + key
            nb_path_to_adcs = len(paths)
            self.total_paths += nb_path_to_adcs
            sortClass = str(nb_path_to_adcs).zfill(6)
            tmp_data["Path to ADCS"] = grid_data_stringify(
                {
                    "link": "path_to_adcs_%s.html" % quote(str(key)),
                    "value": f"{nb_path_to_adcs} paths to ADCS",
                    "before_link": f"<i class='bi bi-sign-turn-right-fill {sortClass}' style='color:#b00404;' aria-hidden='true'></i>",
                }
            )
            cleaned_data.append(tmp_data)

            graph_page = Page(
                self.arguments.cache_prefix,
                "path_to_adcs_%s" % key,
                "Path to ADCS through " + key,
                self.path_to_adcs_name_description,
            )
            graph = Graph()
            graph.setPaths(paths)
            graph_page.addComponent(graph)
            graph_page.render()

        grid.setData(cleaned_data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.unique_starting_points.keys())

        self.name_description = (
            f"{self.data} non-tier-$0$ with local admin privileges on ADCS"
        )

    def get_rating(self) -> int:
        return presence_of(self.ADCS_path_sorted.keys())
