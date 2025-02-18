from ad_miner.sources.modules import logger
from ad_miner.sources.modules.utils import CONFIG_MAP, days_format
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules.path_neo4j import Path
from ad_miner.sources.modules.node_neo4j import Node
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules import generic_computing


import re
import datetime
import time

obsolete_os_list = [
    "Windows XP",
    "Windows 7",
    "Windows 2000",
    "Windows 2003",
    "Windows 2008",
    "Windows 2008R2",
    "Windows 2012",
    "Windows 2012R2",
]


def getUserComputersCountPerDomain(requests_results):
    domains = requests_results["domains"]

    if domains is None:
        logger.print_error(" self.domains is None")
        return ["Domain is None", 0, 0]

    result = []
    users = requests_results["nb_enabled_accounts"]
    computers = requests_results["nb_computers"]

    for domain in domains:
        domain = domain[0]
        nb_user = len(
            [
                element
                for element in users
                if domain.upper() == element["domain"].upper()
            ]
        )  # Inclusion because of the icon. Space to check that it's the full domain name.
        nb_computer = len(
            [element for element in computers if element["domain"] == domain]
        )
        result.append([domain, nb_user, nb_computer])
    return result


def manageComputersOs(computer_list):
    if computer_list is None:
        return None
    all_os = {}
    computers_os_obsolete = []

    for line in computer_list:
        os = line["os"]
        if "windows" in os.lower():
            os = os.lower()
            os = os.replace("\xa0", " ")
            os = os.replace("®", "")
            os = os.replace(" server", "")
            os = os.replace(" storage", "")
            os = os.replace(" 2008 r2", " 2008R2")
            os = os.replace(" 2012 r2", " 2012R2")
            ver = re.match(r"^windows ([.a-zA-Z0-9]+)\s", os, re.M | re.I)
            if ver:
                os = "Windows " + ver.group(1).upper()
            else:
                os = os.replace("windows", "Windows")
        else:
            os = os

        # Cleaner way to do a try/except for dictionaries is to use get() :
        lastLogon = line.get("lastLogon", "Not specified")
        final_line = {
            "Domain": line["domain"],
            "name": line["name"],
            "Operating system": os,
            "Last logon in days": lastLogon,
        }

        # Stats for OS repartition
        def addToOS(key):
            if all_os.get(key):
                all_os[key] += 1
            else:
                all_os[key] = 1

        if "windows" in os.lower():
            addToOS(os)
        elif "linux" in os.lower() or "ubuntu" in os.lower():
            addToOS("Linux")
        elif "mac" in os.lower():
            addToOS("MacOS")
        elif "android" in os.lower():
            addToOS("Android")
        elif "ios" in os.lower():
            addToOS("iOS")
        else:
            addToOS("Other")

        if os in obsolete_os_list:
            computers_os_obsolete.append(final_line)
    return computers_os_obsolete, all_os


def rating_color(total_rating):
    # total_rating = rating(users, domains, computers, objects, arguments)
    dico_rating_color = {"on_premise": {}, "azure": {}}

    conf = CONFIG_MAP["requests"]
    for category_repartition in ["on_premise", "azure"]:
        for notation in total_rating[category_repartition]:
            for indicator in total_rating[category_repartition][notation]:
                if notation == 1:
                    color = "red"
                elif notation == 2:
                    color = "orange"
                elif notation == 3:
                    color = "yellow"
                elif notation == 4 or notation == 5:
                    color = "green"
                else:
                    color = "grey"

                # Check if control is disabled in config.json. If so, color = grey
                try:
                    disabled = conf.get(indicator) == "false"
                except KeyError:
                    disabled = False
                if disabled:
                    color = "grey"

                dico_rating_color[category_repartition][indicator] = color

    return dico_rating_color


# PERCENTAGE SUP FUNCTION
# If no presence argument : return criticity if > percentage
# If presence argument : return criticity if > percentage, criticity+1 if there at least one
def percentage_superior(req, base, criticity=1, percentage=0, presence=False):
    if req is None:
        return -1
    if base is None:
        return -1
    if len(base) == 0:
        return -1

    if len(base) and len(req) / len(base) > percentage:
        return criticity

    if presence:
        if len(req) > 0:
            return criticity + 1
    return 5


