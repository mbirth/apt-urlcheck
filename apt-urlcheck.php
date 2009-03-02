#!/usr/bin/php
<?php

echo 'Getting codename ... ';
$codename = exec('lsb_release -cs');
echo $codename . PHP_EOL;

echo 'Getting apt lists ... ';
$paths = array('/etc/apt/sources.list');
$morefiles = glob('/etc/apt/sources.list.d/*.list');
$paths = array_merge($paths, $morefiles);
echo count($paths) . ' files found.' . PHP_EOL;

echo 'Parsing lists ... ';
$debs = array();
foreach ($paths as $path) {
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
echo count($debs) . ' entries found.' . PHP_EOL;

foreach ($debs as $deb) {
    $info = parseDebLine($deb['data']);
    if (substr($info['distr'], 0, strlen($codename)) != $codename) {
        echo 'Mismatching distribution ' . $info['distr'] . ' in ' . $deb['line'] . '@' . $deb['file'] . PHP_EOL;
        echo 'Available dists: ' . implode(', ', getAvailDists($info['url'])) . PHP_EOL;
    }
}

function parseDebLine($line) {
    $parts = explode(' ', $line);
    $result = array(
        'type' => $parts[0],
        'url' => $parts[1],
        'distr' => $parts[2],
        'components' => array_slice($parts, 3),
    );
    return $result;
}

function getAvailDists($url) {
    $list = @file_get_contents($url.'/dists');
    preg_match_all('/<a [^>]*href="?([^" ]+)"?[^>]*>/i', $list, $matches);
    $result = array();
    foreach ($matches[1] as $match) {
        if ($match{0} != '?' && $match{0} != '/' && substr($match, -1) == '/') {
            $result[] = substr($match, 0, -1);
        }
    }
    return $result;
}


?>