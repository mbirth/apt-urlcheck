#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os.path
import re
import sys
from typing import TypeVar
import requests
from aptsources.distro import get_distro
from aptsources.sourceslist import SourcesList
import ansi

# If this codename is found on the repo, ignore it
codenames_ignore = ["devel"]

# If a PPA has one of these codenames, it is assumed to be fine this way
codenames_okay = ["devel", "stable", "unstable", "beta", "preview", "testing", "syncthing", "flightradar24", "./"]

releases = {
    "Ubuntu": {
        "2004-10-26": "warty",
        "2005-04-08": "hoary",
        "2005-10-12": "breezy",
        "2006-06-01": "dapper",
        "2006-10-26": "edgy",
        "2007-04-19": "feisty",
        "2007-10-18": "gutsy",
        "2008-04-24": "hardy",
        "2008-10-30": "intrepid",
        "2009-04-23": "jaunty",
        "2009-10-29": "karmic",
        "2010-04-29": "lucid",
        "2010-10-10": "maverick",
        "2011-04-28": "natty",
        "2011-10-13": "oneiric",
        "2012-04-26": "precise",
        "2012-10-18": "quantal",
        "2013-04-25": "raring",
        "2013-10-17": "saucy",
        "2014-04-17": "trusty",
        "2014-10-23": "utopic",
        "2015-04-23": "vivid",
        "2015-10-22": "wily",
        "2016-04-21": "xenial",
        "2016-10-13": "yakkety",
        "2017-04-13": "zesty",
        "2017-10-19": "artful",
        "2018-04-30": "bionic"
    },
    "Debian": {
        "2000-08-14": "potato",
        "2002-07-19": "woody",
        "2005-06-06": "sarge",
        "2007-04-08": "etch",
        "2009-02-14": "lenny",
        "2011-02-06": "squeeze",
        "2013-05-04": "wheezy",
        "2015-04-26": "jessie",
        "2017-06-17": "stretch",
        "2019-06-30": "buster",
        "2999-12-31": "sid"      # unstable
    },
    "Mint": {
        "2006-08-27": "ada",
        "2006-11-13": "barbara",
        "2006-12-20": "bea",
        "2007-02-20": "bianca",
        "2007-05-30": "cassandra",
        "2007-09-24": "celena",
        "2007-10-15": "daryna",
        "2008-06-08": "elyssa",
        "2008-12-15": "felicia",
        "2009-05-26": "gloria",
        "2009-11-28": "helena",
        "2010-05-18": "isadora",
        "2010-11-12": "julia",
        "2011-05-26": "katya",
        "2011-11-26": "lisa",
        "2012-05-23": "maya",
        "2012-11-20": "nadia",
        "2013-05-29": "olivia",
        "2013-11-30": "petra",
        "2014-05-31": "qiana",
        "2014-11-29": "rebecca",
        "2015-06-30": "rafaela",
        "2015-12-04": "rosa",
        "2016-06-30": "sarah",
        "2016-12-16": "serena",
        "2017-07-02": "sonya",
        "2017-11-27": "sylvia",
        "2018-06-30": "tara"
    }
}

codenames = []
all_dates = []
for dist in releases:
    all_dates += releases[dist].keys()
all_dates = sorted(all_dates)
for date in all_dates:
    for dist in releases:
        if date in releases[dist]:
            codenames += [releases[dist][date]]

codename = get_distro().codename
distro = get_distro().id
print("This is {} ({}).".format(ansi.YELLOW + codename + ansi.RESET, distro))

if codename not in codenames:
    print("ERROR: Codename not found in database. Please update this tool!")
    sys.exit(1)

print("Loading sources...", end="", flush=True)

valid_sources = 0
outdated_sources = 0
check_sources = []
for source in SourcesList():
    if source.disabled or source.line == "\n":
        continue
    valid_sources += 1
    #print(".", end="", flush=True)
    if codename in source.dist or source.dist in codenames_okay:
        continue
    outdated_sources += 1
    check_sources.append(source)
    #print("{}: {}".format(source.file, source.line.strip()))

check_sources = sorted(check_sources, key=lambda x: x.file)

print(" OK")
print("Found {} sources with {} possibly outdated.".format(valid_sources, outdated_sources))


BorL = TypeVar("BorL", bool, list)

fetch_cache = {}

def try_fetch_dirlisting(url: str) -> BorL:
    global codenames, fetch_cache
    if url in fetch_cache:
        return fetch_cache[url]
    result = requests.get(url)
    if result.status_code != 200:
        fetch_cache[url] = False
        return False
    matches = re.findall(r"<a .*?href=['\"]?([^'\"]+)['\"]?.*?>", result.text)
    valid_matches = []
    for match in matches:
        if match[0] != "?" and match[0] != "/" and match[-1:] == "/" and match != "../" and match[0:4] != "http":
            valid_matches.append(match[0:-1])
        elif match in codenames or match[0:-1] in codenames:
            valid_matches.append(match)
    fetch_cache[url] = valid_matches
    return fetch_cache[url]

def mutate_codename(current_codename: str, new_codename: str) -> str:
    global codenames
    for cn in codenames:
        if cn in current_codename:
            return current_codename.replace(cn, new_codename)
    return new_codename

probe_cache = {}

def get_probing_test_set(current_codename: str) -> list:
    global codenames
    for cn in codenames:
        if cn in current_codename:
            idx = codenames.index(cn)
            return codenames[idx+1:]
    # If nothing found, try 10 newest codenames
    return codenames[-10:]

def try_url_probing(url: str, current_codename: str) -> list:
    global probe_cache
    cache_key = url + "|" + current_codename
    if cache_key in probe_cache:
        return probe_cache[cache_key]
    test_set = get_probing_test_set(current_codename)
    valid_matches = []
    for codename in test_set:
        mcodename = mutate_codename(current_codename, codename)
        print(ansi.SCP + mcodename, end="", flush=True)
        for filename in ["InRelease", "Release", "Release.gpg"]:
            try_url = "{}/{}/{}".format(url, mcodename, filename)
            print(".", end="", flush=True)
            result = requests.get(try_url)
            if result.status_code == 200:
                valid_matches.append(mcodename)
                break
        print(ansi.RCP + ansi.EL, end="", flush=True)
    probe_cache[cache_key] = valid_matches
    return probe_cache[cache_key]

def is_better_match(found_codename: str, current_codename: str) -> bool:
    global codenames
    if found_codename in codenames:
        return (codenames.index(found_codename) > codenames.index(current_codename))
    else:
        return (found_codename > current_codename)

def filter_better_matches(found_codenames: list, current_codename: str) -> list:
    global codenames_ignore
    better_codenames = []
    for cn in found_codenames:
        if  cn not in codenames_ignore and is_better_match(cn, current_codename):
            better_codenames.append(cn)
    return better_codenames

for src in check_sources:
    print("{}: Outdated codename: {}".format(ansi.CYAN + os.path.basename(src.file) + ansi.RESET, ansi.RED + src.dist + ansi.RESET))
    test_url = src.uri + "/dists"
    more_options = try_fetch_dirlisting(test_url)
    if not more_options:
        print("Listing failed. Probing: ", end="", flush=True)
        more_options = try_url_probing(test_url, src.dist)
        print(" OK")
        print(ansi.UP_DEL, end="")
    better_options = filter_better_matches(more_options, src.dist)
    if better_options:
        print("Possibly better options: {}".format(ansi.GREEN + (ansi.RESET + ", " + ansi.GREEN).join(better_options) + ansi.RESET))
    else:
        print(ansi.SILVER + "No better match(es) found at the moment." + ansi.RESET)
