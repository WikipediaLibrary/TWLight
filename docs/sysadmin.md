# Sysadmin docs

This documentation is aimed at the system administrator who is setting up an
instance of TWLight in the Wikimedia Cloud VPS environment, where the production site is currently hosted.

## Access

To follow the rest of this guide you must first be a project administrator for the [twl project](https://tools.wmflabs.org/openstack-browser/project/twl). Contact an existing administrator if you require access.

## Process

### Horizon instance

For general information on using Horizon see the [Horizon FAQ](https://wikitech.wikimedia.org/wiki/Help:Horizon_FAQ).

1. If you are recreating an instance, first delete the old one in the Compute > Instances tab, taking note of the previous name.
2. Launch a new instance, entering the desired hostname (e.g. `twlight-staging`), and appropriate debian image and instance flavor.
3. Click on the new instance, and scroll to the bottom of the Puppet Configuration tab. Edit the Hiera Config to contain only `mount_nfs: true` to give this instance access to the project NFS share.
4. Create a web proxy by navigating to the DNS > Web Proxies tab and creating a new proxy to the newly created backend instance. The backend port should be set to 80.

### Connect

If this is your first time connecting to a Wikimedia Cloud Services environment, see [Help:Access](https://wikitech.wikimedia.org/wiki/Help:Access) for guidance on setting up SSH keys and config.

You should now be able to SSH to the instance with `ssh hostname.twl.eqiad1.wikimedia.cloud`, replacing `hostname` as appropriate. If you are recreating an instance you may need to drop your old keys.

For server setup, see the [Debian Server setup](https://github.com/WikipediaLibrary/TWLight/wiki/Debian-Server-setup) wiki page.

## Deploying updated code

Code deployment works on a mostly automated basis. New commits in the repository master branch are run through Travis CI (scripts [here](https://github.com/WikipediaLibrary/TWLight/tree/master/.travis)) to run tests and check that it builds successfully. Travis will also check for any necessary migrations and translation updates and commit these back to the master branch if necessary (see, for example, [this commit](https://github.com/WikipediaLibrary/TWLight/commit/cac6b36b6f94c4a186360409fb7fa829650f541a)).

Once Travis is happy with the build, the code is pushed to the [production](https://github.com/WikipediaLibrary/TWLight/tree/production) branch. The production server then checks for new code every 5 minutes and deploys it via cron
