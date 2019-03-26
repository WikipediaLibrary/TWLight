function FindProxyForURL(url, host) {
    if (host=='twlight.vagrant.localdomain'){
        return 'PROXY 127.0.0.1:80';
    }
    // All other domains should connect directly without a proxy
    return "DIRECT";
}
