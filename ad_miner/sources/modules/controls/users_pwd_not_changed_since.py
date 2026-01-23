from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import percentage_superior


@register_control
class users_pwd_not_changed_since(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "passwords"

        self.control_key = "users_pwd_not_changed_since"

        self.title = "Users with old passwords"
        self.description = (
            "These accounts have not changed their password for a long period of time."
        )
        self.risk = "Users should regularily change their passwords. This list should be as reduced as possible. Users not changing their password could be a securtiy flaw if these passwords happend to leak."
        self.poa = (
            "Make sure your GPO asks for password renewal and that it is enforced."
        )

        self.users_pwd_not_changed_since = requests_results["password_last_change"]

        self.users_pwd_not_changed_since_3months = (
            [
                user
                for user in self.users_pwd_not_changed_since
                if user["days"] > int(self.arguments.renewal_password)
            ]
            if self.users_pwd_not_changed_since is not None
            else None
        )

        self.users_nb_domain_admins = requests_results["nb_domain_admins"]

        self.users = requests_results["nb_enabled_accounts"]
        self.admin_list = []
        for admin in self.users_nb_domain_admins:
            self.admin_list.append(admin["name"])

    def run(self):
        if self.users_pwd_not_changed_since_3months is None:
            return
        page = Page(
            self.arguments.cache_prefix,
            "users_pwd_not_changed_since",
            f"Number of users with password not changed for at least {self.arguments.renewal_password} days",
            self.get_dico_description(),
        )
        grid = Grid("Users with password not changed > 3 months")
        # grid.setheaders(["user", "days"])
        # grid.setData(self.users_pwd_not_changed_since_3months)

        # Human readable display
        grid.setheaders(["user", "Last password change", "Account Creation Date"])
        data = []
        for dict in self.users_pwd_not_changed_since_3months:
            tmp_data = {"user": dict["user"]}
            if dict["user"] in self.admin_list:
                tmp_data["user"] = (
                    '<i class="bi bi-gem" title="This user is domain admin"></i>'
                    + tmp_data["user"]
                )
            else:
                tmp_data["user"] = (
                    '<i class="bi bi-person-fill"></i>' + tmp_data["user"]
                )
            tmp_data["Last password change"] = days_format(dict["days"])
            tmp_data["Account Creation Date"] = days_format(dict["accountCreationDate"])

            data.append(tmp_data)
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        # TODO define the metric of your control
        # it will be stored in the data json
        self.data = (
            len(self.users_pwd_not_changed_since_3months)
            if self.users_pwd_not_changed_since_3months
            else 0
        )

        self.name_description = f"{self.data} unchanged passwords > ${int(int(self.arguments.renewal_password)/30)}$ months"

    def get_rating(self) -> int:
        return percentage_superior(
            self.users_pwd_not_changed_since_3months,
            self.users,
            criticity=3,
            percentage=0.1,
            presence=True,
        )
