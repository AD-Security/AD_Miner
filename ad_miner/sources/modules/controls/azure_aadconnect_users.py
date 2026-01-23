from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import presence_of


@register_control
class azure_aadconnect_users(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "azure"
        self.category = "az_permissions"
        self.control_key = "azure_aadconnect_users"

        self.title = "Users possibly related to Microsoft Entra Connect"
        self.description = "All Users and Entra ID Users possibly related to Microsoft Entra Connect"
        self.risk = "If the list of users linked to Microsoft Entra Connect does not respect the principle of least privilege, this increases the attack surface."
        self.poa = "Review and clean up the liste users related to Microsoft Entra Connect"

        self.azure_aadconnect_users = requests_results["azure_aadconnect_users"]

    def run(self):
        if self.azure_aadconnect_users is None:
            return

        page = Page(
            self.arguments.cache_prefix,
            "azure_aadconnect_users",
            "Entra ID users with Microsoft Entra Connect session",
            self.get_dico_description(),
        )
        grid = Grid("Entra ID users with Microsoft Entra Connect session")

        data = []
        for user in self.azure_aadconnect_users:
            data.append(
                {
                    "Tenant ID": '<i class="bi bi-file-earmark-person"></i>'
                    + f'{user["Tenant ID"] if user["Tenant ID"] != None else "-"}',
                    "Name": '<i class="bi bi-people-fill"></i>' + user["Name"],
                    "Session": user["Session"] if user["Session"] != None else "-",
                }
            )

        grid.setheaders(["Tenant ID", "Name", "Session"])

        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = len(self.azure_aadconnect_users)
        self.name_description = (
            f"{len(self.azure_aadconnect_users)} users with Microsoft Entra Connect session"
        )

    def get_rating(self) -> int:
        return presence_of(self.azure_aadconnect_users, 3)
