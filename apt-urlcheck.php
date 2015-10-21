#!/usr/bin/php
<?php

class APTChecker
{
    private $whitelist = array();
    private $aptlists = array();
    private $codenames_old = array( 'gutsy', 'hardy', 'intrepid' );
    private $codenames = array( 'jaunty', 'karmic', 'lucid', 'maverick', 'natty', 'oneiric', 'precise', 'quantal', 'raring', 'saucy', 'trusty', 'utopic', 'vivid', 'wily', 'debian', 'squeeze', 'stable', 'unstable', 'beta' );
    private $codename;

    function __construct()
    {
        $this->codename = exec('lsb_release -cs');

        $this->addSourceLists( '/etc/apt/sources.list' );
        $this->addSourceLists( '/etc/apt/sources.list.d/*.list' );
    }

    public function addSourceLists( $filemask )
    {
        $this->aptlists = array_merge( $this->aptlists, glob( $filemask ) );
    }

    public function getSourceLists()
    {
        return $this->aptlists;
    }

    public function addWhitelist( $codename )
    {
        if ( !is_array( $codename ) ) $codename = array( $codename );
        foreach ( $codename as $cn ) {
            $this->whitelist[] = $cn;
        }
    }

    public function isRoot()
    {
        return (posix_getuid() == 0);
    }

    public function getCodename()
    {
        return $this->codename;
    }

    public function parseLists()
    {
        $debs = array();
        foreach ( $this->getSourceLists() as $path ) {
            $fc = file($path, FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES);
            foreach ($fc as $i=>$fline) {
                if ((substr($fline, 0, 4) == 'deb ') || (substr($fline, 0, 8) == 'deb-src ')) {
                    $debs[] = array(
                        'file' => $path,
                        'line' => $i+1,
                        'data' => $fline,
                    );
                }
            }
        }
        return $debs;
    }

    public function parseDebLine( $line )
    {
        $parts = explode(' ', $line);
        if ( $parts[1]{0} == '[' ) {
            $result = array(
                'type' => $parts[0],
                'attributes' => $parts[1],
                'url' => $parts[2],
                'distr' => $parts[3],
                'components' => array_slice($parts, 4),
            );
        } else {
            $result = array(
                'type' => $parts[0],
                'attributes' => '',
                'url' => $parts[1],
                'distr' => $parts[2],
                'components' => array_slice($parts, 3),
            );
        }
        return $result;
    }

    private function tryFetch( $url ) {
        $answer = array();
        stream_context_set_default( array(
            'http' => array(
                'method' => 'HEAD',
                'timeout' => 5.0,
            ),
        ) );
        $result = get_headers( $url, 1 );
        $status_line = $result[0];
        if ( is_array( $status_line ) ) {
            $status_line = end( $status_line );
        }
        $status = substr( $status_line, 9, 3 );

        stream_context_set_default( array(
            'http' => array(
                'method' => 'GET',
            ),
        ) );

        return ( $status == '200' );
    }

    private function tryGetDirectoryListing( $url )
    {
        $list = @file_get_contents( $url );
        if ( $list === false ) return false;
        preg_match_all('/<a [^>]*href="?([^" ]+)"?[^>]*>/i', $list, $matches);
        $result = array();
        foreach ($matches[1] as $match) {
            if ($match{0} != '?' && $match{0} != '/' && substr($match, -1) == '/' && $match != '../' ) {
                $result[] = substr($match, 0, -1);
            }
        }
        return array_unique( $result );
    }

    private function tryReleases( $baseurl, $additional = array() )
    {
        if ( !is_array( $additional ) ) $additional = array( $additional );

        $result = array();
        foreach ( array_unique( array_merge( $this->codenames, $additional ) ) as $codename ) {
            foreach ( array( 'InRelease', 'Release', 'Release.gpg' ) as $filename ) {
                $try_url = $baseurl . '/dists/' . $codename . '/' . $filename;
                $exists = $this->tryFetch( $try_url );
                if ( $exists !== false ) {
                    $result[] = $codename;
                    break;
                }
            }
        }
        return $result;
    }

    private function getServerInfo( $info )
    {
        $result = array();
        $result['method'] = 'dirlist';
        $dirlist = $this->tryGetDirectoryListing( $info['url'] . '/dists' );
        if ( $dirlist === false ) {
            // Damn!
            $dirlist = $this->tryReleases( $info['url'], $info['distr'] );
            $result['method'] = 'bruteforce';
        }
        $result['dists'] = $dirlist;
        return $result;
    }

