from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules import logger
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules import generic_computing
from ad_miner.sources.modules.common_analysis import (
    presence_of,
)
from os.path import sep
from tqdm import tqdm
from urllib.parse import quote
import json


@register_control
class users_GPO_access(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)
        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "users_GPO_access"

        self.title = "Inadequate GPO modifications privileges"
        self.description = "GPOs that can be edited by unprivileged users."
        self.risk = "If an AD object has rights over a GPO, it can potentially cause damage over all the objects affected by the GPO. GPOs can also be leveraged to gain privileges in the domain(s). If an attacker exploits one of these paths, they will be able to gain privileges in the domain(s) and cause some serious damage.<br/><br/><i class='bi bi-star-fill' style='color: red'></i><i class='bi bi-star-fill' style='color: red'></i><i class='bi bi-star-fill' style='color: red'></i>: Full domain or at least one domain admin as target.<br /><i class='bi bi-star-fill' style='color: orange'></i><i class='bi bi-star-fill' style='color: orange'></i><i class='bi bi-star' style='color: orange'></i>: At least one object admin of a computer.<br/><i class='bi bi-star-fill' style='color: green'></i><i class='bi bi-star' style='color: green'></i><i class='bi bi-star' style='color: green'></i>: At least one object as target.<br/><i class='bi bi-star' style='color: green'></i><i class='bi bi-star' style='color: green'></i><i class='bi bi-star' style='color: green'></i>: No direct target."
        self.poa = "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface."

        self.description_grid_GPO_access = {
            "description": "Grid of paths for GPO exploit",
            "interpretation": "",
            "risk": "If an AD object has rights over a GPO, it can potentially cause damage over all the objects affected by the GPO. GPOs can also be leveraged to gain privileges in the domain(s). If an attacker exploits one of these paths, they will be able to gain privileges in the domain(s) and cause some serious damage.",
            "poa": "Review the objects in this list by making sure they are not wrongfully allowed to edit this GPO.",
        }

        self.description_graph_GPO_access = {
            "description": "Graph of paths for GPO exploit",
            "interpretation": "",
            "risk": "If an AD object has rights over a GPO, it can potentially cause damage over all the objects affected by the GPO. GPOs can also be leveraged to gain privileges in the domain(s). If an attacker exploits one of these paths, they will be able to gain privileges in the domain(s) and cause some serious damage.",
            "poa": "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface.",
        }

        self.users_admin_computer = requests_results["users_admin_on_computers"]
        self.users_admin_computer_list = generic_computing.getListAdminTo(
            self.users_admin_computer, "user", "computer"
        )

        self.admin_list = requests_results["admin_list"]

        self.number_of_gpo = 0

        if not arguments.gpo_low:
            self.unpriv_users_to_GPO_init = self.requests_results[
                "unpriv_users_to_GPO_init"
            ]
            self.unpriv_users_to_GPO_user_enforced = self.requests_results[
                "unpriv_users_to_GPO_user_enforced"
            ]
            self.unpriv_users_to_GPO_computer_enforced = self.requests_results[
                "unpriv_users_to_GPO_computer_not_enforced"
            ]
            self.unpriv_users_to_GPO_user_not_enforced = self.requests_results[
                "unpriv_users_to_GPO_user_not_enforced"
            ]
            self.unpriv_users_to_GPO_computer_not_enforced = self.requests_results[
                "unpriv_users_to_GPO_computer_not_enforced"
            ]

        else:
            self.unpriv_users_to_GPO = self.requests_results["unpriv_users_to_GPO"]

    def run(self):
        if self.arguments.gpo_low and self.unpriv_users_to_GPO is None:
            self.data = -1
            self.name_description = ""

        if not self.arguments.gpo_low:
            fail = []
            if self.unpriv_users_to_GPO_init is None:
                fail.append("unpriv_users_to_GPO_init")
            elif self.unpriv_users_to_GPO_user_enforced is None:
                fail.append("unpriv_users_to_GPO_user_enforced")
            elif self.unpriv_users_to_GPO_user_not_enforced is None:
                fail.append("unpriv_users_to_GPO_user_not_enforced")
            elif self.unpriv_users_to_GPO_computer_enforced is None:
                fail.append("unpriv_users_to_GPO_computer_enforced")
            elif self.unpriv_users_to_GPO_computer_not_enforced is None:
                fail.append("unpriv_users_to_GPO_computer_not_enforced")

            if 0 < len(fail) < 5:  # if only some of them are disabled
                logger.print_error(
                    f" In order to use 'normal GPO mode', please activate the following in config.json : {', '.join(fail)}"
                )

            if len(fail) > 0:
                self.data = -1
                self.name_description = ""
                return

        def parseGPOData(listOfPaths, headers):
            """
            Initial parsing of data from neo4j requests for GPO
            """
            dictOfGPO = {}
            for path in listOfPaths:
                start = path.nodes[0]
                end = path.nodes[-1]
                if "GPO" in start.labels:
                    nameOfGPO = start.name
                    idOfGPO = start.id
                    sens = "right"
                elif "GPO" in end.labels:
                    nameOfGPO = end.name
                    idOfGPO = end.id
                    sens = "left"
                else:
                    continue
                try:
                    if sens == "right":
                        dictOfGPO[nameOfGPO][headers[4]] += 1
                        dictOfGPO[nameOfGPO]["right_path"].append(path)
                        dictOfGPO[nameOfGPO]["end_list"].append((end.name, end.labels))
                    elif sens == "left":
                        dictOfGPO[nameOfGPO][headers[1]] += 1
                        dictOfGPO[nameOfGPO]["left_path"].append(path)
                        dictOfGPO[nameOfGPO]["entry_list"].append(
                            (start.name, start.labels)
                        )
                    else:
                        continue
                except KeyError:
                    if sens == "right":
                        dictOfGPO[nameOfGPO] = {
                            headers[0]: nameOfGPO,
                            headers[1]: 0,
                            headers[4]: 1,
                            "left_path": [],
                            "right_path": [path],
                            "id": idOfGPO,
                            "entry_list": [],
                            "end_list": [(end.name, end.labels)],
                        }
                    elif sens == "left":
                        dictOfGPO[nameOfGPO] = {
                            headers[0]: nameOfGPO,
                            headers[1]: 1,
                            headers[4]: 0,
                            "left_path": [path],
                            "right_path": [],
                            "id": idOfGPO,
                            "entry_list": [(start.name, start.labels)],
                            "end_list": [],
                        }
                    else:
                        continue
            return dictOfGPO

        def formatGPOGrid(dictOfGPO, headers):
            output = []

            # Extract all computers admin of computers
            self.computers_with_admin_rights = list(
                self.users_admin_computer_list.keys()
            )
            # self.computers_with_admin_rights = [
            #     d["Computer Admin"].split("</i>")[-1]
            #     for d in self.computers_admin_data_grid
            # ]
            # Extract all users admin of computers
            self.users_with_admin_rights = [
                d["user"] for d in self.users_admin_computer
            ]

            for _, dict in tqdm(dictOfGPO.items()):
                self.number_of_gpo += 1
                # Rate the interest of the GPO
                # 0 star  : no object impacted
                # 1 star  : at least one object impacted
                # 2 stars : at least one admin account impacted
                # 3 stars : full domain or at least one domain admin impacted
                paths = dict["right_path"]

                if len(paths) == 0:
                    interest = 0
                else:
                    interest = 1

                for path in paths:
                    for i in range(len(path.nodes)):
                        if path.nodes[i].labels == "Domain":
                            interest = 3
                            break
                        if path.nodes[i].name in self.admin_list:
                            interest = 3
                            break
                        if (
                            path.nodes[i].name in self.users_with_admin_rights
                            or path.nodes[i].name in self.computers_with_admin_rights
                        ):
                            interest = max(2, interest)

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
                    + f"<i class='bi bi-star' style='color: {color}'></i>"
                    * (3 - interest)
                )

                output.append(
                    {
                        headers[0]: '<i class="bi bi-journal-text"></i>' + dict[headers[0]],
                        headers[
                            1
                        ]: f'<i class="bi bi-sign-turn-right {str(dict[headers[1]]).zfill(6)}"></i>'
                        + str(dict[headers[1]]),
                        headers[2]: {
                            "link": "users_GPO_access-%s-left-graph.html"
                            % (quote(str(dict[headers[0]]).replace(sep, "_"))),
                            "value": "<i class='bi bi-diagram-3-fill' aria-hidden='true'></i>",
                        },
                        headers[3]: {
                            "link": "users_GPO_access-%s-left-grid.html"
                            % (quote(str(dict[headers[0]]).replace(sep, "_"))),
                            "value": "<i class='bi bi-list-columns-reverse' aria-hidden='true'></i>",
                        },
                        headers[
                            4
                        ]: f'<i class="bi bi-bullseye {str(len(list(set(dict["end_list"])))).zfill(6)}"></i>'
                        + str(len(list(set(dict["end_list"])))),
                        headers[5]: icon,
                        headers[6]: {
                            "link": "users_GPO_access-%s-right-graph.html"
                            % (quote(str(dict[headers[0]]).replace(sep, "_"))),
                            "value": "<i class='bi bi-diagram-3-fill' aria-hidden='true'></i>",
                        },
                        headers[7]: {
                            "link": "users_GPO_access-%s-right-grid.html"
                            % (quote(str(dict[headers[0]]).replace(sep, "_"))),
                            "value": "<i class='bi bi-list-columns-reverse' aria-hidden='true'></i>",
                        },
                    }
                )
            return output

        def formatSmallGrid(list, gpo_name):
            output = []
            for n in list:
                if n[1] == "Computer":
                    icon = '<i class="bi bi-pc-display"></i>'
                elif n[1] == "User":
                    icon = '<i class="bi bi-person-fill"></i>'
                elif n[1] == "Domain":
                    icon = '<i class="bi bi-house-fill"></i>'
                else:
                    icon = '<i class="bi bi-question-circle-fill"></i>'

                if (
                    n[0] in self.computers_with_admin_rights
                    or n[0] in self.users_with_admin_rights
                ):
                    icon = (
                        icon
                        + '<i class="bi bi-gem" title="This object has administration rights" style="color:grey;"></i>'
                    )
                if n[0] in self.admin_list:
                    icon = '<i class="bi bi-gem" title="This user is domain admin" style="color:deepskyblue;"></i>'

                output.append({gpo_name: icon + n[0]})
            return output

        headers = [
            "GPO name",
            "Paths to GPO",
            "Inbound graph",
            "Inbound list",
            "Objects impacted",
            "Targets interest",
            "Outbound graph",
            "Outbound list",
        ]
        if not self.arguments.gpo_low:
            data = (
                self.unpriv_users_to_GPO_init
                + self.unpriv_users_to_GPO_user_enforced
                + self.unpriv_users_to_GPO_computer_enforced
                + self.unpriv_users_to_GPO_user_not_enforced
                + self.unpriv_users_to_GPO_computer_not_enforced
            )
            self.unpriv_users_to_GPO_parsed = parseGPOData(data, headers)
            grid = Grid("Users with GPO access")
        else:
            self.domain.unpriv_users_to_GPO_parsed = parseGPOData(
                self.domain.unpriv_users_to_GPO, headers
            )
            grid = Grid("Users with GPO access")

        formated_data = sorted(
            formatGPOGrid(self.unpriv_users_to_GPO_parsed, headers),
            key=lambda x: x[headers[1]],
            reverse=True,
        )
        page = Page(
            self.arguments.cache_prefix,
            "users_GPO_access",
            "Exploitation through GPO",
            self.get_dico_description(),
        )

        grid.setheaders(headers)
        grid.setData(json.dumps(formated_data))
        page.addComponent(grid)
        page.render()

        for _, GPO in self.unpriv_users_to_GPO_parsed.items():
            url_left_graph = "users_GPO_access-%s-left-graph" % GPO[headers[0]]
            url_right_graph = "users_GPO_access-%s-right-graph" % GPO[headers[0]]
            page_left_graph = Page(
                self.arguments.cache_prefix,
                url_left_graph,
                "Users with write access on GPO",
                self.description_graph_GPO_access,
            )
            page_right_graph = Page(
                self.arguments.cache_prefix,
                url_right_graph,
                "Objects impacted by GPO",
                self.description_graph_GPO_access,
            )

            url_left_grid = "users_GPO_access-%s-left-grid" % GPO[headers[0]]
            url_right_grid = "users_GPO_access-%s-right-grid" % GPO[headers[0]]
            page_left_grid = Page(
                self.arguments.cache_prefix,
                url_left_grid,
                "List of users able to compromise %s" % GPO[headers[0]],
                self.description_grid_GPO_access,
            )
            page_right_grid = Page(
                self.arguments.cache_prefix,
                url_right_grid,
                "List of users impacted by %s" % GPO[headers[0]],
                self.description_grid_GPO_access,
            )

            # if GPO[headers[4]] > 0:
            graph_left = Graph()
            graph_left.setPaths(GPO["left_path"])
            page_left_graph.addComponent(graph_left)

            graph_right = Graph()
            graph_right.setPaths(GPO["right_path"])
            page_right_graph.addComponent(graph_right)

            if not self.arguments.gpo_low:
                entry_grid = Grid(
                    "List of users able to compromise %s" % GPO[headers[0]]
                )
            else:
                entry_grid = Grid(
                    "List of users able to compromise %s" % GPO[headers[0]]
                )
            entry_grid.setheaders([GPO[headers[0]]])
            entry_grid.setData(
                json.dumps(
                    formatSmallGrid(list(set(GPO["entry_list"])), GPO[headers[0]])
                )
            )
            page_left_grid.addComponent(entry_grid)

            end_grid = Grid("List of users impacted by %s" % GPO[headers[0]])
            end_grid.setheaders([GPO[headers[0]]])
            end_grid.setData(
                json.dumps(formatSmallGrid(list(set(GPO["end_list"])), GPO[headers[0]]))
            )
            page_right_grid.addComponent(end_grid)

            page_left_graph.render()
            page_right_graph.render()
            page_left_grid.render()
            page_right_grid.render()

        self.data = self.number_of_gpo if self.number_of_gpo else 0

        self.name_description = (
            f"{self.data} GPO with inadequate modification privileges"
        )

    def get_rating(self) -> int:
        return presence_of(self.unpriv_users_to_GPO_parsed.items())
