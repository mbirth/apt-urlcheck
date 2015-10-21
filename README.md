apt-urlcheck
============

Checks all your PPAs in `/etc/apt/sources.list.d/` for outdated entries which
can be updated.

E.g. you're running Ubuntu `wily` but have several PPAs pointing to older
Ubuntu versions. This script will check all those PPA's URLs if there are
build for newer Ubuntu versions available.
