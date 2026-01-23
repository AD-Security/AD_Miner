from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control

from ad_miner.sources.modules import generic_formating
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.common_analysis import parseConstrainedData

import json


@register_control
class users_constrained_delegations(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "kerberos"
        self.control_key = "users_constrained_delegations"

        self.title = "Kerberos constrained delegation"
        self.description = "These accounts have constrained delegations privileges."
        self.risk = "Accounts that have constrained delegation rights can impersonate any user against a determined service. This means that this service will trust the accounts with whatever identity is presented. Compromission of an account with constrained delegation would allow the attacker to progress deeper in the information system and further compromise the domain."
        self.poa = "Set the accounts that should not be impersonated as 'Protected users' so the service cannot be abused to use their identity. Set the MachineAccountQuota to 0 if possible, so that attackers cannot create eligible accounts for constrained delegations."

        self.users_constrained_delegations = requests_results[
            "users_constrained_delegations"
        ]

        if self.users_constrained_delegations is not None:
            self.users_constrained_delegations = dict(
                sorted(
                    parseConstrainedData(self.users_constrained_delegations).items(),
                    key=lambda x: len(x[1]),
                    reverse=True,
                )
            )

    def run(self):
        if self.users_constrained_delegations is None:
            return
        headers = ["Users", "Number of computers", "Computers"]
        formated_data = generic_formating.formatGridValues3Columns(
            generic_formating.formatFor3Col(
                self.users_constrained_delegations, headers
            ),
            headers,
            "users_constrained_delegations",
        )
        page = Page(
            self.arguments.cache_prefix,
            "users_constrained_delegations",
            "Users with constrained delegations",
            self.get_dico_description(),
        )
        grid = Grid("Users with constrained delegations")
        grid.setheaders(headers)
        grid.setData(json.dumps(formated_data))
        page.addComponent(grid)
        page.render()

        self.data = (
            len(self.users_constrained_delegations)
            if self.users_constrained_delegations
            else 0
        )

        self.name_description = (
            f"{self.data} users with Kerberos constrained delegations"
        )

    def get_rating(self) -> int:
        req = self.users_constrained_delegations
        if req is None:
            return -1
        if len(req) > 0:
            return 3
        return 5
