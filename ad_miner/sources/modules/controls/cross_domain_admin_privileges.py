from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import createGraphPage

import copy


@register_control
class cross_domain_admin_privileges(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "cross_domain_admin_privileges"

        self.title = "Users that have powerful cross-domain privileges"
        self.description = "Users privileges are not limited to their domains. Sometimes some users may have direct or non-direct local admin or even domain admin privilege on a foreign domain."
        self.risk = "Cross-domain privileges are quite dangerous and will help attackers to pivot to other domains if they manage to compromise a domain"
        self.poa = "Review these privileges, this list should be as little as possible."

        self.cross_domain_local_admins_paths = requests_results[
            "cross_domain_local_admins"
        ]
        self.cross_domain_domain_admins_paths = requests_results[
            "cross_domain_domain_admins"
        ]

    def run(self):
        # get the result of the cypher request (a list of Path objects)
        paths_local_admins = self.cross_domain_local_admins_paths

        paths_domain_admins = self.cross_domain_domain_admins_paths
        # create the page
        page = Page(
            self.arguments.cache_prefix,
            "cross_domain_admin_privileges",
            "Cross-Domain admin privileges",
            self.get_dico_description(),
        )
        # create the grid
        grid = Grid("Cross-Domain admin privileges")
        # create the headers (domains)
        headers = [
            "user",
            "crossLocalAdminAsGraph",
            "crossLocalAdminAsList",
            "crossDomainAdminAsGraph",
            "crossDomainAdminAsList",
        ]

        data_local_admins = {}
        for path in paths_local_admins:
            user = path.nodes[0].name
            target_domain = path.nodes[-1].domain
            if user in data_local_admins.keys():
                # data_local_admins[user].append(path)
                if target_domain in data_local_admins[user]:
                    data_local_admins[user][target_domain].append(path)
                else:
                    data_local_admins[user][target_domain] = [path]
            else:
                data_local_admins[user] = {target_domain: [path]}

        data = {}

        data_domain_admins = {}
        for path in paths_domain_admins:
            user = path.nodes[0].name
            target_domain = path.nodes[-1].domain
            if user in data_domain_admins.keys():
                # data_domain_admins[user].append(path)
                if target_domain in data_domain_admins[user]:
                    data_domain_admins[user][target_domain].append(path)
                else:
                    data_domain_admins[user][target_domain] = [path]
            else:
                data_domain_admins[user] = {target_domain: [path]}

        user_keys_raw = list(data_local_admins.keys()) + list(data_domain_admins.keys())
        unique_users_keys = set(user_keys_raw)

        grid_data = []

        self.cross_domain_total_admin_accounts = len(list(unique_users_keys))
        self.cross_domain_local_admin_accounts = len(list(data_local_admins))
        self.cross_domain_domain_admin_accounts = len(list(data_domain_admins))

        for key in unique_users_keys:
            user = key
            tmp_data = {}

            tmp_data["user"] = '<i class="bi bi-person-fill"></i>' + user
            grid_list_local_admin_targets_data = []
            grid_list_domain_admin_targets_data = []
            # create the grid
            grid_list_local_admin_targets = Grid(
                "List of computers from a foreign domain where "
                + user
                + " happens to be a local admin"
            )
            grid_list_domain_admin_targets = Grid(
                "List of foreign domains where "
                + user
                + " happens to be a domain admin"
            )
            if key in data_local_admins.keys():
                local_targets = []
                local_distinct_ends = []
                for domain in data_local_admins[key]:
                    list_local_admin_targets_tmp_data = {
                        "domain": '<i class="bi bi-globe2"></i>' + domain
                    }
                    numberofpaths = 0
                    for path in data_local_admins[key][domain]:
                        list_local_admin_targets_tmp_data_copy = copy.deepcopy(
                            list_local_admin_targets_tmp_data
                        )
                        last_node_name = path.nodes[-1].name
                        local_targets.append(path)
                        if last_node_name not in local_distinct_ends:
                            local_distinct_ends.append(last_node_name)
                            sortClass = last_node_name.zfill(6)
                            list_local_admin_targets_tmp_data_copy["target"] = grid_data_stringify(
                                {
                                    "value": f"{last_node_name}",
                                    "link": "%s_paths_cross_domain_local_admin.html" % user,
                                    "before_link": f'<i class="bi bi-sign-turn-right {sortClass}"></i>',
                                }
                            )

                            grid_list_local_admin_targets_data.append(
                                list_local_admin_targets_tmp_data_copy
                            )
                    nb_local_distinct_ends = len(local_distinct_ends)
                sortClass = str(nb_local_distinct_ends).zfill(6)
                tmp_data["crossLocalAdminAsGraph"] = grid_data_stringify(
                    {
                        "value": f"{nb_local_distinct_ends} computers impacted",
                        "link": "%s_paths_cross_domain_local_admin.html" % user,
                        "before_link": f'<i class="bi bi-sign-turn-right {sortClass}"></i>',
                    }
                )
                createGraphPage(
                    self.arguments.cache_prefix,
                    user + "_paths_cross_domain_local_admin",
                    "Paths from "
                    + user
                    + " to machines of privileged groups from other domains making them domainadmin",
                    self.get_dico_description(),
                    local_targets,
                    self.requests_results,
                )

                page_list_local_admin_targets = Page(
                    self.arguments.cache_prefix,
                    "cross_domain_local_admins_targets_from_" + user,
                    "List of computers from a foreign domain where "
                    + user
                    + " happens to be a local admin",
                    self.get_dico_description(),
                )
                # create the headers (domains)
                local_admins_list_page_headers = ["domain", "target"]
                grid_list_local_admin_targets.setheaders(local_admins_list_page_headers)
                grid_list_local_admin_targets.setData(
                    grid_list_local_admin_targets_data
                )
                page_list_local_admin_targets.addComponent(
                    grid_list_local_admin_targets
                )
                page_list_local_admin_targets.render()
                tmp_data["crossLocalAdminAsList"] = grid_data_stringify(
                    {
                        "value": "<i class='bi bi-list-columns-reverse'></i></span>",
                        "link": "cross_domain_local_admins_targets_from_%s.html" % user,
                    }
                )

            else:
                tmp_data["crossLocalAdminAsGraph"] = "-"
                tmp_data["crossLocalAdminAsList"] = "-"

            if key in data_domain_admins.keys():
                domain_targets = []
                domain_distinct_ends = []
                for domain in data_domain_admins[key]:
                    list_domain_admin_targets_tmp_data = {
                        "domain": '<i class="bi bi-globe2"></i>' + domain
                    }

                    for path in data_domain_admins[key][domain]:
                        list_domain_admin_targets_tmp_data_copy = copy.deepcopy(
                            list_domain_admin_targets_tmp_data
                        )
                        last_node_name = path.nodes[-1].name
                        domain_targets.append(path)
                        if last_node_name not in domain_distinct_ends:

                            domain_distinct_ends.append(last_node_name)

                            sortClass = last_node_name.zfill(6)
                            list_domain_admin_targets_tmp_data_copy["target"] = grid_data_stringify(
                                {
                                    "value": f"{last_node_name}",
                                    "link": "%s_paths_cross_domain_domain_admin.html" % user,
                                    "before_link": f'<i class="bi bi-sign-turn-right-fill {sortClass}" style="color:#b00404;"></i>',
                                }
                            )

                            grid_list_domain_admin_targets_data.append(
                                list_domain_admin_targets_tmp_data_copy
                            )

                    nb_domain_distinct_ends = len(domain_distinct_ends)
                sortClass = str(len(list(data_domain_admins[key].keys()))).zfill(6)
                tmp_data["crossDomainAdminAsGraph"] = grid_data_stringify(
                    {
                        "value": f"{len(list(data_domain_admins[key].keys()))} domains impacted",
                        "link": "%s_paths_cross_domain_domain_admin.html" % user,
                        "before_link": f'<i class="bi bi-sign-turn-right-fill {sortClass}" style="color:#b00404;"></i>',
                    }
                )
                createGraphPage(
                    self.arguments.cache_prefix,
                    user + "_paths_cross_domain_domain_admin",
                    "Paths from "
                    + user
                    + " to privileged groups from other domains making him/her domain admin",
                    self.get_dico_description(),
                    domain_targets,
                    self.requests_results,
                )

                page_list_domain_admin_targets = Page(
                    self.arguments.cache_prefix,
                    "cross_domain_domain_admins_targets_from_" + user,
                    "List of other domains where "
                    + user
                    + " happens to be a domain admin",
                    self.get_dico_description(),
                )
                # create the headers (domains)
                domain_admins_list_page_headers = ["domain", "target"]
                grid_list_domain_admin_targets.setheaders(
                    domain_admins_list_page_headers
                )
                grid_list_domain_admin_targets.setData(
                    grid_list_domain_admin_targets_data
                )
                page_list_domain_admin_targets.addComponent(
                    grid_list_domain_admin_targets
                )
                page_list_domain_admin_targets.render()
                tmp_data["crossDomainAdminAsList"] = grid_data_stringify(
                    {
                        "value": "<i class='bi bi-list-columns-reverse'></i></span>",
                        "link": "cross_domain_domain_admins_targets_from_%s.html"
                        % user,
                    }
                )

            else:
                tmp_data["crossDomainAdminAsGraph"] = "-"
                tmp_data["crossDomainAdminAsList"] = "-"
            grid_data.append(tmp_data)

        grid.setheaders(headers)
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = self.cross_domain_total_admin_accounts
        self.name_description = (
            f"{self.data} accounts have cross-domain admin privileges"
        )

    def get_rating(self) -> int:
        if self.cross_domain_domain_admin_accounts > 0:
            return 1
        elif self.cross_domain_local_admin_accounts > 0:
            return 2
        else:
            return 5
