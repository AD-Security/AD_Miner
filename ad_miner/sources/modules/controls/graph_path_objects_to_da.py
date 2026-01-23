from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules import logger
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of, createGraphPage

from urllib.parse import quote


@register_control
class graph_path_objects_to_da(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "graph_path_objects_to_da"

        self.title = "Paths to Domain Admins"
        self.description = "Compromission paths from some Active Directory object to domain admin privileges."
        self.risk = "Compromission paths to domain admin represent the exposed attack surface that the AD environment presents to the attacker in order to gain privileges in the domain(s). If an attacker exploits one of these paths, they will be able to gain privileges in the domain(s) and cause some serious damage."
        self.poa = "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface."

        self.objects_to_domain_admin = requests_results["objects_to_domain_admin"]

        self.objects_to_domain = self.requests_results["objects_to_domain_admin"]
        self.users_to_domain = self.requests_results["users_to_domain_admin"]
        self.groups_to_domain = self.requests_results["groups_to_domain_admin"]
        self.computers_to_domain = self.requests_results["computers_to_domain_admin"]
        self.domains_to_domain = self.requests_results["domains_to_domain_admin"]

        self.users_to_domain_admin = self.users_to_domain
        self.computers_to_domain_admin = self.computers_to_domain
        self.groups_to_domain_admin = self.groups_to_domain

        self.domains = requests_results["domains"]
        self.collected_domains = requests_results["nb_domain_collected"]

        self.dico_description_paths_to_domain_admin = {
            "description": "Paths leading to domain admin",
            "risk": "Compromission paths to domain admin represent the exposed attack surface that the AD environment presents to the attacker in order to gain privileges in the domain(s). If an attacker exploits one of these paths, they will be able to gain privileges in the domain(s) and cause some serious damage.",
            "poa": "Review the paths, make sure they are not exploitable. If they are, cut the link between the Active Directory objects in order to reduce the attack surface.",
        }

    def run(self):
        self.generatePathToDa()
        self.data = (
            len(
                list(
                    set(
                        p.nodes[0]
                        for p in [
                            item
                            for sublist in self.users_to_domain_admin.values()
                            for item in sublist
                        ]
                    )
                )
            )
            if self.users_to_domain_admin
            else 0
        )
        self.name_description = f"{len(list(set(p.nodes[0] for p in [item for sublist in self.users_to_domain_admin.values() for item in sublist]))) if self.users_to_domain_admin else 0} users have a path to DA"

    def get_rating(self) -> int:
        if (
            self.users_to_domain_admin is None
            or self.computers_to_domain_admin is None
            or self.groups_to_domain_admin is None
        ):
            return -1

        for domain in self.users_to_domain_admin:
            if len(self.users_to_domain_admin[domain]) > 0:
                return 1
        for domain in self.computers_to_domain_admin:
            if len(self.computers_to_domain_admin[domain]) > 0:
                return 2
        for domain in self.groups_to_domain_admin:
            if len(self.groups_to_domain_admin[domain]) > 0:
                return 3
        return 5

    def generatePathToDa(
        self, file_variable="da", file_variable2="admin"
    ):  # file_variable if we want to generate path to something other than domain admin groups
        if file_variable == "da":
            if self.objects_to_domain_admin is None:
                return

        for domain in self.domains:
            domain = domain[0]
            logger.print_debug(f"Generating paths to DA pages for {domain}")

            count_users = len(self.users_to_domain[domain])
            logger.print_debug(f"Trying to generate users to DA graph page with {count_users} paths")
            if count_users:
                createGraphPage(
                    self.arguments.cache_prefix,
                    domain + f"_users_to_{file_variable}",
                    f"Paths to domain {file_variable2}",
                    self.dico_description_paths_to_domain_admin,
                    self.users_to_domain[domain],
                    self.requests_results,
                )

            count_computers = len(self.computers_to_domain[domain])
            logger.print_debug(f"Trying to generate computers to DA graph page with {count_computers} paths")
            if count_computers:
                createGraphPage(
                    self.arguments.cache_prefix,
                    domain + f"_computers_to_{file_variable}",
                    f"Paths to domain {file_variable2}",
                    self.dico_description_paths_to_domain_admin,
                    self.computers_to_domain[domain],
                    self.requests_results,
                )

            count_groups = len(self.groups_to_domain[domain])
            logger.print_debug(f"Trying to generate groups to DA graph page with {count_groups} paths")
            if count_groups:
                createGraphPage(
                    self.arguments.cache_prefix,
                    domain + f"_groups_to_{file_variable}",
                    f"Paths to domain {file_variable2}",
                    self.dico_description_paths_to_domain_admin,
                    self.groups_to_domain[domain],
                    self.requests_results,
                )

        if len(self.domains_to_domain):
            createGraphPage(
                self.arguments.cache_prefix,
                f"domains_to_{file_variable}",
                f"Paths to domain {file_variable2}",
                self.dico_description_paths_to_domain_admin,
                self.domains_to_domain_admin,
                self.requests_results,
            )

        def count_object_from_path(list_of_paths):
            """
            Count the numbers of object leading to DA instead of counting number of path.
            """
            entries = {}
            for path in list_of_paths:
                start = path.nodes[0].name
                if start not in entries:
                    entries[start] = True
            return len(entries.keys())

        # generating graph object to da grid
        page = Page(
            self.arguments.cache_prefix,
            f"graph_path_objects_to_{file_variable}",
            "Paths to Domain Admins",
            self.get_dico_description(),
        )
        grid = Grid("Numbers of path to domain admin per domain and objects")
        grid_data = []
        headers = [
            "Domain",
            "Users (Paths)",
            "Computers (Paths)",
            "Groups (Paths)",
        ]
        self.total_object = 0

        for domain in self.collected_domains:
            domain = domain[0]
            tmp_data = {}

            tmp_data[headers[0]] = '<i class="bi bi-globe2"></i>' + domain

            count = count_object_from_path(self.users_to_domain[domain])
            sortClass = str(count).zfill(
                6
            )  # used to make the sorting feature work with icons
            if count != 0:
                tmp_data[headers[1]] = grid_data_stringify(
                    {
                        "value": f"{count} (<i class='bi bi-sign-turn-right-fill' style='color:#b00404;' aria-hidden='true'></i>{len(self.users_to_domain_admin[domain])})",
                        "link": "%s_users_to_da.html" % quote(str(domain)),
                        "before_link": f"<i class='bi bi-person-fill {sortClass}' aria-hidden='true'></i>",
                    }
                )
            else:
                tmp_data[headers[1]] = (
                    "<i class='bi bi-person-fill %s' aria-hidden='true'></i>%s (<i class='bi bi-sign-turn-right' aria-hidden='true'></i>%s)"
                    % (sortClass, count, len(self.users_to_domain_admin[domain]))
                )
            self.total_object += count

            count = count_object_from_path(self.computers_to_domain[domain])
            sortClass = str(count).zfill(
                6
            )  # used to make the sorting feature work with icons
            if count != 0:
                tmp_data[headers[2]] = grid_data_stringify(
                    {
                        "value": f"{count} (<i class='bi bi-sign-turn-right-fill' style='color:#b00404;' aria-hidden='true'></i>{len(self.computers_to_domain_admin[domain])})",
                        "link": "%s_computers_to_da.html" % quote(str(domain)),
                        "before_link": f"<i class='bi bi-pc-display-horizontal {sortClass}' aria-hidden='true'></i>",
                    }
                )
            else:
                tmp_data[headers[2]] = (
                    "<i class='bi bi-pc-display-horizontal %s' aria-hidden='true'></i>%s (<i class='bi bi-sign-turn-right' aria-hidden='true'></i>%s)"
                    % (sortClass, count, len(self.computers_to_domain_admin[domain]))
                )
            self.total_object += count

            count = count_object_from_path(self.groups_to_domain[domain])
            sortClass = str(count).zfill(
                6
            )  # used to make the sorting feature work with icons
            if count != 0:
                tmp_data[headers[3]] = grid_data_stringify(
                    {
                        "value": f"{count} (<i class='bi bi-sign-turn-right' aria-hidden='true'></i>{len(self.groups_to_domain_admin[domain])})",
                        "link": "%s_groups_to_da.html" % quote(str(domain)),
                        "before_link": f"<i class='bi bi-people-fill {sortClass}' aria-hidden='true'></i>",
                    }
                )
            else:
                tmp_data[headers[3]] = (
                    "<i class='bi bi-people-fill %s' aria-hidden='true'></i>%s (<i class='bi bi-sign-turn-right' aria-hidden='true'></i>%s)"
                    % (sortClass, count, len(self.groups_to_domain_admin[domain]))
                )
            self.total_object += count

            grid_data.append(tmp_data)
        grid.setheaders(headers)
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()
