from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules import generic_formating
from ad_miner.sources.modules.common_analysis import hasPathToDA

import json


@register_control
class server_users_could_be_admin(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "server_users_could_be_admin"

        self.title = "Paths to servers"
        self.description = (
            "Users could gain administration privileges privileges on some servers."
        )
        self.interpretation = ""
        self.risk = "Inadequate administration rights on computers can lead to easy privilege escalation for an attacker. With a privileged account, it is possible to perform local memory looting to find credentials for example."
        self.poa = "Only a handful of accounts should have administrator privilege on computers to perform some maintenance actions. No normal user should be admin of any computer, not even its own."

        self.users_admin_on_servers = requests_results["users_admin_on_servers"]
        self.users_admin_on_servers_list = requests_results[
            "users_admin_on_servers_list"
        ]
        self.servers_with_most_paths = requests_results["servers_with_most_paths"]
        self.users_admin_on_servers_all_data = requests_results[
            "users_admin_on_servers_all_data"
        ]

    def run(self):
        if self.users_admin_on_servers is None:
            return
        icon = '<i class="bi bi-people-fill"></i>'
        formated_data = generic_formating.formatGridValues2Columns(
            self.users_admin_on_servers,
            ["Computers", "Users who have a server compromise path"],
            "server_compromisable",
            icon=icon,
            icon2='<i class="bi bi-pc-display"></i>',
        )

        page = Page(
            self.arguments.cache_prefix,
            "server_users_could_be_admin",
            "Paths to servers",
            self.get_dico_description(),
        )
        grid = Grid("Servers with the most user compromise paths")
        grid.setheaders(["Computers", "Users who have a server compromise path"])
        grid.setData(json.dumps(formated_data))
        page.addComponent(grid)
        page.render()

        if self.users_admin_on_servers_list is None:
            return
        allValues = []
        for computer, values in self.users_admin_on_servers_list.items():
            for v in values:
                allValues.append(
                    "<span class='compromisable-by-%s'> %s </span>" % (computer, v)
                )
        page = Page(
            self.arguments.cache_prefix,
            "server_compromisable",
            "Compromisable computers",
            self.get_dico_description(),
        )
        grid = Grid("Server compromisable")
        grid.addheader("TO CHANGE")
        users_admin_of_servers = generic_formating.formatGridValues1Columns(
            allValues, grid.getHeaders()
        )
        grid.setData(users_admin_of_servers)
        page.addComponent(grid)
        page.render()

        self.data = self.servers_with_most_paths if self.servers_with_most_paths else 0

        self.name_description = f"Up to {self.data} users can compromise servers"

    def get_rating(self) -> int:
        return hasPathToDA(self.users_admin_on_servers_all_data)