    public function analyzeDebs( $debs = null, $progress = null )
    {
        if (is_null($debs)) $debs = $this->parseLists();
        $result = array();
        foreach ( $debs as $deb ) {
            $info = $this->parseDebLine( $deb['data'] );
            if ( substr( $info['distr'], 0, strlen( $this->codename ) ) != $this->codename && !in_array( $info['distr'], $this->whitelist ) ) {
                $serverinfo = $this->getServerInfo( $info );
                $result[] = array(
                    'deb'    => $deb,
                    'info'   => $info,
                    'server' => $serverinfo,
                );
            }
            if ($this->isRoot()) $this->getKeyId($info['url'], $info['distr']);  // cache key-id
            if (!is_null($progress)) call_user_func($progress);
        }
        return $result;
    }

    private function getKeyId( $url, $dist )
    {
        global $keycache;
        if (!isset($keycache)) $keycache = array();
        if (isset($keycache[$url][$dist])) return $keycache[$url][$dist];
        $sigfile = @file_get_contents($url.'/dists/'.$dist.'/Release.gpg');
        if ($sigfile === false) {
            echo 'No signature found.' . PHP_EOL;
            $keycache[$url][$dist] = false;
            return false;
        }
        exec('echo "' . $sigfile . '" | gpg --batch --verify - /etc/passwd 2>&1', $output, $retval);
        $output = implode(PHP_EOL, $output);
        preg_match('/gpg: Signature made (.*) using (.*) key ID (.*)\r?\n/m', $output, $matches);
        $result = array(
            'date' => $matches[1],
            'type' => $matches[2],
            'id'   => $matches[3],
            'desc' => $matches[4],
        );
        echo 'Repo uses key id ' . $result['id'] . PHP_EOL;
        if (empty($result['id'])) {
            echo 'DEBUG: ' . $output . PHP_EOL;
        }
        $keycache[$url][$dist] = $result;
        return $result;
    }

    public function outputResults( $debinfo ) {
        foreach ( $debinfo as $di ) {
            echo 'Mismatching distribution "' . $di['info']['distr'] . '" in ' . $di['deb']['file'] . ':' . $di['deb']['line'] . PHP_EOL;
            $better = array();
            $current = array_search( $di['info']['distr'], $this->codenames );
            foreach ( $di['server']['dists'] as $dist_avail ) {
                $where = array_search( $dist_avail, $this->codenames );
                if ( $where === false || $where > $current ) {
                    $better[] = $dist_avail;
                }
            }
            //echo 'Available: ' . implode( ', ', $di['server']['dists'] ) . PHP_EOL;
            if ( count( $better ) > 0 ) echo 'Possibly better matches: ' . implode( ', ', $better ) . PHP_EOL;
        }
    }
}

$ac = new APTChecker();
$ac->addWhitelist( array( 'stable', 'unstable', 'beta' ) );

echo 'System: ' . $ac->getCodename() . PHP_EOL;

echo 'Running as user id ' . posix_getuid() . PHP_EOL;

echo 'Parsing lists ... ';
$debs = $ac->parseLists();
echo count($debs) . ' entries found.' . PHP_EOL;

if ( $ac->isRoot() ) {
    echo 'Fetching key ids of keyring ... ';
    exec('apt-key list', $output, $retval);
    $output = implode(PHP_EOL, $output);
    preg_match_all('/pub.*\/([^\s]+).*\r?\n/m', $output, $matches);
    $allkeys = $matches[1];
    echo count($allkeys) . ' keys found.' . PHP_EOL;
} else {
    echo 'Not started as root. Will not check GPG keys.' . PHP_EOL;
}

$debinfo = $ac->analyzeDebs( $debs, 'progressInd' );
echo PHP_EOL;
$ac->outputResults( $debinfo );

if ( $ac->isRoot() ) {
    foreach ( $keycache as $url=>$dists ) {
        foreach ( $dists as $dist=>$key ) {
            if ( !empty( $key['id'] ) && !in_array( $key['id'], $allkeys ) ) {
                echo 'Importing key ' . $key['id'] . ' ... ';
                passthru( 'apt-key adv --batch --recv-keys --keyserver keyserver.ubuntu.com ' . $key['id'] );
            }
        }
    }
}
    
echo 'All done.';
if ( !$ac->isRoot() ) echo ' (Run as root to import missing PPA keys.)';
echo PHP_EOL;
exit;

function progressInd() {
    echo '.';
}

function checkCurrentDist($url) {
    $fullurl = 'http://linux.getdropbox.com/ubuntu/dists/jaunty/main/binary-i386/Packages.gz';
}