# PERCENTAGE INF FUNCTION
# return criticity if < percentage, criticity - 1 if < percentage/2
def percentage_inferior(req, base, criticity=1, percentage=0):
    if req is None:
        return -1
    if base is None:
        return -1
    if len(base) == 0:
        return -1

    if len(base) and len(req) / len(base) < percentage:
        return criticity

    if len(base) and len(req) / len(base) < percentage / 2:
        return criticity - 1

    return 5


# PRESENCE FUNCTION
# Return criticity if at least one, 5 if not
def presence_of(req, criticity=1, threshold=0):
    if req is None:
        return -1
    if len(req) > threshold:
        return criticity
    return 5


# TIME SINCE EXTRACT FUNCTION
# return criticity if time since > age, 5 if not
def time_since_extraction_date(req, extimestamp=0, age=90, criticity=1):
    if req is None:
        return -1

    year = int(extimestamp[0:4])
    month = int(extimestamp[4:6])
    day = int(extimestamp[6:8])
    date_time = datetime.datetime(year, month, day)
    extraction_date = time.mktime(date_time.timetuple())
    days_since = (extraction_date - req) / 86400

    if days_since > age:
        return criticity

    return 5


# TIME SINCE FUNCTION
# return criticity if time since > age, 5 if not
def time_since(req, age=90, criticity=1):  # req as days
    if req is None:
        return -1
    if req > age:
        return criticity

    return 5


# CONTAINS DA FUNCTION
# return criticity if at least one DA, 5 if not
def containsDAs(req, criticity=1):
    if req is None:
        return -1

    for object in req:
        if object.get("is_Domain_Admin"):
            if object["is_Domain_Admin"] == True:
                return criticity
        # if object.get("is_da"):
        #     if object["is_da"] == True:
        #         return criticity

    if len(req) > 0:
        return criticity + 1

    return 5


def parseConstrainedData(list_of_dict):
    final_dict = {}
    for dict in list_of_dict:
        if dict["name"] in final_dict.keys():
            final_dict[dict["name"]] += [dict["computer"]]
        else:
            final_dict[dict["name"]] = [dict["computer"]]
    return final_dict


def createGraphPage(
    render_prefix, page_name, page_title, page_description, graph_data, requests_results
):
    page = Page(render_prefix, page_name, page_title, page_description)
    graph = Graph()
    graph.setPaths(graph_data)

    graph.addGhostComputers(requests_results["dico_ghost_computer"])
    graph.addGhostUsers(requests_results["dico_ghost_user"])
    graph.addDCComputers(requests_results["dico_dc_computer"])
    graph.addUserDA(requests_results["dico_user_da"])
    graph.addGroupDA(requests_results["dico_da_group"])
    graph.addKerberoastableUsers(requests_results["dico_is_kerberoastable"])

    page.addComponent(graph)
    page.render()


def findAndCreatePathToDaFromUsersList(
    requests_results, arguments, admin_user, computers
):
    users_to_domain_admin = requests_results["users_to_domain_admin"]
    computers_to_domain_admin = requests_results["computers_to_domain_admin"]
    if users_to_domain_admin is None:
        return 0, 0
    path_to_generate = []
    # node_to_add = Node(id=42424243, labels="User",
    #                    name=admin_user, domain="start")
    list_domain = []

    dico_description_computers_path_to_da = {
        "description": "All compromission paths from computers to domain administrators.",
        "risk": "This graph shows all the paths that an attacker could take to become domain admin if they had compromised a computer. These paths show potential privilege escalation paths in the domain. If an attacker compromises a computer, he could use these paths to become domain admin.",
        "poa": "Review these paths and make sure that they are not exploitable. Cut some of the links between the Active Directory objects by changing configuration in order to reduce the number of possible paths.",
    }

    for paths in computers_to_domain_admin.values():
        for path in paths:
            if path.nodes[0].name in computers:
                # if path.start_node.name in computers:
                node_to_add = Node(
                    id=42424243,
                    labels="User",
                    name=admin_user,
                    domain="start",
                    tenant_id=None,
                    relation_type="AdminTo",
                )
                # relation = Relation(
                #     id=88888, nodes=[node_to_add, path.start_node], type="AdminTo"
                # )
                new_nodes = path.nodes.copy()
                new_nodes.insert(0, node_to_add)
                new_path = Path(new_nodes)
                path_to_generate.append(new_path)
                if new_path.nodes[-1].domain not in list_domain:
                    list_domain.append(path.nodes[-1].domain)
    if len(path_to_generate):
        createGraphPage(
            arguments.cache_prefix,
            "users_path_to_da_from_%s" % admin_user,
            "Path to domain admins",
            dico_description_computers_path_to_da,
            path_to_generate,
            requests_results,
        )
    return (len(path_to_generate), len(list_domain))


