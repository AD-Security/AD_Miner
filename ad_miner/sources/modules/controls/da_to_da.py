from ad_miner.sources.modules.controls import Control
from ad_miner.sources.modules.controls import register_control
from ad_miner.sources.modules.page_class import Page
from ad_miner.sources.modules.grid_class import Grid
from ad_miner.sources.modules.graph_class import Graph
from ad_miner.sources.modules.utils import grid_data_stringify
from ad_miner.sources.modules.common_analysis import presence_of

from urllib.parse import quote


@register_control
class da_to_da(Control):
    "Legacy control"

    def __init__(self, arguments, requests_results) -> None:
        super().__init__(arguments, requests_results)

        self.azure_or_onprem = "on_premise"
        self.category = "permissions"
        self.control_key = "da_to_da"

        self.title = "Cross-domain paths to Domain Admin"
        self.description = "From a domain admin group of a given domain, it shows the paths the domain admin groups of every other domains."
        self.risk = "If a path exists between two domains, it means that if the first domain is fully compromised, the second one can quickly be compromised as well. A malicious entity could use these paths to rapidly compromise all domains."
        self.poa = "Review the paths of compromission between domains and remove links if possible."

        self.da_to_da = requests_results["da_to_da"]
        self.collected_domains = requests_results["nb_domain_collected"]

        self.crossDomain = 0

    def run(self):
        # get the result of the cypher request (a list of Path objects)
        paths = self.da_to_da
        # create the page
        page = Page(
            self.arguments.cache_prefix,
            "da_to_da",
            "Cross-domain paths to Domain Admin",
            self.get_dico_description(),
        )
        # create the grid
        grid = Grid("Cross-domain paths to Domain Admin")
        # create the headers (domains)
        headers = []
        # future list of dicts
        pathLengthss = []
        graphDatas = {}
        if paths == None:
            grid.setheaders(["FROM / TO"])
            grid.setData([])
            return
        # for each path
        for domain in self.collected_domains:
            domain = domain[0]
            headers.append(domain)
            graphDatas[domain] = {}
            pathLengthss.append(
                {"FROM / TO": '<i class="bi bi-globe2"></i>' + domain, domain: "-"}
            )
        for path in paths:
            # headers and pathLengths share the same index and it is cheaper to use headers here
            try:
                rowIndex = headers.index(path.nodes[0].name.split("@")[1])
            except ValueError:
                # Dirty fix in case there is a domain missing
                unknown_domain = path.nodes[0].name.split("@")[1]
                headers.append(unknown_domain)
                graphDatas[unknown_domain] = {}
                pathLengthss.append(
                    {
                        "FROM / TO": '<i class="bi bi-globe2"></i>' + unknown_domain,
                        unknown_domain: "-",
                    }
                )
                rowIndex = headers.index(unknown_domain)

            # change value of the cell
            try:
                pathLengthss[rowIndex][path.nodes[-1].name.split("@")[1]] = {
                    "value": pathLengthss[rowIndex][path.nodes[-1].name.split("@")[1]][
                        "value"
                    ]
                    + 1,
                    "link": quote(
                        path.nodes[0].name.split("@")[1]
                        + "_to_"
                        + path.nodes[-1].name.split("@")[1]
                    )
                    + ".html",
                }
            except KeyError:
                pathLengthss[rowIndex][path.nodes[-1].name.split("@")[1]] = {
                    "value": 1,
                    "link": quote(
                        path.nodes[0].name.split("@")[1]
                        + "_to_"
                        + path.nodes[-1].name.split("@")[1]
                    )
                    + ".html",
                }

            # add a path to the list
            try:
                graphDatas[path.nodes[0].name.split("@")[1]][
                    path.nodes[-1].name.split("@")[1]
                ].append(path)
            except KeyError:
                graphDatas[path.nodes[0].name.split("@")[1]][
                    path.nodes[-1].name.split("@")[1]
                ] = [path]

        # fill the grid
        headers.insert(0, "FROM / TO")

        # Add some nice touch to the grid ;)
        for row in pathLengthss:
            # Add some text and icon to cells with links
            for key in row.keys():
                if key == "FROM / TO":
                    continue
                if row[key] == "-":
                    continue
                else:
                    sortClass = str(row[key]["value"]).zfill(6)
                    row[key][
                        "value"
                    ] = f"{row[key]['value']} path{'s' if row[key]['value'] > 1 else ''}"
                    row[key][
                        "before_link"
                    ] = f"<i class='bi bi-sign-turn-right-fill {sortClass}' style='color:#b00404;' aria-hidden='true'></i>"
                    row[key] = grid_data_stringify(row[key])
            # Add some text to empty cells
            for header in headers:
                if header not in row.keys():
                    row[header] = "-"

        grid.setheaders(headers)
        grid.setData(pathLengthss)

        # create pages and graphs for each link
        for inputDomain, outputDomains in graphDatas.items():
            alreadySeenOutputDomains = []
            for outputDomain, paths in outputDomains.items():
                intGraph = Graph()
                # add each path to the graph
                for path in paths:
                    if not (outputDomain in alreadySeenOutputDomains):
                        # found a new domain reachable by the given input domain
                        self.crossDomain += 1
                        # each output domain is added once seen and the list is reset for each new input domain
                        alreadySeenOutputDomains.append(outputDomain)
                    intGraph.addPath(path)
                intPage = Page(
                    self.arguments.cache_prefix,
                    inputDomain + "_to_" + outputDomain,
                    "Paths through Domain Admins between "
                    + inputDomain
                    + " and "
                    + outputDomain,
                    self.get_dico_description(),
                )
                intPage.addComponent(intGraph)
                intPage.render()

        page.addComponent(grid)
        page.render()

        self.data = self.crossDomain
        self.name_description = f"{self.crossDomain} cross-domain paths to Domain Admin"

    def get_rating(self) -> int:
        return presence_of(self.da_to_da)
