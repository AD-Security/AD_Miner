from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.path_neo4j import Path

from ad_miner.sources.modules.macro_graph_class import MacroGraphPage

from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import (
    percentage_superior,
    days_format,
    manage_plural,
)

from urllib.parse import quote
from tqdm import tqdm


@register_control
class users_admin_of_computers(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "users_admin_of_computers"

        self.title = "Users with local admin privileges"
        self.description = "Users have administration rights over machines, creating potential compromission paths."
        self.risk = "You should watch out for accounts who are admin of too many computers or users who should not be admin at all. Wrongfully configured administration privileges are a big vector of vertical and lateral movement."
        self.poa = "Review this list to ensure admin privilege are effectively provided on a need to know basis."

        self.description_users_to_computer = {
            "description": "Path of users who have direct or indirect administration privilege on computers",
            "interpretation": "",
            "risk": "Inadequate administration rights on computers can lead to easy privilege escalation for an attacker. With a privileged account, it is possible to perform local memory looting to find credentials for example.",
            "poa": "Only a handful of accounts should have administrator privilege on computers to perform some maintenance actions. No normal user should be admin of any computer, not even its own.",
        }

        self.admin_list = requests_results["admin_list"]
        self.users = requests_results["nb_enabled_accounts"]
        self.users_kerberoastable_users = requests_results["nb_kerberoastable_accounts"]
        self.users_pwd_not_changed_since = requests_results["password_last_change"]

        self.users_admin_on_computers = requests_results["users_admin_on_computers"]

        self.creates_path_to_DA = False

    def run(self):

        headers = [
            "User",
            "Display Name",
            "Kerberoastable",
            "Last password change",
            "List of computers",
            "Path to computers",
            "Path to DA"
        ]
        headers_details = ["User", "Computers"]

        def check_kerberoastable(account):
            for elem in self.users_kerberoastable_users:
                if elem["name"] == account:
                    return "<i class='bi bi-ticket-perforated-fill' style='color: #b00404;' title='This account is vulnerable to Kerberoasting'></i>YES"
            return "-"

        def get_last_pass_change(account):
            for elem in self.users_pwd_not_changed_since:
                if elem["user"] == account:
                    return days_format(elem["days"])
            return "<i class='bi bi-calendar3'></i>Unknown"

        users_displaynames = {}
        for entry in self.users_admin_on_computers:
            users_displaynames[entry['user']] = entry['displayname'] if entry['displayname'] else 'N/A'

        # Creating one dic with all data for performance reasons
        processed_data = {}

        for d in tqdm(self.users_admin_on_computers):
            username = d["user"]
            if username not in processed_data:
                processed_data[username] = {
                    "displayname": users_displaynames[username],
                    "kerberoastable": check_kerberoastable(username),
                    "last password change": get_last_pass_change(username),
                    "list_computer_names": [d["computer"]],
                    "admin_path": [d["p"]],
                    "paths_from_user_to_DA": [],  # through computers
                    "is_da": username in self.admin_list,
                }

            else:
                processed_data[username]["list_computer_names"].append(d["computer"])
                processed_data[username]["admin_path"].append(d["p"])
            if d["has_path_to_da"]:
                self.creates_path_to_DA = True
                for p in self.requests_results["dico_computers_to_da"][d["computer"]]:
                    # do not add path to DA if already DA of this domain
                    if (
                        processed_data[username]["is_da"]
                        and d["p"].nodes[0].domain == p.nodes[-1].domain
                    ):
                        continue
                    complete_path = Path(d["p"].nodes[:-1] + p.nodes)
                    processed_data[username]["paths_from_user_to_DA"].append(complete_path)

        # Sorting computer names to remove duplicates
        for username in processed_data:
            processed_data[username]["list_computer_names"] = list(
                set(processed_data[username]["list_computer_names"])
            )

        # Initializing things to generate page
        page = Page(
            self.arguments.cache_prefix,
            "users_admin_of_computers",
            "Users with local admin privileges",
            self.get_dico_description(),
        )
        grid = Grid("Users admins of")
        grid.setheaders(headers)
        main_grid_data = []
        macrographpages_admin_paths = MacroGraphPage()
        macrographpages_paths_to_DA = MacroGraphPage()

        users_admin_of_computers_details_grid = []

        for username in processed_data:
            tmp_dict = {}

            tmp_dict["User"] = username
            # Add gem if DA somewhere, bi-person-fill else
            if processed_data[username]["is_da"]:
                tmp_dict["User"] = (
                    '<i class="bi bi-gem" title="This user is domain admin" style="color: #c0941cff;"></i>'
                    + tmp_dict["User"]
                )
            else:
                tmp_dict["User"] = '<i class="bi bi-person-fill"></i>' + tmp_dict["User"]
            tmp_dict["Display Name"] = processed_data[username]["displayname"]
            tmp_dict["Kerberoastable"] = processed_data[username]["kerberoastable"]
            tmp_dict["Last password change"] = processed_data[username]["last password change"]

            admin_link = macrographpages_admin_paths.addPathsAndGetLink(
                "users_admin_computers", processed_data[username]["admin_path"]
            )

            count_admin = len(processed_data[username]["admin_path"])
            computer_count = len(processed_data[username]["list_computer_names"])
            sortClass = str(count_admin).zfill(6)

            tmp_dict["Path to computers"] = grid_data_stringify(
                {
                    "link": admin_link
                    + f"?node={str(processed_data[username]['admin_path'][0].nodes[0].id)}",
                    "value": f"{count_admin} {manage_plural(count_admin, ('path', 'paths'))} to {manage_plural(computer_count, ('computer', 'computers'))}",
                    "before_link": f"<i class='bi bi-sign-turn-right {sortClass}' aria-hidden='true'></i>",
                }
            )

            count_to_DA = len(processed_data[username]["paths_from_user_to_DA"])
            sortClassDA = str(count_to_DA).zfill(6)

            get_domain = lambda o: o.nodes[-1].domain
            count_impacted_domains = len(
                {get_domain(o) for o in processed_data[username]["paths_from_user_to_DA"]}
            )

            if count_to_DA > 0:

                DA_link = macrographpages_paths_to_DA.addPathsAndGetLink(
                    "users_admin_computers_to_DA", processed_data[username]["paths_from_user_to_DA"]
                )

                tmp_dict["Path to DA"] = grid_data_stringify(
                    {
                        "link": DA_link
                        + f"?node={str(processed_data[username]['admin_path'][0].nodes[0].id)}",
                        "value": f"{count_to_DA} {manage_plural(count_to_DA, ('path', 'paths'))} to DA ({count_impacted_domains} {manage_plural(count_impacted_domains, ('domain', 'domains'))})",
                        "before_link": f"<i class='bi bi-sign-turn-right-fill {sortClassDA}' style='color:#b00404;' aria-hidden='true'></i>",
                    }
                )
            else:
                tmp_dict["Path to DA"] = "-"

            tmp_dict["List of computers"] = grid_data_stringify(
                {
                    "link": f"users_admin_of_computers_details.html?parameter={quote(username)}",
                    "value": f" {computer_count} {manage_plural(computer_count, ('computer', 'computers'))}",
                    "before_link": f"<i class='bi bi-hdd-network {sortClass}'></i>",
                }
            )

            main_grid_data.append(tmp_dict)

            users_admin_of_computers_details_grid.append(
                {
                    headers_details[0]: username,
                    headers_details[1]: processed_data[username]["list_computer_names"],
                }
            )

        grid.setData(main_grid_data)
        grid.writeEvolutionJSON(
            self.arguments.cache_prefix,
            "users_admin_of_computers",
            main_grid_data,
        )
        grid.AddNewIconsToNewLines(
            self.arguments.previous_prefix, "users_admin_of_computers", "User"
        )
        page.addComponent(grid)
        page.render()

        macrographpages_admin_paths.render_pages(
            self.arguments, self.requests_results, self.dico_description, "Path to computers"
        )
        macrographpages_paths_to_DA.render_pages(
            self.arguments,
            self.requests_results,
            self.dico_description,
            "Path to DA through admin privileges",
        )

        page = Page(
            self.arguments.cache_prefix,
            "users_admin_of_computers_details",
            "Users with local admin privileges",
            self.get_dico_description(),
        )
        grid = Grid("Users admins of")
        grid.setheaders(headers)
        grid.setData(users_admin_of_computers_details_grid)
        page.addComponent(grid)
        page.render()

        self.data = len(processed_data.keys())
        self.name_description = f"{self.data} users with local admin privileges"

    def get_rating(self) -> int:
        if self.creates_path_to_DA:
            return 1
        return percentage_superior(self.users_admin_on_computers, self.users, criticity=2, percentage=0.5)