def hasPathToDA(
    req, criticity=1
):  # ne marche que partiellement : besoin de rajouter l'attribut has_path_to_DA dans toutes les requêtes pertinentes + dans domains.py/findAndCreatePathToDaFromComputersList
    if req is None:
        return -1

    for object in req:
        # print(object)
        if not object.get("has_path_to_da"):
            continue
        if object["has_path_to_da"] == True:
            # print(object)
            return criticity

    if len(req) > 0:
        return criticity + 1

    return 5


def findAndCreatePathToDaFromComputersList(
    requests_results, arguments, admin_computer, computers
) -> tuple([int, int]):
    """
    Returns the number of path to DA from admin_computer and the number of domains impacted
    """
    dico_description_computers_path_to_da = {
        "description": "All compromission paths from computers to domain administrators.",
        "risk": "This graph shows all the paths that an attacker could take to become domain admin if they had compromised a computer. These paths show potential privilege escalation paths in the domain. If an attacker compromises a computer, he could use these paths to become domain admin.",
        "poa": "Review these paths and make sure that they are not exploitable. Cut some of the links between the Active Directory objects by changing configuration in order to reduce the number of possible paths.",
    }

    computers_to_domain_admin = requests_results["computers_to_domain_admin"]
    if computers_to_domain_admin is None:
        logger.print_error(" self.computers_to_domain_admin is None")
        return 0, 0
    path_to_generate = []

    domains = []

    for paths in computers_to_domain_admin.values():
        for path in paths:
            domains.append(path.nodes[-1].domain)

            if path.nodes[0].name in computers:
                # relation = Relation(
                #     id=88888, nodes=[node_to_add, path.nodes[0]], type="Relay"
                # )
                node_to_add = Node(
                    id=42424243,
                    labels="Computer",
                    name=admin_computer,
                    domain="start",
                    tenant_id=None,
                    relation_type="Relay",
                )
                new_nodes = path.nodes.copy()
                new_nodes.insert(0, node_to_add)
                new_path = Path(new_nodes)
                path_to_generate.append(new_path)
    if len(path_to_generate):
        createGraphPage(
            arguments.cache_prefix,
            "computers_path_to_da_from_%s" % admin_computer,
            "Path to domain admins",
            dico_description_computers_path_to_da,
            path_to_generate,
            requests_results,
        )
    return len(path_to_generate), len(list(set(domains)))


def get_dico_admin_of_computer_id(requests_results):
    get_users_linked_admin_group = requests_results["get_users_linked_admin_group"]
    get_groups_linked_admin_group = requests_results["get_groups_linked_admin_group"]
    get_computers_linked_admin_group = requests_results[
        "get_computers_linked_admin_group"
    ]
    get_users_direct_admin = requests_results["get_users_direct_admin"]
    users_admin_on_computers = requests_results["users_admin_on_computers"]

    dico_admin_of_computer_id = {}

    for couple in get_users_linked_admin_group:
        u = couple["u"]

        dico_admin_of_computer_id[u["name"]] = couple["idu"]

    for couple in get_groups_linked_admin_group:
        g = couple["g"]

        dico_admin_of_computer_id[g["name"]] = couple["idg"]

    for couple in get_computers_linked_admin_group:
        g = couple["g"]

        dico_admin_of_computer_id[g["name"]] = couple["idg"]

    for couple in get_users_direct_admin:
        g = couple["g"]

        dico_admin_of_computer_id[g["name"]] = couple["idg"]

    for d in users_admin_on_computers:
        dico_admin_of_computer_id[d["user"]] = d["user_id"]

    return dico_admin_of_computer_id


