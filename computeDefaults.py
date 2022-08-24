from glob import glob
import yaml
from yaml.loader import SafeLoader
from typing import Dict, List
import argparse

parser = argparse.ArgumentParser(description="Compute defaults from known sources")
parser.add_argument(
    "-d",
    "--defaultsFile",
    default="defaults.yaml",
    help="Set the defaults file to use (overrides defaults.yaml)",
)
parser.add_argument("--dry-run", action="store_true", help="Print the defaults but don't write to file")
args = parser.parse_args()

modelInputs = {
    "travel emissions mt per employee per month",
    "office emissions mt per employee per month",
    "commuting emissions mt per employee per month",
    "it emissions mt per employee per month",
    "bid requests processed billion per month",
    "pct of bid requests processed from ad tech platforms",
    "bid request size in bytes",
    "server to server emissions g per gb",
    "server emissions mt per month",
    "servers processing bid requests pct",
}

# inputs where we don't have enough data and have to guess
bestGuess: Dict[str, float] = {
    "pct of bid requests processed from ad tech platforms": 30,
    "bid request size in bytes": 10000,
    # https://www.cloudcarbonfootprint.org/docs/methodology/#cloud-usage-and-cost-data-source
    # https://www.cloudcarbonfootprint.org/docs/methodology/#appendix-v-grid-emissions-factors
    # Above give 0.001 kWh per GB and 379 g per kWh (AWS US East 1)
    "server to server emissions g per gb": 0.379,
    # TODO: Need templates
    "servers processing bid requests pct": 100,
}

# get a list of all facts from our sources
facts: Dict[str, List[float]] = {}

files = glob("sources/**/*.yaml", recursive=True)
for file in files:
    stream = open(file, "r")
    documents = list(yaml.load_all(stream, Loader=SafeLoader))
    for document in documents:
        if "company" not in document:
            print("No company found in " + document)
            continue
        if "sources" not in document["company"]:
            print("No sources found in " + document)
            continue
        for source in document["company"]["sources"]:
            for fact in source["source"]["facts"]:
                keys = [key for key in fact["fact"] if key != "reference" and key != "comment"]
                for key in keys:
                    if key not in facts:
                        facts[key] = []
                    facts[key].append(fact["fact"][key])

defaults: Dict[str, float] = {}
for key in facts:
    if key in modelInputs:
        defaults[key] = round(sum(facts[key]) / len(facts[key]), 4)

for input in modelInputs:
    if input not in defaults:
        print(f"{input} not modeled - using best guess")
        defaults[input] = bestGuess[input]

output = yaml.dump({"defaults": defaults}, Dumper=yaml.Dumper)
if args.dry_run:
    print(output)
else:
    writeStream = open(args.defaultsFile, "w")
    writeStream.write(output)
    writeStream.close()
