# row format : {key1 : {"value": value, "link":link}, key2 : value2}
from ad_miner.sources.modules.utils import HTML_DIRECTORY
from ad_miner.sources.modules import logger

import json
import os


class Grid:
    def __init__(self, title, template="grid", classes="thead-light"):
        self.template_base_path = HTML_DIRECTORY / "components/grid/"
        self.title = title
        self.template = template
        self.headers = []
        self.data = ""
        self.class_css = classes

    def addheader(self, header):
        self.headers.append(header)

    def setheaders(self, header):
        self.headers = header

    def getHeaders(self):
        return self.headers

    def setData(self, data):
        self.data = data

    def render(self, page_f):
        with open(self.template_base_path / (self.template + "_template.html"), "r") as grid_template:
            # Grid data that will be inserted in the template
            textToInsert = "var columnDefs = ["
            for header in self.headers:
                textToInsert += """{
                    field:\"%s\",
                    cellRenderer: function(params) {
                        if (typeof params.data[params.column.colId] === 'object') {
                            if (params.data[params.column.colId].value == \"0\") {
                                return params.data[params.column.colId].value;
                            }
                            if (params.data[params.column.colId].link == 'FALSE_LINK') {
                                params.data[params.column.colId] = '<p>' + params.data[params.column.colId].value + '</p>';
                                return params.data[params.column.colId];
                            }
                            if (params.data[params.column.colId].link != null) {
                                if (params.data[params.column.colId].before_link != null) {
                                    var prepend = params.data[params.column.colId].before_link;
                                }
                                else {
                                    var prepend = "";
                                }
                                params.data[params.column.colId] = prepend + '<a onMouseOver="this.style.color=#99c3ff" onMouseOut="this.style.color=#000" href="' + params.data[params.column.colId].link + '">'+ params.data[params.column.colId].value + '</a>';
                                return params.data[params.column.colId];
                            }
                            return params.data[params.column.colId];
                        }
                        else {
                            return params.value;
                        }
                    },
                },""" % (
                    header
                )

            textToInsert = textToInsert + "];\nvar rowData=%s;\n" % (self.data)

            template_contents = grid_template.read()

            new_contents = template_contents.replace("// DATA PLACEHOLDER", textToInsert)

            page_f.write(new_contents)

    def writeEvolutionJSON(self, render_prefix, grid_key, data):
        evolution_folder = os.path.join(".", "evolution_data")
        os.makedirs(evolution_folder, exist_ok=True)

        evolution_json_path = os.path.join(
            evolution_folder, render_prefix + "_grid_" + grid_key
        )

        with open(evolution_json_path, "w") as f:
            f.write(json.dumps(data, indent=4))

    def AddNewIconsToNewLines(self, previous_render_prefix, grid_key, column):
        # Skip if no previous render prefix was created
        if previous_render_prefix == "":
            return
        try:
            evolution_json_path = os.path.join(
                ".", "evolution_data", previous_render_prefix + "_grid_" + grid_key
            )
            with open(evolution_json_path) as f:
                previous_data = json.load(f)

            # Creating a dic with existing entries in the previous dic to improve performance
            existing_lines = {}
            for dict in previous_data:
                existing_lines[dict[column]] = True

            # Editing current data to add a "new" mark to new lines
            for d in self.data:
                v = d[column]
                if v not in existing_lines:
                    d[column] = (
                        '<i class="bi bi-patch-exclamation" style="color: darkred;"></i>'
                        + v
                        + " (new)"
                    )

        except Exception as e:
            logger.print_error(
                f'"New" icon will not be displayed as an error occurend when trying to open the json file {evolution_json_path}'
            )
            logger.print_error(e)