def manage_plural(elem, text):
    "Used to add an s if plural (e.g. text = ['computer', 'computers'])"
    if elem > 1:
        return text[1]
    return text[0]


def generateDomainMapTrust(requests_results, arguments):
    domain_map_trust = requests_results["domain_map_trust"]
    domains_list = requests_results["domains"]

    dico_description_domain_map_trust = {
        "description": "Visual map of the existing domains and their trust relationship.",
        "risk": "Unnecessary trusts between domain will at least provide visibility (e.g., capacity to enumerate domain objects in an attemps to determine attack path).",
        "poa": "Review existing trusts and make sure that these are justified for operations.",
    }

    if domain_map_trust is None:
        return

    if domain_map_trust == []:
        # Add empty graph with the domains when no trust returned
        path_list = list()
        for i in range(len(domains_list)):
            domain_name = domains_list[i][0]
            id, labels, tenant_id, relation_type = i, "Domain", 0, None
            path_list.append(
                Path(
                    [
                        Node(
                            id,
                            labels,
                            domain_name,
                            domain_name,
                            tenant_id,
                            relation_type,
                        )
                    ]
                )
            )

        createGraphPage(
            arguments.cache_prefix,
            "domain_map_trust",
            "Map trust of domains ",
            dico_description_domain_map_trust,
            path_list,
            requests_results,
        )
        return

    createGraphPage(
        arguments.cache_prefix,
        "domain_map_trust",
        "Map trust of domains ",
        dico_description_domain_map_trust,
        domain_map_trust,
        requests_results,
    )


def genNumberOfDCPage(requests_results, arguments):
    computers_nb_domain_controllers = requests_results["nb_domain_controllers"]
    dico_name_description_nb_domain_controllers = {
        "description": "Domain controllers are the central servers of AD and provide multiple services to support the AD infrastructure.",
        "interpretation": "This control is rather informational and is meant to point which computers act as domain controllers.",
        "risk": "N/A",
        "poa": "N/A",
    }

    if computers_nb_domain_controllers is None:
        return
    page = Page(
        arguments.cache_prefix,
        "nb_domain_controllers",
        "List of domain controllers",
        dico_name_description_nb_domain_controllers,
    )
    grid = Grid("List of domain controllers")
    grid.setheaders(["domain", "name", "os", "last logon"])

    data = []

    computers_nb_domain_controllers = sorted(
        computers_nb_domain_controllers, key=lambda x: x["ghost"], reverse=True
    )

    for d in computers_nb_domain_controllers:
        temp_data = {}
        temp_data["domain"] = '<i class="bi bi-globe2"></i> ' + d["domain"]
        if d["ghost"]:
            temp_data["name"] = (
                '<svg height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><path fill="#ff595e" d="M40.1 467.1l-11.2 9c-3.2 2.5-7.1 3.9-11.1 3.9C8 480 0 472 0 462.2V192C0 86 86 0 192 0S384 86 384 192V462.2c0 9.8-8 17.8-17.8 17.8c-4 0-7.9-1.4-11.1-3.9l-11.2-9c-13.4-10.7-32.8-9-44.1 3.9L269.3 506c-3.3 3.8-8.2 6-13.3 6s-9.9-2.2-13.3-6l-26.6-30.5c-12.7-14.6-35.4-14.6-48.2 0L141.3 506c-3.3 3.8-8.2 6-13.3 6s-9.9-2.2-13.3-6L84.2 471c-11.3-12.9-30.7-14.6-44.1-3.9zM160 192a32 32 0 1 0 -64 0 32 32 0 1 0 64 0zm96 32a32 32 0 1 0 0-64 32 32 0 1 0 0 64z"/></svg> '
                + d["name"]
            )
        else:
            temp_data["name"] = '<i class="bi bi-server"></i> ' + d["name"]
        if "WINDOWS" in d["os"].upper():
            temp_data["os"] = '<i class="bi bi-windows"></i> ' + d["os"]
        temp_data["last logon"] = days_format(d["lastLogon"])
        data.append(temp_data)
    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genUsersListPage(requests_results, arguments):
    users = requests_results["nb_enabled_accounts"]
    users_nb_domain_admins = requests_results["nb_domain_admins"]
    dico_name_description_users = {
        "description": "List of all users on any domain",
        "risk": "N/A",
        "poa": "This control is rather informational and shall help getting a better understanding of the current objects.",
    }

    admin_list = []
    for admin in users_nb_domain_admins:
        admin_list.append(admin["name"])

    if users is None:
        return

    page = Page(
        arguments.cache_prefix,
        "users",
        "List of all users",
        dico_name_description_users,
    )
    grid = Grid("Users")
    grid.setheaders(["domain", "name", "last logon"])
    data = []
    for user in users:
        tmp_dict = {}
        tmp_dict["domain"] = '<i class="bi bi-globe2"></i> ' + user["domain"]
        # Add admin icon
        if user["name"] in admin_list:
            tmp_dict["name"] = (
                '<i class="bi bi-gem" title="This user is domain admin"></i> '
                + user["name"]
            )
        else:
            tmp_dict["name"] = '<i class="bi bi-person-fill"></i> ' + user["name"]
        # Add calendar icon
        logon = -1
        if user.get("logon"):
            logon = user["logon"]
        tmp_dict["last logon"] = days_format(logon)
        data.append(tmp_dict)
    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAllGroupsPage(requests_results, arguments):
    groups = requests_results["nb_groups"]
    dico_name_description_groups = {
        "description": "List of all groups on any domain",
        "risk": "N/A",
        "poa": "This control is rather informational and shall help getting a better understanding of the current objects.",
    }

    if groups is None:
        return
    page = Page(
        arguments.cache_prefix,
        "groups",
        "List of all groups",
        dico_name_description_groups,
    )
    grid = Grid("Groups")
    grid.setheaders(["domain", "name"])
    group_extract = [
        {
            "domain": '<i class="bi bi-globe2"></i> ' + groups[k]["domain"],
            "name": (
                '<i class="bi bi-gem" title="This group is domain admin"></i> '
                + groups[k]["name"]
                if groups[k].get("da")
                else '<i class="bi bi-people-fill"></i> ' + groups[k]["name"]
            ),
        }
        for k in range(len(groups))
    ]
    grid.setData(group_extract)
    page.addComponent(grid)
    page.render()


