from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class privileged_accounts_outside_Protected_Users(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "privileged_accounts_outside_Protected_Users"

        self.title = "Privileged account outside the protected users group."
        self.description = (
            "Privileged accounts not protected by the Protected Users group."
        )
        self.risk = "The Protected Users group should be used to harden authentication and encryption mechanisms for sensitive accounts."
        self.poa = "Privileged accounts must be part of the Protected Users group."

        self.users_nb_domain_admins = requests_results["nb_domain_admins"]

    def run(self):
        if self.users_nb_domain_admins is None:
            self.users_nb_domain_admins = []

        page = Page(
            self.arguments.cache_prefix,
            "privileged_accounts_outside_Protected_Users",
            "Privileged accounts not part of the Protected Users group",
            self.get_dico_description(),
        )
        grid = Grid("Privileged accounts not part of the Protected Users group")
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
                "protected user",
            ]
        )

        data = []

        for dic in self.users_nb_domain_admins:
            if "Protected Users" in dic["admin type"]:
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
            tmp_data["protected user"] = (
                '<i class="bi bi-x-circle" style="color: rgb(255, 89, 94);"></i>Unprotected'
            )
            data.append(tmp_data)

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(
            [
                dic
                for dic in self.users_nb_domain_admins
                if "Protected Users" not in dic["admin type"]
            ]
        )

        # TODO define the sentence that will be displayed in the 'smolcard' view and in the center of the mainpage
        self.name_description = f"{self.data} privileged accounts not in Protected Users group"

    def get_rating(self) -> int:
        return presence_of(
            [
                dic
                for dic in self.users_nb_domain_admins
                if "Protected Users" not in dic["admin type"]
            ],
            criticity=2,
        )
