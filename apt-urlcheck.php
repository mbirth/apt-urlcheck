#!/usr/bin/php
<?php

class APTChecker
{
    private $whitelist = array();
    private $aptlists = array();
    private $codenames = array( 'debian', 'stable', 'unstable', 'beta', 'hardy', 'intrepid', 'jaunty', 'karmic', 'lucid', 'maverick', 'natty', 'oneiric', 'precise', 'quantal', 'raring' );
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
        $result = array(
            'type' => $parts[0],
            'url' => $parts[1],
            'distr' => $parts[2],
            'components' => array_slice($parts, 3),
        );
        return $result;
    }

    private function tryFetch( $url ) {
        $answer = array();
        stream_context_set_default( array(
            'http' => array(
                'method' => 'HEAD'
            )
        ) );
        $result = get_headers( $url, 1 );
        $status_line = $result[0];
        if ( is_array( $status_line ) ) {
            $status_line = end( $status_line );
        }
        $status = substr( $status_line, 9, 3 );

        stream_context_set_default( array(
            'http' => array(
                'method' => 'GET'
            )
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
            if ($match{0} != '?' && $match{0} != '/' && substr($match, -1) == '/') {
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
            $try_url = $baseurl . '/dists/' . $codename . '/Release';
            $exists = $this->tryFetch( $try_url );
            if ( $exists !== false ) {
                $result[] = $codename;
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

    public function analyzeDebs()
    {
        $debs = $this->parseLists();
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
                echo 'Mismatching distribution ' . $info['distr'] . ' in ' . $deb['line'] . '@' . $deb['file'] . PHP_EOL;
                echo 'Available dists: ' . implode(', ', $this->getAvailDists( $info['url'], $info['distr'] ) ) . PHP_EOL;
            }
            if ($this->isRoot()) $this->getKeyId($info['url'], $info['distr']);  // cache key-id
        }
        return $result;
    }

    public function getAvailDists( $url, $expect = false )
    {
        if ( $expect === false ) $expect = $this->codename;
        $list = @file_get_contents($url.'/dists');
        if ( $list === false ) {
            // TODO: Build URL for private PPAs (trailing slash in $expect)
            $try_url = rtrim( $url, '/' ) . '/dists/' . $expect . '/Release';
            echo 'Dirlisting denied. Trying: ' . $try_url . PHP_EOL;
            $pkgfile = @file_get_contents( $try_url );
            if ( $pkgfile === false ) {
                return array( '404 NOT FOUND!! or error while fetching.' );
            }
            return array( '[' . $expect . ']' );
        }
        preg_match_all('/<a [^>]*href="?([^" ]+)"?[^>]*>/i', $list, $matches);
        $result = array();
        foreach ($matches[1] as $match) {
            if ($match{0} != '?' && $match{0} != '/' && substr($match, -1) == '/') {
                $dist_code = substr($match, 0, -1);
                $result[] = (($dist_code==$this->codename)?strtoupper( $dist_code ):$dist_code);
            }
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


}

$ac = new APTChecker();
$ac->addWhitelist( array( 'stable', 'unstable' ) );

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

$debinfo = $ac->analyzeDebs( $debs );
print_r( $debinfo );

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


function checkCurrentDist($url) {
    $fullurl = 'http://linux.getdropbox.com/ubuntu/dists/jaunty/main/binary-i386/Packages.gz';
}


?>