def generateComputersListPage(requests_results, arguments):

    dico_name_description_computers = {
        "description": "List of all computers on any domain.",
        "interpretation": "This control is rather informational and shall help confirming the current extent of the computer objects within the domain.",
        "risk": "N/A",
        "poa": "N/A",
    }
    list_total_computers = requests_results["nb_computers"]

    if list_total_computers is None:
        return
    page = Page(
        arguments.cache_prefix,
        "computers",
        "List of all computers",
        dico_name_description_computers,
    )
    grid = Grid("Computers")
    data = []
    for computer in list_total_computers:
        # Check if computer is ghost computer
        if computer["ghost"]:
            name = (
                '<svg height="15px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 512"><path d="M40.1 467.1l-11.2 9c-3.2 2.5-7.1 3.9-11.1 3.9C8 480 0 472 0 462.2V192C0 86 86 0 192 0S384 86 384 192V462.2c0 9.8-8 17.8-17.8 17.8c-4 0-7.9-1.4-11.1-3.9l-11.2-9c-13.4-10.7-32.8-9-44.1 3.9L269.3 506c-3.3 3.8-8.2 6-13.3 6s-9.9-2.2-13.3-6l-26.6-30.5c-12.7-14.6-35.4-14.6-48.2 0L141.3 506c-3.3 3.8-8.2 6-13.3 6s-9.9-2.2-13.3-6L84.2 471c-11.3-12.9-30.7-14.6-44.1-3.9zM160 192a32 32 0 1 0 -64 0 32 32 0 1 0 64 0zm96 32a32 32 0 1 0 0-64 32 32 0 1 0 0 64z"/></svg> '
                + computer["name"]
            )
        else:
            name = '<i class="bi bi-pc-display"></i> ' + computer["name"]
        # OS
        if computer["os"]:
            os = computer["os"]
            if "windows" in computer["os"].lower():
                os = '<i class="bi bi-windows"></i> ' + os
            elif "mac" in computer["os"].lower():
                os = '<i class="bi bi-apple"></i> ' + os
            else:
                os = '<i class="bi bi-terminal-fill"></i> ' + os
        else:
            os = "Unknown"
        formated_computer = {
            "domain": '<i class="bi bi-globe2"></i> ' + computer["domain"],
            "name": name,
            "operating system": os,
        }
        data.append(formated_computer)
    grid.setheaders(["domain", "name", "operating system"])
    grid.setData(data)
    page.addComponent(grid)
    page.render()


