from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.utils import days_format
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class users_password_not_required(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "passwords"
        self.control_key = "users_password_not_required"

        self.title = "Password requirement bypass"
        self.description = "Those users have the attribute 'Password not required'. This attribute technically allows the account to accept blank password to be set and even override the password policy of the company."
        self.risk = "Such misconfiguration could lead to some account having non compliant password suck as a blank or weak password and might be easier to compromise."
        self.poa = "Ensure that this list is empty by setting the ms-DS-User-Password-Not-Required attribute to false for every user."

        self.users_password_not_required = requests_results[
            "get_users_password_not_required"
        ]

    def run(self):
        if self.users_password_not_required is None:
            self.users_password_not_required = []
            return
        page = Page(
            self.arguments.cache_prefix,
            "users_password_not_required",
            "Users that can bypass your password policy",
            self.get_dico_description(),
        )
        grid_data = []
        for dic in self.users_password_not_required:
            tmp_data = {}
            tmp_data["Domain"] = '<i class="bi bi-globe2"></i>' + dic["domain"]
            tmp_data["User"] = '<i class="bi bi-person-fill"></i>' + dic["user"]
            tmp_data["Password last change"] = days_format(dic["pwdlastset"])
            tmp_data["Last logon"] = days_format(dic["lastlogon"])
            grid_data.append(tmp_data)
        grid = Grid("Users that can bypass your password policy")
        grid.setheaders(["Domain", "User", "Password last change", "Last logon"])
        grid.setData(grid_data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.users_password_not_required)

        self.name_description = f"{self.data} users without password requirement"

    def get_rating(self) -> int:
        return presence_of(self.users_password_not_required, 3)
