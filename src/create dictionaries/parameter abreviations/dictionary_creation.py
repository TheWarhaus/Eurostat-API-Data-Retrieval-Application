"""
Code which takes Eurostat code list donwloaded from here: https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/codelist/ESTAT/
And parse it into dictionary json file.
"""
import xml.etree.ElementTree as ET
import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, "ALL_CODELISTS.xml")

tree = ET.parse(input_path)
root = tree.getroot()

ns = {
    "s": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "c": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common"
}

lookup = {}

# Loop though all the parameters
for codelist in root.findall(".//s:Codelist", ns):
    parameter_id = codelist.get("id")
    parameter_name = codelist.find(
        "c:Name[@{http://www.w3.org/XML/1998/namespace}lang='en']",
        ns
    )

    # Get the full name of the parameter
    lookup[parameter_id] = {
        "name": parameter_name.text if parameter_name is not None else "",
        "values": {}
    }

    # Loop though all the values of the parameter
    for code in codelist.findall("s:Code", ns):
        code_id = code.get("id")
        code_name = code.find(
            "c:Name[@{http://www.w3.org/XML/1998/namespace}lang='en']",
            ns
        )

        if code_name is not None:
            lookup[parameter_id]["values"][code_id] = code_name.text

output_path = os.path.join(script_dir, "lookup_dictionary.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(lookup, f, indent=4, ensure_ascii=False) # move the json file to P drive after its produced.

print(f"Dictionary created at:\n{output_path}")
