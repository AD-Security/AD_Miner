from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify

from ad_miner.sources.modules.common_analysis import createGraphPage, presence_of

from urllib.parse import quote


@register_control
class dom_admin_on_non_dc(Control):
    "Docstring of my control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "dom_admin_on_non_dc"

        self.title = "Tier-0 violation (sessions)"
        self.description = "Domain admins connected to non DC computers. If an attacker compromises any of these computers, he will instantly obtain domain administration privileges."
        self.risk = "Ideally, this page should be empty. Domain administrators connecting to computers leave credentials traces in memory, which could lead to a complete compromission of the Active Directory."
        self.poa = "If this page is not empty, modify the configuration so that no domain admins are connected to non DC computers."

        self.users_domain_admin_on_nondc = requests_results["dom_admin_on_non_dc"]

    def run(self):
        if self.users_domain_admin_on_nondc is None:
            return
        dico = {}
        for path in self.users_domain_admin_on_nondc:
            da = path.nodes[-1].name
            if da not in dico:
                dico[da] = {
                    "paths": [],
                    "computers": [],
                    "domains_impacted": {},
                    "domain": path.nodes[-1].domain,
                }
            dico[da]["paths"].append(path)
            dico[da]["computers"].append(path.nodes[0].name)
            dico[da]["domains_impacted"][path.nodes[0].domain] = 0

        page = Page(
            self.arguments.cache_prefix,
            "dom_admin_on_non_dc",
            "Tier-0 violation (sessions)",
            self.get_dico_description(),
        )
        grid = Grid("Tier-0 violation (sessions)")
        grid.setheaders(
            ["Domain", "Domain Admin", "Computers", "Paths", "Domains impacted"]
        )
        data = []
        for da in dico.keys():
            tmp = {}
            tmp["Domain"] = '<i class="bi bi-globe2"></i>' + dico[da]["domain"]
            tmp["Domain Admin"] = '<i class="bi bi-gem"></i>' + da
            nb_computers = len(dico[da]["computers"])
            tmp["Computers"] = grid_data_stringify(
                {
                    "link": f"dom_admin_on_non_dc_list_of_{quote(str(da.replace(' ', '_')))}.html",
                    "value": f'{nb_computers} computer{"s" if  nb_computers > 1 else ""} impacted',
                    "before_link": f"<i class='<i bi bi-pc-display-horizontal {str(nb_computers).zfill(6)}'></i>",
                }
            )
            nb_domains = len(dico[da]["domains_impacted"].keys())
            tmp["Domains impacted"] = grid_data_stringify(
                {
                    "link": f"dom_admin_on_non_dc_domain_list_of_{quote(str(da.replace(' ', '_')))}.html",
                    "value": f'{nb_domains} domain{"s" if nb_domains > 1 else ""} impacted',
                    "before_link": f"<i class='<i bi bi-globe2 {str(nb_domains).zfill(6)}'></i>",
                }
            )
            nb_paths = len(dico[da]["paths"])
            tmp["Paths"] = grid_data_stringify(
                {
                    "link": f"dom_admin_on_non_dc_paths_from_{quote(str(da.replace(' ', '_')))}.html",
                    "value": f'{nb_paths} path{"s" if  nb_paths > 1 else ""}',
                    "before_link": f"<i class='<i bi bi-sign-turn-right {str(nb_paths).zfill(6)}'></i>",
                }
            )
            data.append(tmp)
            createGraphPage(
                self.arguments.cache_prefix,
                f"dom_admin_on_non_dc_paths_from_{str(da.replace(' ', '_'))}",
                f"Sessions of {da} on non-DC computers",
                self.get_dico_description(),
                dico[da]["paths"],
                self.requests_results,
            )
            computer_list_page = Page(
                self.arguments.cache_prefix,
                f"dom_admin_on_non_dc_list_of_{str(da.replace(' ', '_'))}",
                f"Computers storing sensitive connection informations of {da}",
                self.get_dico_description(),
            )
            computer_list_grid = Grid(
                f"Computers storing sensitive connection informations of {da}"
            )
            computer_list_grid.setheaders(["Computer"])
            computer_list_data = [
                {"Computer": '<i class="bi bi-pc-display-horizontal"></i>' + c}
                for c in dico[da]["computers"]
            ]
            computer_list_grid.setData(computer_list_data)
            computer_list_page.addComponent(computer_list_grid)
            computer_list_page.render()

            domain_list = dico[da]["domains_impacted"].keys()
            domain_list_page = Page(
                self.arguments.cache_prefix,
                f"dom_admin_on_non_dc_domain_list_of_{str(da.replace(' ', '_'))}",
                f"Domains of computers storing sensitive connection informations of {da}",
                self.get_dico_description(),
            )
            domain_list_grid = Grid(
                f"Domains of computers storing sensitive connection informations of {da}"
            )
            domain_list_grid.setheaders(["Domain"])
            domain_list_data = [{"Domain": '<i class="bi bi-globe2"></i>' + c} for c in domain_list]
            domain_list_grid.setData(domain_list_data)
            domain_list_page.addComponent(domain_list_grid)
            domain_list_page.render()
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.users_domain_admin_on_nondc)
            if self.users_domain_admin_on_nondc
            else 0
        )

        self.name_description = (
            f"{self.data} Tier-$0$ sessions on non-Tier-$0$ computers"
        )

    def get_rating(self) -> int:
        return presence_of(self.users_domain_admin_on_nondc)
