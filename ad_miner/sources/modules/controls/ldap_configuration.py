from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid


@register_control
class ldap_configuration(Control):
    "LDAP and LDAPS server configuration"

    # LDAP + no LDAP signing required -> relay to LDAP possible (from SMB if drom the mic / NTLMv1)
    # LDAPS + no EPA -> relay to LDAP possible (seems not correctly implemented by ntlmrelayx when coming from SMB)
    # LDAPS doesn't support LDAP signing (because based on SSL like HTTPS)

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "ldap_configuration"

        self.title = "LDAP servers configuration"
        self.description = "LDAP(S) allows for the modification of permissions and configurations within the Active Directory. Signing protects against relay attacks targeting LDAP. Extended Protection for Authentication (EPA) protects against relay attacks targeting LDAPS."
        self.risk = "Relay attacks targeting LDAP or LDAPS allow attackers to move laterally and vertically, potentially compromising the domain."
        self.poa = "Enable LDAP signing and Extended Protection for Authentication (EPA) to protect against relay attacks. Audit mode allows to assess the feasibility of this action."

        self.ldap_configuration = requests_results["ldap_server_configuration"]

    def run(self):
        self.ldap_relay_possible = False
        self.ldaps_relay_possible = False
        self.misconfigurations = 0

        page = Page(self.arguments.cache_prefix, "ldap_configuration", "LDAP and LDAPS configuration", self.get_dico_description())
        grid = Grid("LDAP and LDAPS configuration")
        grid.setheaders(["domain", "name", "LDAP available", "LDAP signing", "LDAPS available", "LDAPS EPA", "Relay to LDAP(S)"])

        data = []
        for d in self.ldap_configuration:
            tmp_data = {}
            tmp_data["domain"] = '<i class="bi bi-globe2"></i>' + d["domain"]
            tmp_data["name"] = '<i class="bi bi-hdd-network"></i>' + d["name"]

            if d["ldap"]:
                tmp_data["LDAP available"] = '<i class="bi bi-check-square"></i>LDAP available'
            elif d["ldap"] is not None:
                tmp_data["LDAP available"] = '<i class="bi bi-square"></i>LDAP unavailable'
            else:
                tmp_data["LDAP available"] = "<i class='bi bi-question-circle'></i>Not collected"

            if d["ldapsigning"]:
                tmp_data["LDAP signing"] = '<i class="bi bi-lock-fill text-success"></i>Signing required'
            elif d["ldapsigning"] is not None:
                tmp_data["LDAP signing"] = '<i class="bi bi-unlock-fill text-danger"></i>Signing not required'
            else:
                tmp_data["LDAP signing"] = "<i class='bi bi-question-circle'></i>Not collected"

            if d["ldaps"]:
                tmp_data["LDAPS available"] = '<i class="bi bi-check-square"></i>LDAPS available'
            elif d["ldaps"] is not None:
                tmp_data["LDAPS available"] = '<i class="bi bi-square"></i>LDAPS unavailable'
            else:
                tmp_data["LDAPS available"] = "<i class='bi bi-question-circle'></i>Not collected"

            if d["ldapsepa"]:
                tmp_data["LDAPS EPA"] = '<i class="bi bi-lock-fill text-success"></i>EPA required'
            elif d["ldapsepa"] is not None:
                tmp_data["LDAPS EPA"] = '<i class="bi bi-unlock-fill text-danger"></i>EPA not required'
            else:
                tmp_data["LDAPS EPA"] = "<i class='bi bi-question-circle'></i>Not collected"

            if (d["ldap"] and d["ldapsigning"] is not None and not d["ldapsigning"]) or (d["ldaps"] and d["ldapsepa"] is not None and not d["ldapsepa"]):
                tmp_data["Relay to LDAP(S)"] = '<i class="bi bi-exclamation-diamond-fill text-danger"></i>Relay to LDAP(S) possible'
                self.ldap_relay_possible = True
                self.misconfigurations += 1
            else:
                tmp_data["Relay to LDAP(S)"] = '<i class="bi bi-check-circle-fill text-success"></i>Relay to LDAP(S) impossible'

            data.append(tmp_data)
        grid.setData(data)
        page.addComponent(grid)
        page.render()

        self.data = self.misconfigurations
        self.name_description = f"{self.data} LDAP(S) misconfiguration{'s' if self.data > 1 else ''} allow relay to LDAP"

    def get_rating(self) -> int:
        # -1 = grey, 1 = red, 2 = orange, 3 = yellow, 4 =green, 5 = green,
        if self.ldap_relay_possible or self.ldaps_relay_possible:
            return 1
        else:
            return 5
