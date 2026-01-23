from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules import generic_formating, generic_computing

from ad_miner.sources.modules.common_analysis import presence_of

from urllib.parse import quote


@register_control
class has_sid_history(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "has_sid_history"

        self.title = "Objects with SID history"
        self.description = "SID History (Security Identifier History) is a feature that allows a user or group to retain access to resources that they had permissions for in a different domain. This feature is particularly useful in scenarios involving domain migrations, domain trust relationships, or domain reorganizations."
        self.risk = " If an attacker gains control of an account with SID History entries, they may be able to use those historical SIDs to gain unauthorized access to resources in old domains. This is particularly concerning if the attacker can exploit vulnerabilities or weak security practices in the old domain."
        self.poa = "Regularly review and clean up SID History entries for users and groups that no longer require access to resources in old domains."

        self.has_sid_history = requests_results["has_sid_history"]
        self.users_admin_on_computers = requests_results["users_admin_on_computers"]

        self.users_admin_computer_list = generic_computing.getListAdminTo(
            self.users_admin_on_computers, "user", "computer"
        )

    def run(self):
        page = Page(
            self.arguments.cache_prefix,
            "has_sid_history",
            "Objects who can abuse SID History",
            self.get_dico_description(),
        )
        grid = Grid("Objects who can abuse SID History")
        headers = ["Has SID History", "Admin of", "Target", "admin of"]

        # add icons for type of object
        star_icon = "<i class='bi bi-star-fill' style='color:gold; text-shadow: 0px 0px 1px black, 0px 0px 1px black, 0px 0px 1px black, 0px 0px 1px black;' title='This SID history allows for access to more computers'></i>"
        for row in self.has_sid_history:
            # add admin of columns
            row["Admin of"] = "-"
            row["admin of"] = "-"
            target_count = 0
            origin_count = 0
            for d in self.users_admin_on_computers:
                name_user = d["user"]
                if row["Has SID History"] == name_user:
                    origin_count = len(self.users_admin_computer_list[name_user])
                    row["Admin of"] = (
                        f"<i class='bi bi-pc-display-horizontal 000003'></i><a style='color: blue' target='_blank' href='users_admin_of_computers_details.html?parameter={quote(name_user)}'> {origin_count} computer{'s' if origin_count > 0 else ''} </a>"
                    )

                if row["Target"] == name_user:
                    target_count = len(self.users_admin_computer_list[name_user])
                    row["admin of"] = (
                        f"<i class='bi bi-pc-display-horizontal 000003'></i><a style='color: blue' target='_blank' href='users_admin_of_computers_details.html?parameter={quote(name_user)}'> {target_count} computer{'s' if target_count > 0 else ''} </a>"
                    )

            # add user icons
            type_label_a = generic_formating.clean_label(row["Type_a"])
            row["Has SID History"] = (
                f"{generic_formating.get_label_icon(type_label_a)} {row['Has SID History']}"
            )

            type_label_b = generic_formating.clean_label(row["Type_b"])
            row["Target"] = (
                f"{generic_formating.get_label_icon(type_label_b)} {row['Target']}"
            )

            # add star icon
            if target_count > origin_count:
                row["Has SID History"] = star_icon + " " + row["Has SID History"]
                row["Target"] = star_icon + " " + row["Target"]

        grid.setheaders(headers)
        grid.setData(self.has_sid_history)

        page.addComponent(grid)
        page.render()

        self.data = len(self.has_sid_history)
        self.name_description = f"{len(self.has_sid_history)} objects with SID history"

    def get_rating(self) -> int:
        return presence_of(self.has_sid_history, 2)
