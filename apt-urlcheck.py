#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import ansi
import os.path
import re
import requests
from aptsources.distro import get_distro
from aptsources.sourceslist import SourcesList
from typing import TypeVar

codenames_okay = ["devel", "stable", "unstable", "beta", "preview", "testing", "syncthing"]
codenames_old = ["gutsy", "hardy", "intrepid", "jaunty", "karmic", "lucid", "maverick", "natty", "oneiric", "precise", "quantal", "raring", "saucy", "trusty", "utopic", "vivid", "wily"]
codenames = ["jessie", "xenial", "yakkety", "zesty", "stretch", "artful", "bionic", "squeeze"]

codename = get_distro().codename
print("This is {}.".format(ansi.YELLOW + codename + ansi.RESET))

print("Loading sources...", end="", flush=True)

valid_sources = 0
outdated_sources = 0
check_sources = []
for source in SourcesList():
    if source.disabled or source.line=="\n":
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
    global codenames_okay, codenames_old, codenames, fetch_cache
    if url in fetch_cache:
        return fetch_cache[url]
    all_known_codenames = codenames_old + codenames
    result = requests.get(url)
    if result.status_code != 200:
        fetch_cache[url] = False
        return False
    matches = re.findall(r"<a .*?href=['\"]?([^'\"]+)['\"]?.*?>", result.text)
    valid_matches = []
    for match in matches:
        if match[0] != "?" and match[0] != "/" and match[-1:] == "/" and match != "../" and match[0:4] != "http":
            valid_matches.append(match[0:-1])
        elif match in all_known_codenames or match[0:-1] in all_known_codenames:
            valid_matches.append(match)
    fetch_cache[url] = valid_matches
    return fetch_cache[url]

def mutate_codename(current_codename: str, new_codename: str) -> str:
    global codenames_okay, codenames_old, codenames
    all_codenames = codenames_old + codenames
    for cn in all_codenames:
        if cn in current_codename:
            return current_codename.replace(cn, new_codename)
    return new_codename

probe_cache = {}

def try_url_probing(url: str, current_codename: str) -> list:
    global codenames_okay, codenames_old, codenames, probe_cache
    cache_key = url + "|" + current_codename
    if cache_key in probe_cache:
        return probe_cache[cache_key]
    test_set = codenames + codenames_okay
    valid_matches = []
    for codename in test_set:
        for filename in ["InRelease", "Release", "Release.gpg"]:
            mcodename = mutate_codename(current_codename, codename)
            try_url = "{}/{}/{}".format(url, mcodename, filename)
            print(".", end="", flush=True)
            result = requests.get(try_url)
            if result.status_code == 200:
                valid_matches.append(mcodename)
                break
    probe_cache[cache_key] = valid_matches
    return probe_cache[cache_key]

def filter_better_matches(found_codenames: list, current_codename: str) -> list:
    global codenames, codenames_okay, codenames_old
    better_codenames = []
    for cn in found_codenames:
        if cn > current_codename:
            better_codenames.append(cn)
        elif cn in codenames_okay:
            better_codenames.append(cn)
    return better_codenames

for src in check_sources:
    print("{}: Outdated codename: {}".format(ansi.CYAN + os.path.basename(src.file) + ansi.RESET, ansi.RED + src.dist + ansi.RESET))
    test_url = src.uri + "/dists"
    more_options = try_fetch_dirlisting(test_url)
    if not more_options:
        print("Listing failed. Probing", end="", flush=True)
        more_options = try_url_probing(test_url, src.dist)
        print(" OK")
        print(ansi.UP_DEL, end="")
    better_options = filter_better_matches(more_options, src.dist)
    if better_options:
        print("Possibly better options: {}".format(ansi.GREEN + (ansi.RESET + ", " + ansi.GREEN).join(better_options) + ansi.RESET))
    else:
        print(ansi.SILVER + "No better match(es) found at the moment." + ansi.RESET)
