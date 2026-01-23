from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid

from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class nb_domain_admins(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "nb_domain_admins"

        self.title = "Inadequate number of domain admins"
        self.description = "These accounts are the most privileged and have unlimited access to the AD infrastructure."
        self.risk = "Domain admin accounts have unlimited access over the Active Directory infrastructure. Compromise of a domain account will provide attackers full access over the infrastructure. Such privileges should be stricly provided on a need-to-know basis."
        self.poa = "Make sure that domain admins shown here effectively need this level of privileges. Also, make sure that these accounts are used solely for activities that require domain administration (i.e., these accounts should not be used for daily routines and should never be used outside of domain controllers)"

        self.users_nb_domain_admins = requests_results["nb_domain_admins"]

    def run(self):
        if self.users_nb_domain_admins is None:
            self.max_da_per_domain = 0
            return
        page = Page(
            self.arguments.cache_prefix,
            "nb_domain_admins",
            "List of domain admins",
            self.get_dico_description(),
        )
        # Count the max number of domain admins per domain
        count_da = {}
        for da in self.users_nb_domain_admins:
            try:
                count_da[da["domain"]] += 1
            except KeyError:
                count_da[da["domain"]] = 1
        self.max_da_per_domain = max(count_da.values(), default=0)

        data = []

        for da in self.users_nb_domain_admins:
            tmp_data = {}
            tmp_data["domain"] = '<i class="bi bi-globe2"></i>' + da["domain"]
            tmp_data["name"] = '<i class="bi bi-gem"></i>' + da["name"]
            tmp_data["domain admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Domain Admin" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["schema admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Schema Admin" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["enterprise admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Enterprise Admin" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["protected users"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Protected Users" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["key admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "_ Key Admin" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["enterprise key admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Enterprise Key Admin" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            tmp_data["builtin admin"] = (
                '<i class="bi bi-check-square-fill"></i><span style="display:none">True</span>'
                if "Builtin Administrator" in da["admin type"]
                else '<i class="bi bi-square"></i>'
            )
            data.append(tmp_data)

        grid = Grid("Domain admins")
        grid.setheaders(
            [
                "domain",
                "name",
                "domain admin",
                "schema admin",
                "enterprise admin",
                "protected users",
                "key admin",
                "enterprise key admin",
                "builtin admin",
            ]
        )
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.users_nb_domain_admins) if self.users_nb_domain_admins else 0
        )
        self.name_description = f"{self.data} domain admins"

    def get_rating(self) -> int:
        return presence_of(["1"] * self.max_da_per_domain, criticity=2, threshold=10)
