"""
Code which takes Eurostat database list donwloaded from here: https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/xml
And parse it into dictionary json file.
"""

import xml.etree.ElementTree as ET
import json
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(script_dir, "table_of_contents.xml")

NS = "urn:eu.europa.ec.eurostat.navtree"
LANG = "en"

def q(tag):
    return f"{{{NS}}}{tag}"

def title(el):
    for t in el.findall(q("title")):
        if t.get("language") == LANG:
            return (t.text or "").strip()

def parse(el):
    if el.tag == q("branch"): # folder
        node = {"code": el.findtext(q("code")), "title": title(el),
                "type": "folder", "children": []}
    else: # database
        node = {"code": el.findtext(q("code")), "title": title(el),
                "type": el.get("type"),
                "last_update": el.findtext(q("lastUpdate")),
                "data_start": el.findtext(q("dataStart")),
                "data_end": el.findtext(q("dataEnd"))}
 
    children = el.find(q("children"))
    if children is not None:
        node["children"] = [parse(c) for c in children
                            if c.tag in (q("branch"), q("leaf"))]
    return node

root = ET.parse(input_path).getroot()
tree = [parse(b) for b in root.findall(q("branch"))]

output_path = os.path.join(script_dir, "database_dictionary.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(tree, f, indent=4, ensure_ascii=False) # move the json file to P drive after its produced.

print(f"Dictionary created at:\n{output_path}")
