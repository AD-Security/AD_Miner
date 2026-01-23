from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.utils import days_format


@register_control
class smb_signing(Control):
    "SMB signing requirements amongst computers"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "misc"
        self.control_key = "smb_signing"

        self.title = "SMB signing requirement"
        self.description = "Computers that do not require SMB signing are vulnerable to relay attacks."
        self.risk = "Not requiring SMB signing on domain controllers could lead to immediate domain compromission through coerced authentication and relay attack."
        self.poa = "Require SMB signing on all computers with a GPO. Prioritize domain controllers or particularly sensitive servers, then other servers and finally workstations. Audit mode can be enabled to check the feasibility of the operation."

        self.smb_signing = requests_results["smb_signing"]

    def run(self):
        self.dc_without_signing = False
        self.server_without_signing = False
        self.workstation_without_signing = False

        page = Page(self.arguments.cache_prefix, "smb_signing", "SMB signing", self.get_dico_description())
        grid = Grid("SMB signing")
        grid.setheaders(["domain", "name", "type", "last logon", "signing"])
        data = []
        for d in self.smb_signing:
            tmp_data = {}
            tmp_data["domain"] = '<i class="bi bi-globe2"></i>' + d["domain"]
            tmp_data["name"] = '<i class="bi bi-cpu"></i>' + d["name"]
            if d["dc"]:
                tmp_data["type"] = '<i class="bi bi-gem"></i>Domain Controller'
                tmp_data["order2"] = 0
                if not self.dc_without_signing and d["smbsigning"] is not None and not d["smbsigning"]:
                    self.dc_without_signing = True
            elif d["server"]:
                tmp_data["type"] = "<i class='bi bi-hdd-network'></i>Server"
                tmp_data["order2"] = 1
                if not self.server_without_signing and d["smbsigning"] is not None and not d["smbsigning"]:
                    self.server_without_signing = True
            else:
                tmp_data["type"] = "<i class='bi bi-laptop'></i>Workstation"
                tmp_data["order2"] = 2
                if not self.workstation_without_signing and d["smbsigning"] is not None and not d["smbsigning"]:
                    self.workstation_without_signing = True
            tmp_data["last logon"] = days_format(d["lastlogontimestamp"])
            if d["smbsigning"] is None:
                tmp_data["signing"] = "<i class='bi bi-question-circle'></i>Not collected"
                tmp_data["order"] = 2
            elif d["smbsigning"]:
                tmp_data["signing"] = '<i class="bi bi-lock-fill text-success"></i>Signing required'
                tmp_data["order"] = 1
            else:
                tmp_data["signing"] = '<i class="bi bi-unlock-fill text-danger"></i>Signing not required'
                tmp_data["order"] = 0
            data.append(tmp_data)
        sorted_data = sorted(data, key=lambda x: x["order2"])
        sorted_sorted_data = sorted(sorted_data, key=lambda x: x["order"])
        grid.setData(sorted_sorted_data)
        page.addComponent(grid)
        page.render()

        self.data = len([c for c in self.smb_signing if c["smbsigning"] is not None and not c["smbsigning"]])
        self.name_description = f"{self.data} computer{'s' if self.data > 1 else ''} without SMB signing requirement"

    def get_rating(self) -> int:
        # -1 = grey, 1 = red, 2 = orange, 3 = yellow, 4 =green, 5 = green,
        if self.dc_without_signing:
            return 1
        elif self.server_without_signing:
            return 2
        elif self.workstation_without_signing:
            return 3
        return 5