def generateADCSListPage(requests_results, arguments):
    dico_name_description_adcs = {
        "title": "ADCS servers",
        "description": "ADCS (Active Directory Certificate Services) is a Windows Server feature that provides a customizable certification authority (CA) for issuing and managing digital certificates. Digital certificates are used to authenticate and secure communication between devices, servers, and users on a network.",
        "interpretation": "",
        "risk": "",
        "poa": "",
    }
    computers_adcs = requests_results["set_is_adcs"]

    if computers_adcs is None:
        return
    page = Page(
        arguments.cache_prefix,
        "adcs",
        "List of all ADCS servers",
        dico_name_description_adcs,
    )
    grid = Grid("ADCS servers")
    grid.setheaders(["domain", "name"])
    for adcs in computers_adcs:
        adcs["domain"] = '<i class="bi bi-globe2"></i> ' + adcs["domain"]
        adcs["name"] = '<i class="bi bi-server"></i> ' + adcs["name"]
    grid.setData(computers_adcs)
    page.addComponent(grid)
    page.render()


tenant_id_name = {
    "F8CDEF31-A31E-4B4A-93E4-5F571E91255A": "Microsoft Entra",
    None: "Unknown",
}


def setTenantIDName(requests_results, arguments):
    azure_tenants = requests_results["azure_tenants"]
    for tenant in azure_tenants:
        tenant_id_name[tenant["ID"]] = tenant["Name"]  # Associe l'ID au nom du tenant

    return tenant_id_name


