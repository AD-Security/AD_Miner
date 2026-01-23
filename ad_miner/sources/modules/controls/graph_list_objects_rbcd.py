from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules import logger
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of, createGraphPage

from urllib.parse import quote
from tqdm import tqdm


@register_control
class graph_list_objects_rbcd(Control):  # TODO change the class name
    "Docstring of my control"  # TODO small documentation here

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "kerberos"
        self.control_key = "graph_list_objects_rbcd"

        self.title = "Kerberos RBCD against computers"
        self.description = (
            "Users that can perform Ressource-Based Constrained Delegation attacks"
        )
        self.risk = "Users that have GenericWrite ACE on machines can perform RBCD attacks. Thanks to the GenericWrite access, the attacker can edit the 'msDS-AllowedToActOnBehalfOfOtherIdentity' attribute of the targeted machine and add an attacker-controlled account to it in order to impersonate any account of the domain. In short, if the attacker has GenericWrite over the target machine, then they can have local administration privileges. An attacker could take advantage of this misconfiguration to further compromise the domains."
        self.poa = "In order to perform RBCD attacks, the attackers need to use an account with a Service Principal Name. In order to make it more difficult for them, you cant reduce the 'MachineAccountQuota' domain-level attribute to 0 so that an attacker cannot create an SPN-enabled account for himself. What's more, review all the GenericWrite ACEs you can find and ask yourself if they are legitimate or if they could be removed."

        self.dico_description_rbcd_to_da = {
            "title": "Compromission paths to domain admins",
            "description": "Compromission paths from some Active Directory object to domain admin privileges.",
            "risk": "Compromission paths to domain admin represent the exposed attack surface that the AD environment presents to the attacker in order to gain privileges in the domain(s). If an attacker exploits one of these paths, they will be able to gain privileges in the domain(s) and cause some serious damage.",
            "poa": "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface.",
        }

        self.rbcd_paths = requests_results["graph_rbcd"]
        self.rbcd_paths_to_da = requests_results["graph_rbcd_to_da"]

        self.rbcd_to_da_graphs = {}
        self.rbcd_graphs = {}

        self.rbcd_nb_start_nodes = 0
        self.rbcd_nb_end_nodes = 0

    def run(self):
        if self.rbcd_paths is None:
            return
        logger.print_debug("Generate paths of objects that can RCBD on a computer")

        for path in self.rbcd_paths_to_da:
            starting_node = path.nodes[0]
            starting_node_name = starting_node.name
            if starting_node_name not in list(self.rbcd_to_da_graphs.keys()):
                self.rbcd_to_da_graphs[starting_node_name] = {}
                self.rbcd_to_da_graphs[starting_node_name]["paths"] = []
            if path not in self.rbcd_to_da_graphs[starting_node_name]["paths"]:
                self.rbcd_to_da_graphs[starting_node_name]["paths"].append(path)

        for object_name in list(self.rbcd_to_da_graphs.keys()):
            createGraphPage(
                self.arguments.cache_prefix,
                "rbcd_target_" + object_name + "_paths_to_da",
                "Path to DA from " + object_name + " RBCD target",
                self.dico_description_rbcd_to_da,
                self.rbcd_to_da_graphs[object_name]["paths"],
                requests_results=self.requests_results,
            )

        ending_nodes_names_distinct = []

        for path in tqdm(self.rbcd_paths):
            starting_node = path.nodes[0]
            starting_node_name = starting_node.name
            ending_node = path.nodes[-1]
            ending_node_name = ending_node.name

            if starting_node_name not in list(self.rbcd_graphs.keys()):
                self.rbcd_nb_start_nodes += 1
                self.rbcd_graphs[starting_node_name] = {}
                self.rbcd_graphs[starting_node_name]["paths"] = []
                self.rbcd_graphs[starting_node_name]["nb_paths_to_da"] = 0
                self.rbcd_graphs[starting_node_name]["destinations"] = []
                self.rbcd_graphs[starting_node_name]["domain"] = starting_node.domain
            if path not in self.rbcd_graphs[starting_node_name]["paths"]:
                self.rbcd_graphs[starting_node_name]["paths"].append(path)
            if (
                ending_node_name
                not in self.rbcd_graphs[starting_node_name]["destinations"]
            ):
                self.rbcd_graphs[starting_node_name]["destinations"].append(
                    ending_node_name
                )
            if ending_node_name not in ending_nodes_names_distinct:
                self.rbcd_nb_end_nodes += 1
                ending_nodes_names_distinct.append(ending_node_name)

        for object_name in list(self.rbcd_graphs.keys()):

            createGraphPage(
                self.arguments.cache_prefix,
                object_name + "_rbcd_graph",
                "Attack paths of accounts that can RBCD",
                self.get_dico_description(),
                self.rbcd_graphs[object_name]["paths"],
                self.requests_results,
            )

            sub_page = Page(
                self.arguments.cache_prefix,
                "graph_list_objects_rbcd_to_da_from_" + object_name,
                "Paths to DA from rbcd targets",
                self.dico_description_rbcd_to_da,
            )
            sub_grid = Grid("RBCD targets that have a path to DA from " + object_name)
            sub_grid_data = []

            for destination in self.rbcd_graphs[object_name]["destinations"]:

                sub_tmp_data = {}
                sub_tmp_data["Name"] = destination
                if destination in list(self.rbcd_to_da_graphs.keys()):
                    self.rbcd_graphs[object_name]["nb_paths_to_da"] += len(
                        self.rbcd_to_da_graphs[destination]["paths"]
                    )
                    sortClass = str(
                        len(self.rbcd_to_da_graphs[destination]["paths"])
                    ).zfill(6)
                    sub_tmp_data["Paths to DA"] = grid_data_stringify(
                        {
                            "value": f'{len(self.rbcd_to_da_graphs[destination]["paths"])} path{"s" if len(self.rbcd_to_da_graphs[destination]["paths"]) > 1 else ""} to DA <i class="bi bi-gem"></i>',
                            "link": "rbcd_target_%s_paths_to_da.html" % quote(str(destination)),
                            "before_link": f'<i class="bi bi-sign-turn-right {sortClass}" style="color:#b00404;""></i>',
                        }
                    )
                else:
                    sub_tmp_data["Paths to DA"] = "-"
                sub_grid_data.append(sub_tmp_data)
            sub_headers = ["Name", "Paths to DA"]
            sub_grid.setheaders(sub_headers)
            sub_grid.setData(sub_grid_data)
            sub_page.addComponent(sub_grid)
            sub_page.render()

        page = Page(
            self.arguments.cache_prefix,
            "graph_list_objects_rbcd",
            "Kerberos RBCD against computers",
            self.get_dico_description(),
        )
        grid = Grid("Objects that can perform an RBCD attack on computers")
        headers = ["Domain", "Name", "Paths to targets", "Paths to DA"]
        grid.setheaders(headers)
        grid_data = []

        if len(list(self.rbcd_graphs.keys())) != 0:
            for object_name in list(self.rbcd_graphs.keys()):
                tmp_data = {}
                tmp_data["Domain"] = (
                    '<i class="bi bi-globe2"></i>'
                    + self.rbcd_graphs[object_name]["domain"]
                )
                tmp_data["Name"] = '<i class="bi bi-person-fill"></i>' + object_name
                sortClass1 = str(len(self.rbcd_graphs[object_name]["paths"])).zfill(6)
                tmp_data["Paths to targets"] = grid_data_stringify(
                    {
                        "value": f'{len(self.rbcd_graphs[object_name]["paths"])} path{"s" if len(self.rbcd_graphs[object_name]["paths"]) > 1 else ""} to targets <i class="bi bi-bullseye"></i>',
                        "link": "%s_rbcd_graph.html" % quote(str(object_name)),
                        "before_link": f'<i class="bi bi-sign-turn-right {sortClass1}"></i>',
                    }
                )
                if self.rbcd_graphs[object_name]["nb_paths_to_da"] > 0:
                    sortClass2 = str(
                        self.rbcd_graphs[object_name]["nb_paths_to_da"]
                    ).zfill(6)
                    tmp_data["Paths to DA"] = grid_data_stringify(
                        {
                            "value": f'{self.rbcd_graphs[object_name]["nb_paths_to_da"]} path{"s" if self.rbcd_graphs[object_name]["nb_paths_to_da"] > 1 else ""} to DA <i class="bi bi-gem"></i>',
                            "link": "graph_list_objects_rbcd_to_da_from_%s.html"
                            % quote(str(object_name)),
                            "before_link": f'<i class="bi bi-sign-turn-right-fill {sortClass2}" style="color:#b00404;"></i>',
                        }
                    )
                else:
                    tmp_data["Paths to DA"] = "-"
                grid_data.append(tmp_data)
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = len(list(self.rbcd_graphs.keys())) if self.rbcd_graphs else 0

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.rbcd_nb_start_nodes} users can perform an RBCD attack on {self.rbcd_nb_end_nodes} computers"

    def get_rating(self) -> int:
        return min(
            presence_of(list(self.rbcd_graphs.keys()), criticity=2),
            presence_of(list(self.rbcd_to_da_graphs.keys()), criticity=1),
        )
