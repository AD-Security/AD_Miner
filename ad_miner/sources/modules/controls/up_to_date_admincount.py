from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid


@register_control
class up_to_date_admincount(Control):
    "Docstring of my control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "up_to_date_admincount"

        self.title = "Inadequate AdminCount settings"
        self.description = "Discrepancies in 'adminCount' attribute for accounts"
        self.risk = "Potential security oversight leading to unauthorized access, privilege misrepresentation, or unintended privilege escalation."
        self.poa = "Consistently audit and rectify any discrepancies in the `adminCount` attribute settings for all accounts, ensuring it aligns with actual privilege levels."

        self.users_nb_domain_admins = requests_results["nb_domain_admins"]
        self.unpriviledged_users_with_admincount = requests_results[
            "unpriviledged_users_with_admincount"
        ]

    def run(self):
        if self.users_nb_domain_admins is None:
            self.users_nb_domain_admins = []
        if self.unpriviledged_users_with_admincount is None:
            self.unpriviledged_users_with_admincount = []
        page = Page(
            self.arguments.cache_prefix,
            "up_to_date_admincount",
            "Inadequate AdminCount settings",
            self.get_dico_description(),
        )
        grid = Grid("Inadequate AdminCount settings")
        grid.setheaders(
            [
                "domain",
                "name",
                "domain admin",
                "schema admin",
                "enterprise admin",
                "key admin",
                "enterprise key admin",
                "builtin admin",
                "admincount",
            ]
        )

        data = []

        for dic in self.users_nb_domain_admins:
            if dic["admincount"]:
                continue
            tmp_data = {"domain": '<i class="bi bi-globe2"></i>' + dic["domain"]}
            tmp_data["name"] = '<i class="bi bi-gem"></i>' + dic["name"]
            tmp_data["domain admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Domain Admin" in dic["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["schema admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Schema Admin" in dic["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["enterprise admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Enterprise Admin" in dic["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["key admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "_ Key Admin" in dic["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["enterprise key admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Enterprise Key Admin" in dic["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["builtin admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Builtin Administrator" in dic["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["admincount"] = (
                '<i class="bi bi-square" style="color: red;"></i>Missing admincount'
            )
            data.append(tmp_data)

        for name, domain, da_type in self.unpriviledged_users_with_admincount:
            tmp_data = {"domain": '<i class="bi bi-globe2"></i>' + domain}
            tmp_data["name"] = '<i class="bi bi-person-fill"></i>' + name
            tmp_data["domain admin"] = '<i class="bi bi-square"></i>'
            tmp_data["schema admin"] = '<i class="bi bi-square"></i>'
            tmp_data["enterprise admin"] = '<i class="bi bi-square"></i>'
            tmp_data["key admin"] = '<i class="bi bi-square"></i>'
            tmp_data["enterprise key admin"] = '<i class="bi bi-square"></i>'
            tmp_data["builtin admin"] = '<i class="bi bi-square"></i>'
            tmp_data["admincount"] = (
                '<i class="bi bi-check-square-fill" style="color: red;"></i>Misleading admincount<span style="display:none">True</span>'
            )
            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.priviledge_users_without_admincount = len(
            [dic for dic in self.users_nb_domain_admins if not dic["admincount"]]
        )

        self.data = len(self.unpriviledged_users_with_admincount) + len(
            [dic for dic in self.users_nb_domain_admins if not dic["admincount"]]
        )
        self.name_description = f"{self.priviledge_users_without_admincount} priviledged accounts without admincount and {len(self.unpriviledged_users_with_admincount)} unpriviledged accounts with admincount"

    def get_rating(self) -> int:
        if (
            self.unpriviledged_users_with_admincount is None
            or self.users_nb_domain_admins is None
        ):
            return -1
        for da_dic in self.users_nb_domain_admins:
            if not da_dic["admincount"]:
                return 1
        if len(self.unpriviledged_users_with_admincount) > 0:
            return 3
        return 5