def genAzureTenants(requests_results, arguments):
    azure_tenants = requests_results["azure_tenants"]
    dico_name_description_azure_tenants = {
        "title": "Azure Tenants",
        "description": "List of all Azure Tenants",
        "risk": "",
        "poa": "",
    }
    if azure_tenants is None:
        return

    page = Page(
        arguments.cache_prefix,
        "azure_tenants",
        "List of all Azure Tenants",
        dico_name_description_azure_tenants,
    )
    grid = Grid("Azure Tenants")

    data = []
    for tenant in azure_tenants:
        data.append(
            {
                "Tenant ID": '<i class="bi bi-file-earmark-person"></i> '
                + tenant["ID"],
                "Tenant Name": '<i class="bi bi-globe2"></i> ' + tenant["Name"],
            }
        )

    grid.setheaders(["Tenant ID", "Tenant Name"])

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAzureUsers(requests_results, arguments):
    azure_users = requests_results["azure_user"]
    name_description_azure_users = {
        "title": "Azure users",
        "description": "Exhaustive list of all users in the Azure tenant",
        "risk": "",
        "poa": "",
    }

    if azure_users is None:
        return

    setTenantIDName(requests_results, arguments)

    page = Page(
        arguments.cache_prefix,
        "azure_users",
        "List of all Azure users",
        name_description_azure_users,
    )
    grid = Grid("Azure Users")

    data = []
    for user in azure_users:
        tenant_id = user.get("Tenant ID")
        tenant_name = tenant_id_name.get(tenant_id, tenant_id)
        data.append(
            {
                "Tenant Name": '<i class="bi bi-globe2"></i> ' + tenant_name,
                "Name": '<i class="bi bi-person-fill"></i> ' + user["Name"],
                "Synced on premise": (
                    '<i class="bi bi-check-square"></i>'
                    if user["onpremisesynced"] == True
                    else '<i class="bi bi-square"></i>'
                ),
                "On premise SID": (
                    user["SID"]
                    if user["onpremisesynced"] == True and user["SID"] != None
                    else "-"
                ),
            }
        )

    grid.setheaders(["Tenant Name", "Name", "Synced on premise", "On premise SID"])

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAzureAdmin(requests_results, arguments):
    azure_admin = requests_results["azure_admin"]
    dico_name_description_azure_admin = {
        "title": "Azure administrators",
        "description": "List of all Global Admins in the Azure tenant",
        "risk": "",
        "poa": "",
    }

    if azure_admin is None:
        return

    setTenantIDName(requests_results, arguments)

    page = Page(
        arguments.cache_prefix,
        "azure_admin",
        "List of all Azure Global Admins",
        dico_name_description_azure_admin,
    )
    grid = Grid("Azure Admin")

    data = []
    for admin in azure_admin:
        tenant_id = admin.get("Tenant ID")
        tenant_name = tenant_id_name.get(tenant_id, tenant_id)
        data.append(
            {
                "Tenant Name": '<i class="bi bi-globe2"></i> ' + tenant_name,
                "Name": '<i class="bi bi-gem"></i> ' + admin["Name"],
            }
        )

    grid.setheaders(["Tenant Name", "Name"])

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAzureGroups(requests_results, arguments):
    azure_groups = requests_results["azure_groups"]
    dico_name_description_azure_groups = {
        "title": "Azure groups",
        "description": "List of all groups in the Azure tenant",
        "risk": "",
        "poa": "",
    }

    if azure_groups is None:
        return

    setTenantIDName(requests_results, arguments)

    page = Page(
        arguments.cache_prefix,
        "azure_groups",
        "List of all Azure groups",
        dico_name_description_azure_groups,
    )
    grid = Grid("Azure Groups")

    data = []
    for group in azure_groups:
        tenant_id = group.get("Tenant ID")
        tenant_name = tenant_id_name.get(tenant_id, tenant_id)
        data.append(
            {
                "Tenant Name": '<i class="bi bi-globe2"></i> ' + tenant_name,
                "Name": '<i class="bi bi-people-fill"></i> ' + group["Name"],
                "Description": group["Description"],
            }
        )

    grid.setheaders(["Tenant Name", "Name", "Description"])

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAzureVM(requests_results, arguments):
    dico_name_description_azure_vm = {
        "title": "Azure virtual machines",
        "description": "List of all virtual machines in the Azure tenant",
        "risk": "",
        "poa": "",
    }
    azure_vm = requests_results["azure_vm"]

    if azure_vm is None:
        return

    setTenantIDName(requests_results, arguments)

    page = Page(
        arguments.cache_prefix,
        "azure_vm",
        "List of all Azure VM",
        dico_name_description_azure_vm,
    )
    grid = Grid("Azure VM")

    grid.setheaders(["Tenant Name", "Name", "Operating System"])

    data = []
    for dict in azure_vm:
        tenant_id = dict.get("Tenant ID")
        tenant_name = tenant_id_name.get(tenant_id, tenant_id)
        tmp_data = {"Tenant Name": tenant_name}

        tmp_data["Name"] = dict["Name"]

        # os
        if dict.get("os"):
            os = dict["os"]
            if "windows" in dict["os"].lower():
                os = '<i class="bi bi-windows"></i> ' + os
            elif "mac" in dict["os"].lower():
                os = '<i class="bi bi-apple"></i> ' + os
            else:
                os = '<i class="bi bi-terminal-fill"></i> ' + os
        else:
            os = "Unknown"

        tmp_data["Operating System"] = os

        data.append(tmp_data)

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAzureDevices(requests_results, arguments):
    dico_name_description_azure_devices = {
        "title": "Azure Devices",
        "description": "List of all enrolled devicess in the Azure tenants",
        "risk": "",
        "poa": "",
    }
    azure_devices = requests_results["azure_devices"]
    if azure_devices is None:
        return

    setTenantIDName(requests_results, arguments)

    page = Page(
        arguments.cache_prefix,
        "azure_devices",
        "List of all Azure devices",
        dico_name_description_azure_devices,
    )
    grid = Grid("Azure Devices")

    grid.setheaders(["Tenant Name", "Name", "Operating System"])

    data = []
    for dict in azure_devices:
        tenant_id = dict.get("Tenant ID")
        tenant_name = tenant_id_name.get(tenant_id, tenant_id)

        tmp_data = {"Tenant Name": tenant_name}

        tmp_data["Name"] = dict["Name"]

        # os
        if dict.get("os"):
            os = dict["os"]
            if "windows" in dict["os"].lower():
                os = '<i class="bi bi-windows"></i> ' + os
            elif (
                "mac" in dict["os"].lower()
                or "iphone" in dict["os"].lower()
                or "ios" in dict["os"].lower()
            ):
                os = '<i class="bi bi-apple"></i> ' + os
            elif "android" in dict["os"].lower():
                os = '<i class="bi bi-android"></i> ' + os
            else:
                os = '<i class="bi bi-terminal-fill"></i> ' + os
        else:
            os = "Unknown"

        tmp_data["Operating System"] = os

        data.append(tmp_data)

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def genAzureApps(requests_results, arguments):
    dico_name_description_azure_apps = {
        "title": "Azure Apps",
        "description": "List of all applications in the Azure tenants",
        "risk": "",
        "poa": "",
    }
    azure_apps = requests_results["azure_apps"]

    if azure_apps is None:
        return

    setTenantIDName(requests_results, arguments)

    page = Page(
        arguments.cache_prefix,
        "azure_apps",
        "List of all Azure applications",
        dico_name_description_azure_apps,
    )
    grid = Grid("Azure Applications")

    grid.setheaders(["Tenant ID", "Name"])

    data = []
    data_microsft = []

    for app in azure_apps:
        tenant_id = app.get("Tenant ID")
        tenant_name = tenant_id_name.get(tenant_id, tenant_id)

        if tenant_id == "F8CDEF31-A31E-4B4A-93E4-5F571E91255A":
            data_microsft.append(
                {
                    "Tenant ID": '<i class="bi bi-globe2"></i> ' + tenant_name,
                    "Name": '<i class="bi bi-window-sidebar"></i> ' + app["Name"],
                }
            )
        else:
            data.append(
                {
                    "Tenant ID": '<i class="bi bi-globe2"></i> ' + tenant_name,
                    "Name": '<i class="bi bi-window-sidebar"></i> ' + app["Name"],
                }
            )
    data += data_microsft

    grid.setData(data)
    page.addComponent(grid)
    page.render()


