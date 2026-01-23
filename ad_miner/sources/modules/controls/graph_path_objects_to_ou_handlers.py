from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.path_neo4j import Path
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import (
    presence_of,
    createGraphPage,
    get_interest,
)

from urllib.parse import quote
from tqdm import tqdm


@register_control
class graph_path_objects_to_ou_handlers(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "graph_path_objects_to_ou_handlers"

        self.title = "Paths to Organizational Units (OU)"
        self.description = "Objects that have paths to compromise OU handlers."
        self.risk = "OUs that can be used to leverage access to privileged accounts or objects are particularly sensitive."
        self.poa = (
            "Review the exploitation paths for these OUs and remove dangerous links."
        )

        self.subpage_dico_description_paths_to_ou_handlers = {
            "description": "Graph of paths leading to OU handlers",
            "risk": "Compromission paths to OU handlers represent the exposed attack surface that the AD environment presents to the attacker in order to gain corresponding privileges.",
            "poa": "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface.",
        }

        self.compromise_paths_of_OUs = requests_results["compromise_paths_of_OUs"]
        self.vulnerable_OU_impact = requests_results["vulnerable_OU_impact"]
        self.contains_da = requests_results["set_containsda"]
        self.contains_dc = requests_results["set_containsdc"]

    def run(self):
        if self.compromise_paths_of_OUs is None:
            return
        OU_to_targets_dico = {}
        all_compromise_paths = []

        for p in self.contains_da:
            if p.nodes[0].id not in OU_to_targets_dico:
                OU_to_targets_dico[p.nodes[0].id] = [p]
            else:
                OU_to_targets_dico[p.nodes[0].id].append(p)
        for p in self.contains_dc:
            if p.nodes[0].id not in OU_to_targets_dico:
                OU_to_targets_dico[p.nodes[0].id] = [p]
            else:
                OU_to_targets_dico[p.nodes[0].id].append(p)
        for p in self.vulnerable_OU_impact:
            if p.nodes[0].id not in OU_to_targets_dico:
                OU_to_targets_dico[p.nodes[0].id] = [p]
            else:
                OU_to_targets_dico[p.nodes[0].id].append(p)

        for p1 in self.compromise_paths_of_OUs:
            if p1.nodes[-1].id not in OU_to_targets_dico:
                continue
            for p2 in OU_to_targets_dico[p1.nodes[-1].id]:
                assert p1.nodes[-1].id == p2.nodes[0].id
                p = Path(p1.nodes[:-1] + p2.nodes)
                all_compromise_paths.append(p)

        # Compute users and computers admin of computers to compute targets interest
        # should be moved to a common cache (with GPO control, ACL anomaly, etc)

        page = Page(
            self.arguments.cache_prefix,
            "graph_path_objects_to_ou_handlers",
            "Paths to Organizational Units (OU)",
            self.get_dico_description(),
        )

        analysis_dict = {}

        for p in tqdm(all_compromise_paths):
            for i in range(len(p.nodes)):
                if p.nodes[i].labels == "OU":
                    OU_node = p.nodes[i]
                    inbound_path = Path(p.nodes[: i + 1])
                    outbount_path = Path(p.nodes[i:])
                    break
            if OU_node not in analysis_dict:
                analysis_dict[OU_node] = {"inbound_paths": [], "outbound_paths": []}

            # if inbound_path not in analysis_dict[OU_node]["inbound_paths"]:
            analysis_dict[OU_node]["inbound_paths"].append(inbound_path.nodes)
            # if outbount_path not in analysis_dict[OU_node]["outbound_paths"]:
            analysis_dict[OU_node]["outbound_paths"].append(outbount_path.nodes)

        for OU_node in analysis_dict:
            analysis_dict[OU_node]["inbound_paths"] = [
                Path(list(x))
                for x in {(tuple(e)) for e in analysis_dict[OU_node]["inbound_paths"]}
            ]
            analysis_dict[OU_node]["outbound_paths"] = [
                Path(list(x))
                for x in {(tuple(e)) for e in analysis_dict[OU_node]["outbound_paths"]}
            ]

        grid = Grid("TODO")
        headers = [
            "OU name",
            "Inbound graph",
            "Inbound list",
            "Targets interest",
            "Outbound list",
            "Outbound graph",
        ]
        grid.setheaders(headers)
        grid_data = []

        self.maxInterest = 0

        for OU_node in analysis_dict:

            inbound_list = [
                p.nodes[0].name for p in analysis_dict[OU_node]["inbound_paths"]
            ]
            inbound_list = list(dict.fromkeys(inbound_list))

            outbound_list = [
                p.nodes[-1].name for p in analysis_dict[OU_node]["outbound_paths"]
            ]
            outbound_list = list(dict.fromkeys(outbound_list))

            # Generate page with inbound list
            inbound_list_page = Page(
                self.arguments.cache_prefix,
                "path_objects_to_ou_handlers_inbound_list_" + OU_node.name,
                "Objects that can get control over " + OU_node.name,
                self.get_dico_description(),
            )
            inbound_grid = Grid("Objects that can get control over " + OU_node.name)
            inbound_grid.setheaders(
                ["Objects that can get control over " + OU_node.name]
            )
            inbound_grid_data = []

            for name in inbound_list:
                inbound_grid_data.append(
                    {"Objects that can get control over " + OU_node.name: name}
                )
            inbound_grid.setData(inbound_grid_data)
            inbound_list_page.addComponent(inbound_grid)
            inbound_list_page.render()

            # Generate page with outbound list
            outbound_list_page = Page(
                self.arguments.cache_prefix,
                "path_objects_to_ou_handlers_outbound_list_" + OU_node.name,
                "Objects that can get control over " + OU_node.name,
                self.get_dico_description(),
            )
            outbound_grid = Grid("Objects controlled by " + OU_node.name)
            outbound_grid.setheaders(["Objects controlled by " + OU_node.name])
            outbound_grid_data = []

            for name in outbound_list:
                outbound_grid_data.append(
                    {"Objects controlled by " + OU_node.name: name}
                )
            outbound_grid.setData(outbound_grid_data)
            outbound_list_page.addComponent(outbound_grid)
            outbound_list_page.render()

            # Generate inbound graph page
            createGraphPage(
                self.arguments.cache_prefix,
                "paths_to_OU_" + OU_node.name,
                "Paths to OU handlers",
                self.get_dico_description(),
                analysis_dict[OU_node]["inbound_paths"],
                self.requests_results,
            )

            # Generate outbound graph page
            createGraphPage(
                self.arguments.cache_prefix,
                "paths_from_OU_" + OU_node.name,
                "Paths from OU handlers",
                self.get_dico_description(),
                analysis_dict[OU_node]["outbound_paths"],
                self.requests_results,
            )

            tmp_data = {}
            tmp_data["OU name"] = OU_node.name

            inbound_objects_count = len(inbound_list)
            tmp_data["Inbound list"] = grid_data_stringify(
                {
                    "value": f"{inbound_objects_count} object{'s' if inbound_objects_count > 1 else ''}",
                    "link": "path_objects_to_ou_handlers_inbound_list_"
                    + str(quote(OU_node.name))
                    + ".html",
                    "before_link": '<i class="bi bi-list-columns-reverse" aria-hidden="true"></i>',
                }
            )
            outbound_objects_count = len(outbound_list)
            tmp_data["Outbound list"] = grid_data_stringify(
                {
                    "value": f"{outbound_objects_count} object{'s' if outbound_objects_count > 1 else ''}",
                    "link": "path_objects_to_ou_handlers_outbound_list_"
                    + str(quote(OU_node.name))
                    + ".html",
                    "before_link": '<i class="bi bi-list-columns-reverse" aria-hidden="true"></i>',
                }
            )
            inbound_paths_count = len(analysis_dict[OU_node]["inbound_paths"])
            tmp_data["Inbound graph"] = grid_data_stringify(
                {
                    "value": f"{inbound_paths_count} path{'s' if inbound_paths_count > 1 else ''}",
                    "link": "paths_to_OU_" + str(quote(OU_node.name)) + ".html",
                    "before_link": '<i class="bi bi-diagram-3-fill" aria-hidden="true"></i>',
                }
            )
            outbound_paths_count = len(analysis_dict[OU_node]["outbound_paths"])
            tmp_data["Outbound graph"] = grid_data_stringify(
                {
                    "value": f"{outbound_paths_count} path{'s' if outbound_paths_count > 1 else ''}",
                    "link": "paths_from_OU_" + str(quote(OU_node.name)) + ".html",
                    "before_link": '<i class="bi bi-diagram-3-fill" aria-hidden="true"></i>',
                }
            )

            # Rate the interest of the OU

            # 0 star  : no object impacted or other objects
            # 1 star  : at least one object is admin of computer
            # 2 stars : at least one object has path to DA
            # 3 stars : full domain or at least one domain admin impacted
            paths = analysis_dict[OU_node]["outbound_paths"]

            if len(paths) == 0:
                interest = 0
            else:
                interest = 0
                for path in paths:
                    for node in path.nodes:
                        interest = max(
                            get_interest(
                                self.requests_results,
                                node.labels,
                                node.name,
                            ),
                            interest,
                        )

            self.maxInterest = max(interest, self.maxInterest)

            # Color for stars
            if interest == 3:
                color = "red"
            elif interest == 2:
                color = "orange"
            else:
                color = "green"

            icon = (
                f"<span class='{interest}'></span><i class='bi bi-star-fill' style='color: {color}'></i>"
                * interest
                + f"<i class='bi bi-star' style='color: {color}'></i>" * (3 - interest)
            )

            tmp_data["Targets interest"] = icon

            grid_data.append(tmp_data)

        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = len(analysis_dict.keys())

        self.name_description = f"{self.data} dangerous control paths over OUs"

    def get_rating(self) -> int:
        if self.data == 0:
            return 5
        elif self.maxInterest >= 2:
            return 1
        else:
            return 3
