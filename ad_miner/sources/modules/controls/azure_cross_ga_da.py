from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import createGraphPage
from hashlib import md5


@register_control
class azure_cross_ga_da(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_permissions"
        self.control_key = "azure_cross_ga_da"

        self.title = "Cross on-prem/Entra ID path to tier-0"
        self.description = "Paths from Entra ID admins that leads to on premise admins compromission and vice-versa"
        self.risk = "With these paths, a attacker that would have compromised one environment can directly compromise the other one (either cloud or on premise)."
        self.poa = "Limit the existence of these paths by limiting the synchronization between administration accounts."

        self.azure_cross_ga_da = requests_results["azure_cross_ga_da"]
        self.collected_domains = requests_results["nb_domain_collected"]
        self.azure_tenants = requests_results["azure_tenants"]

        self.tenant_id_name = {}
        for tenant in self.azure_tenants:
            self.tenant_id_name[tenant["ID"]] = tenant["Name"]

    def run(self):
        self.azure_total_cross_ga_da_compromission = 0
        if self.azure_cross_ga_da is None:
            self.azure_cross_ga_da = []
        # Create the page
        page = Page(
            self.arguments.cache_prefix,
            "azure_cross_ga_da",
            "Cross on-prem/Entra ID path to tier-0",
            self.get_dico_description(),
        )
        # Create the grid
        grid = Grid("Cross on-prem/Entra ID path to tier-0")
        # Add the headers
        headers = ["Domain / Tenant"]
        for tenant_id in self.tenant_id_name.keys():
            headers.append(self.tenant_id_name[tenant_id])

        paths_sorted_per_domain = {}
        for domain in self.collected_domains:
            domain = domain[0]
            paths_sorted_per_domain[domain] = {}
            # We re-do the loop for easier code reading
            for tenant_id in self.tenant_id_name.keys():
                paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]] = {
                    "GA_to_DA": [],
                    "DA_to_GA": [],
                }

        for path in self.azure_cross_ga_da:
            # Case where starting point is Azure
            if path.nodes[0].tenant_id != None:
                domain = path.nodes[-1].domain
                tenant_id = path.nodes[0].tenant_id
                paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]][
                    "GA_to_DA"
                ].append(path)
            # Case where starting point is on premise
            else:
                domain = path.nodes[0].domain
                tenant_id = path.nodes[-1].tenant_id
                paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]][
                    "DA_to_GA"
                ].append(path)

        data = []
        for domain in paths_sorted_per_domain.keys():
            row1 = {"Domain / Tenant": domain}
            row2 = {"Domain / Tenant": domain}
            for tenant_id in self.tenant_id_name.keys():
                count1 = len(
                    paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]][
                        "GA_to_DA"
                    ]
                )
                count2 = len(
                    paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]][
                        "DA_to_GA"
                    ]
                )
                sortClass1 = str(count1).zfill(6)
                sortClass2 = str(count2).zfill(6)
                hash1 = md5((tenant_id + domain).encode()).hexdigest()
                hash2 = md5((domain + tenant_id).encode()).hexdigest()
                if count1 > 0:
                    row1[self.tenant_id_name[tenant_id]] = grid_data_stringify(
                        {
                            "link": f"azure_cross_ga_da_{hash1}.html",
                            "value": f"{count1} Entra ID ⇨ On-prem path{'s' if count1 > 1 else ''}",
                            "before_link": f"<i class='bi bi-sign-turn-right {sortClass1}' aria-hidden='true'></i>",
                        }
                    )
                    createGraphPage(
                        self.arguments.cache_prefix,
                        f"azure_cross_ga_da_{hash1}",
                        f"Paths from {self.tenant_id_name[tenant_id]} to {domain}",
                        self.get_dico_description(),
                        paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]][
                            "GA_to_DA"
                        ],
                        self.requests_results,
                    )
                    self.azure_total_cross_ga_da_compromission += 1
                else:
                    row1[self.tenant_id_name[tenant_id]] = "-"
                if count2 > 0:
                    row2[self.tenant_id_name[tenant_id]] = grid_data_stringify(
                        {
                            "link": f"azure_cross_ga_da_{hash2}.html",
                            "value": f"{count2} On-prem ⇨ ENtra ID path{'s' if count2 > 1 else ''}",
                            "before_link": f"<i class='bi bi-sign-turn-right {sortClass2}' aria-hidden='true'></i>",
                        }
                    )
                    createGraphPage(
                        self.arguments.cache_prefix,
                        f"azure_cross_ga_da_{hash2}",
                        f"Paths from {domain} to {self.tenant_id_name[tenant_id]}",
                        self.get_dico_description(),
                        paths_sorted_per_domain[domain][self.tenant_id_name[tenant_id]][
                            "DA_to_GA"
                        ],
                        self.requests_results,
                    )
                    self.azure_total_cross_ga_da_compromission += 1
                else:
                    row2[self.tenant_id_name[tenant_id]] = "-"
            data.append(row1)
            data.append(row2)

        grid.setheaders(headers)
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = self.azure_total_cross_ga_da_compromission
        self.name_description = f"{self.azure_total_cross_ga_da_compromission} domain{'s' if self.azure_total_cross_ga_da_compromission > 1 else ''} & tenant{'s' if self.azure_total_cross_ga_da_compromission > 1 else ''} are cross compromisable"

    def get_rating(self) -> int:
        return 1 if self.azure_total_cross_ga_da_compromission > 0 else 5
