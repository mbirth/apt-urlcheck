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
        "2004-10-26": "warty",    # Warty Warthog
        "2005-04-08": "hoary",    # Hoary Hedgehog
        "2005-10-12": "breezy",   # Breezy Badger
        "2006-06-01": "dapper",   # Dapper Drake
        "2006-10-26": "edgy",     # Edgy Eft
        "2007-04-19": "feisty",   # Feisty Fawn
        "2007-10-18": "gutsy",    # Gutsy Gibbon
        "2008-04-24": "hardy",    # Hardy Heron
        "2008-10-30": "intrepid", # Intrepid Ibex
        "2009-04-23": "jaunty",   # Jaunty Jackalope
        "2009-10-29": "karmic",   # Karmic Koala
        "2010-04-29": "lucid",    # Lucid Lynx
        "2010-10-10": "maverick", # Maverick Meerkat
        "2011-04-28": "natty",    # Natty Narwhal
        "2011-10-13": "oneiric",  # Oneiric Ocelot
        "2012-04-26": "precise",  # Precise Pangolin
        "2012-10-18": "quantal",  # Quantal Quetzal
        "2013-04-25": "raring",   # Raring Ringtail
        "2013-10-17": "saucy",    # Saucy Salamander
        "2014-04-17": "trusty",   # Trusty Tahr
        "2014-10-23": "utopic",   # Utopic Unicorn
        "2015-04-23": "vivid",    # Vivid Vervet
        "2015-10-22": "wily",     # Wily Werewolf
        "2016-04-21": "xenial",   # Xenial Xerus
        "2016-10-13": "yakkety",  # Yakkety Yak
        "2017-04-13": "zesty",    # Zesty Zapus
        "2017-10-19": "artful",   # Artful Aardvark
        "2018-04-26": "bionic",   # Bionic Beaver
        "2018-10-18": "cosmic",   # Cosmic Cuttlefish
        "2019-04-18": "disco",    # Disco Dingo
        "2019-10-30": "eoan"      # Eoan Ermine
    },
    "Debian": {
        "1996-06-17": "buzz",     # 1.1 - Buzz Lightyear
        "1996-12-12": "rex",      # 1.2 - T-Rex
        "1997-06-05": "bo",       # 1.3 - Bo Peep
        "1998-07-24": "hamm",     # 2.0 - Piggy bank
        "1999-03-09": "slink",    # 2.1 - Slinky Dog
        "2000-08-14": "potato",   # 2.2 - Mr. Potato
        "2002-07-19": "woody",    # 3.0 - Woody (Toys Cowboy)
        "2005-06-06": "sarge",    # 3.1 - Searge (Toys Soldier)
        "2007-04-08": "etch",     # 4.0 - Etch-a-Sketch
        "2009-02-14": "lenny",    # 5.0 - Binoculars (Toys)
        "2011-02-06": "squeeze",  # 6.0 - Toys Aliens
        "2013-05-04": "wheezy",   # 7.0 - Penguin Toy
        "2015-04-26": "jessie",   # 8.0 - Cowgirl
        "2017-06-17": "stretch",  # 9.0 - Octopus toy (current stable)
        "2019-06-30": "buster",   # 10.0 - Toys Dachshund
        "2020-06-30": "bullseye", # 11.0 - Toys Horse
        "2021-06-30": "bookworm", # 12.0 - worm with built-in flashlight
        "2999-12-31": "sid"      # unstable (Still In Development)
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
        "2018-06-30": "tara",
        "2018-11-30": "tessa",
        "2019-06-30": "tina"
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
    if source.disabled or source.line == "\n" or source.line == "#\n":
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

def fill_probe_cache(url: str, current_codename: str, candidates: list):
    global probe_cache
    probe_cache[url + "|" + current_codename] = candidates
    while len(candidates) > 0:
        codename = candidates.pop(0)
        probe_cache[url + "|" + codename] = candidates

def try_url_probing(url: str, current_codename: str) -> list:
    global probe_cache
    cache_key = url + "|" + current_codename
    if cache_key in probe_cache:
        return probe_cache[cache_key]
    test_set = get_probing_test_set(current_codename)
    valid_matches = []
    for codename in test_set:
        mcodename = mutate_codename(current_codename, codename)
        cache_key = url + "|" + mcodename
        if cache_key in probe_cache:
            valid_matches += probe_cache[cache_key]
            break
        print(ansi.SCP + mcodename, end="", flush=True)
        for filename in ["InRelease", "Release", "Release.gpg"]:
            try_url = "{}/{}/{}".format(url, mcodename, filename)
            print("?", end="", flush=True)
            result = requests.get(try_url)
            if result.status_code == 200:
                valid_matches.append(mcodename)
                break
        print(ansi.RCP + ansi.EL, end="", flush=True)
    fill_probe_cache(url, current_codename, valid_matches)
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
    print("{}: {} → ".format(ansi.CYAN + os.path.basename(src.file) + ansi.RESET, ansi.RED + src.dist + ansi.RESET), end="")
    test_url = src.uri + "/dists"
    more_options = try_fetch_dirlisting(test_url)
    if not more_options:
        more_options = try_url_probing(test_url, src.dist)
    better_options = filter_better_matches(more_options, src.dist)
    if better_options:
        print("{}".format(ansi.GREEN + (ansi.RESET + ", " + ansi.GREEN).join(better_options) + ansi.RESET))
    else:
        print(ansi.SILVER + src.dist + ansi.RESET)
