from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import percentage_superior


@register_control
class never_expires(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "passwords"

        self.control_key = "never_expires"

        self.title = "Users without password expiration"
        self.description = "These accounts have their passwords set to never expire."
        self.risk = "Ideally, this list should be empty. Non-expiring passwords are easier to exploit for an attacker."
        self.poa = "Check that all of these users have a reason to be on this list."

        self.users_password_never_expires = requests_results[
            "user_password_never_expires"
        ]
        self.users = requests_results["nb_enabled_accounts"]
        self.users_nb_domain_admins = requests_results["nb_domain_admins"]
        self.admin_list = []
        for admin in self.users_nb_domain_admins:
            self.admin_list.append(admin["name"])

    def run(self):
        if self.users_password_never_expires is None:
            return
        for user in self.users_password_never_expires:
            # Add admin icon
            if user["name"] in self.admin_list:
                user["name"] = (
                    '<i class="bi bi-gem" title="This user is domain admin"></i>'
                    + user["name"]
                )
            else:
                user["name"] = '<i class="bi bi-person-fill"></i>' + user["name"]
        page = Page(
            self.arguments.cache_prefix,
            "never_expires",
            "List of all users without password expiration",
            self.get_dico_description(),
        )
        grid = Grid("Users without password expiration")
        grid.setheaders(
            [
                "domain",
                "name",
                "Last login",
                "Last password change",
                "Account Creation Date",
            ]
        )

        data = []
        for dict in self.users_password_never_expires:
            tmp_data = {
                "domain": '<i class="bi bi-globe2"></i>' + dict["domain"],
                "name": dict["name"],
            }
            tmp_data["Last login"] = days_format(dict["LastLogin"])
            tmp_data["Last password change"] = days_format(dict["LastPasswChange"])
            tmp_data["Account Creation Date"] = days_format(dict["accountCreationDate"])

            data.append(tmp_data)
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = (
            len(self.users_password_never_expires)
            if self.users_password_never_expires
            else 0
        )

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.data} users without password expiration"

    def get_rating(self) -> int:
        # TODO define the rating function.
        # You can use common rating functions define in ad_miner.sources.modules.common_analysis like presenceof, percentage_superior, etc.
        # -1 = grey, 1 = red, 2 = orange, 3 = yellow, 4 =green, 5 = green,
        return percentage_superior(
            self.users_password_never_expires,
            self.users,
            criticity=2,
            percentage=0.8,
            presence=True,
        )