def get_interest(requests_results, target_label: str, name: str) -> int:
    """Common function to compute the interest of an object.
    Used in ACL anomalies, Path to OU, etc.
    The rating should be:
    3 stars: object is tier 0
    2 stars: object has a path to DA / tier 0
    1 star: object has local admin privileges over a computer
    0 star: other objects

    Returns an int (0, 1, 2 or 3 stars)
    """
    admin_list = requests_results["admin_list"]
    dico_is_user_admin_on_computer = requests_results["dico_is_user_admin_on_computer"]

    dico_users_to_da = requests_results["dico_users_to_da"]
    dico_computers_to_da = requests_results["dico_computers_to_da"]
    dico_groups_to_da = requests_results["dico_groups_to_da"]
    dico_ou_to_da = requests_results["dico_ou_to_da"]
    dico_gpo_to_da = requests_results["dico_gpo_to_da"]

    computers_admin_to_count = requests_results["computers_admin_to_count"]

    interest = 0
    if target_label == "User":
        if name in admin_list:
            interest = max(3, interest)
        if name in dico_is_user_admin_on_computer:
            interest = max(1, interest)
        if name in dico_users_to_da:
            interest = max(2, interest)

    elif target_label == "Group":
        if name in dico_groups_to_da:
            interest = max(2, interest)

    elif target_label == "Computer":
        if name in dico_computers_to_da:
            interest = max(2, interest)
        if name in computers_admin_to_count:
            interest = max(1, interest)

    elif target_label == "OU":
        if name in dico_ou_to_da:
            interest = max(2, interest)

    elif target_label == "Container":
        interest = interest  # TODO

    elif target_label == "GPO":
        if name in dico_gpo_to_da:
            interest = max(2, interest)

    elif target_label == "CertTemplate":
        interest = max(3, interest)

    elif target_label == "Domain":
        interest = max(3, interest)

    elif target_label == "EnterpriseCA":
        interest = max(3, interest)  # TODO verif

    elif target_label == "IssuancePolicy":
        interest = max(3, interest)  # TODO verif

    elif target_label == "AIACA":
        interest = max(3, interest)  # TODO verif

    elif target_label == "NTAuthStore":
        interest = max(3, interest)  # TODO verif

    elif target_label == "RootCA":
        interest = max(3, interest)  # TODO verif

    else:
        logger.print_warning(
            f"Label {target_label} is unknown by the interest rating function and will not be analyzed."
        )
    return interest
