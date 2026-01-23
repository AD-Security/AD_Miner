from ad_miner.sources.modules.utils import grid_data_stringify
from urllib.parse import quote


def clean_label(label_list):
    if 'Base' in label_list: 
        label_list.remove('Base')

    if 'AZBase' in label_list: 
        label_list.remove('AZBase')

    if len(label_list) == 0:
        return ""
    else:
        return label_list[0]

def clean_data_type(data, list_type_to_clean):
    for k in range(len(data)):
        for type_name in list_type_to_clean:
            data[k][type_name] = clean_label(data[k][type_name])
    return data


def get_label_icon_dictionary():
    return {"User": "<i class='bi bi-person-fill' title='User'></i>", "Computer": "<i class='bi bi-pc-display' title='Computer'></i>", "Group": "<i class='bi bi-people-fill' title='Group'></i>", "ADLocalGroup": "<i class='bi bi-people-fill' title='Group'></i>", "OU": "<i class='bi bi-building' title='OU'></i>", "Container": "<i class='bi bi-box' title='Container'></i>", "Domain": "<i class='bi bi-globe' title='Domain'></i>", "GPO": "<i class='bi bi-journal-text' title='GPO'></i>", "Unknown": "<i class='bi bi-question-circle-fill' title='Unknown'></i>"}

def get_label_icon(name):
    if name in get_label_icon_dictionary():
        return get_label_icon_dictionary()[name]
    else:
        return get_label_icon_dictionary()["Unknown"]


# format data for grid components format: list of dicts [{key1:value1}, {key2:value2}]
def formatGridValues2Columns(data, headers, prefix, icon="", icon2=""):
    output = []
    for key, value in data.items():
        if icon == "":
            output.append(
                {
                    headers[0]: icon2 + key,
                    headers[1]: grid_data_stringify({
                        "link": "%s.html?object=%s" % (quote(str(prefix)), quote(str(key))),
                        "value": str(value)
                        + ' <i class="bi bi-box-arrow-up-right"></i>',
                    }),
                }
            )
        else:
            sortClass = str(value).zfill(6)  # used to make the sorting feature work with icons
            output.append(
                {
                    headers[0]: icon2 + key,
                    headers[1]: grid_data_stringify({
                        "link": "%s.html?object=%s" % (quote(str(prefix)), quote(str(key))),
                        "before_link": f'{icon[:-6]} {sortClass}"></i>',
                        "value": str(value),
                    }),
                }
            )
    return output


# trash, this will probably be deleted (11/08/22 EDIT : spoilers it wasn't)
def formatGridValues1Columns(data, headers):
    output = []
    for value in data:
        output.append({headers[0]: value, "href_link": ""})
    return output


# Format : [{k1:v1, k2:v2, k3:v3}, {k1:v1', k2:v2', k3:v3'}, ...]
def formatGridValues3Columns(data, headers, prefix):
    output = []
    for dict in data:
        if dict[headers[1]] > 1:
            output.append(
                {
                    headers[0]: dict[headers[0]],
                    headers[1]: dict[headers[1]],
                    headers[2]: {
                        "link": "%s.html?parameter=%s"
                        % (quote(str(prefix)), quote(str(dict[headers[0]]))),
                        "value": "Show list of objects <i class='bi bi-box-arrow-up-right'></i><p style='display: none;'>%s</p>"
                        % dict[headers[2]],
                    },
                }
            )
        else:
            output.append(
                {
                    headers[0]: dict[headers[0]],
                    headers[1]: dict[headers[1]],
                    headers[2]: {"link": "FALSE_LINK", "value": dict[headers[2]]},
                }
            )

    return output


def formatFor3Col(dictRDP, headers):
    rslt = []
    for key in dictRDP.keys():
        partDict = {}
        partDict[headers[0]] = key
        partDict[headers[1]] = len(dictRDP[key])
        partDict[headers[2]] = dictRDP[key]
        rslt.append(partDict)
    return rslt
