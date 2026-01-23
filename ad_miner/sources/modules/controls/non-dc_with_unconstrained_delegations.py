from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules import logger
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.node_neo4j import Node
from ad_miner.sources.modules.path_neo4j import Path

from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of, createGraphPage

from urllib.parse import quote


@register_control
class non_dc_with_unconstrained_delegations(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "kerberos"

        # Do NOT change existing control_key, as it will break evolution with older ad miner versions
        self.control_key = "non-dc_with_unconstrained_delegations"

        self.title = "Kerberos unconstrained delegations"
        self.description = "These objects are allowed to connect to any service with the identity of another user who connected to them."
        self.interpretation = ""
        self.risk = "These objects can impersonate any domain and eventually lead to full compromise of the infrastructure. Optimally, this list should be empty as delegation should be set up with constrained delegation."
        self.poa = "Unless necessary, switch to constrained delegation for a safer infrastructure."

        self.kud = requests_results["kud"]
        self.kud_graphs = {}

        self.graph_path_objects_to_unconstrained_delegation_users = {
            "description": "Path to user accounts that are allowed to connect to any service with the identity of another user who connected to them.",
            "risk": "These accounts can impersonate any domain and eventually lead to full compromise of the infrastructure. Optimally, this list should be empty as delegation should be set up with constrained delegation.",
            "poa": "Unless necessary, switch to constrained delegation for a safer infrastructure.",
        }

    def run(self):
        if self.kud is None:
            return
        logger.print_debug("Generate paths to Kerberos Unconstrained Delegations")

        for path in self.kud:
            if not self.kud_graphs.get(path.nodes[-1].name):
                self.kud_graphs[path.nodes[-1].name] = [path]
            else:
                self.kud_graphs[path.nodes[-1].name].append(path)

        page = Page(
            self.arguments.cache_prefix,
            "non-dc_with_unconstrained_delegations",
            "Path to Unconstrained Delegations",
            self.get_dico_description(),
        )
        grid = Grid(
            "Numbers of path to domain admin using Kerberos Unconstrained Delegations"
        )
        grid_data = []

        self.kud_list = self.kud_graphs.keys()

        for end_node in self.kud_list:
            # if len(self.kud_graphs[end_node]):
            node = self.kud_graphs[end_node][0].nodes[-1]
            node.relation_type = "UnconstrainedDelegations"
            domain = node.domain
            end = Node(
                id=42424243,
                labels="Domain",
                name=domain,
                domain="end",
                tenant_id=None,
                relation_type="UnconstrainedDelegations",
            )
            path = Path([self.kud_graphs[end_node][0].nodes[-1], end])
            self.kud_graphs[end_node].append(path)

            createGraphPage(
                self.arguments.cache_prefix,
                end_node + "_kud_graph",
                "Paths to Unconstrained Delegations",
                self.graph_path_objects_to_unconstrained_delegation_users,
                self.kud_graphs[end_node],
                self.requests_results,
            )

            tmp_data = {}

            if node.labels == "User":
                pretty_name = f'<i class="bi bi-person-fill"></i>{end_node}'
            elif node.labels == "Computer":
                pretty_name = f'<i class="bi bi-pc-display"></i>{end_node}'
            else:
                pretty_name = end_node

            tmp_data["Configured for Kerberos Unconstrained Delegation"] = pretty_name
            tmp_data["Compromise Paths"] = grid_data_stringify(
                {
                    "value": f'{len(self.kud_graphs[end_node])} <i class="bi bi-sign-turn-right 000001"></i>',
                    "link": "%s_kud_graph.html" % quote(str(end_node)),
                }
            )

            grid_data.append(tmp_data)
        headers = [
            "Configured for Kerberos Unconstrained Delegation",
            "Compromise Paths",
        ]
        grid.setheaders(headers)
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.kud_list) if self.kud_list else 0

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.data} objects with unconstrained delegations"

    def get_rating(self) -> int:
        return presence_of(self.kud_list, criticity=1)
