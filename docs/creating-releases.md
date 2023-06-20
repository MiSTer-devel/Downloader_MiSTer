# Creating Releases

Developers of cores _outside_ of the [MiSTer-devel Github organization](https://github.com/MiSTer-devel) should create an external manifest/"database" as described in [Custom Databases](custom-databases.md).

## Hosting the Manifest

There are several recommended methods to host your manifest file:

* Commit the manifest directly to the repository - This has the disadvantage of requiring constant commits simultaneously with your core releases
* Create an orphaned branch (with no normal commits in it) to contain your manifest - This still requires constant commits, but those commits are hidden away in another branch

Releases can be stored on any webserver, including in Github Releases.

If you are using Github, prefer to host in a way that hits Github's CDN, as downloads will be much faster.

> **Warning**: Github API not supported
>
> The Github API has significant rate limits that would limit the ability to fetch multiple databases.
>
> A previous version of the tool used the Github API, and the problems encountered were significant enough to remove the feature.