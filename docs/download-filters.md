# Controlling **downloader** with filters

By default **downloader** will download everything that's available, based on your selections in the configuration menu.  For more specific control over what is being downloaded, the filter option allows you to specify which cores you retrieve or update. For example, you could download only console and arcade cores, but none of the computer cores.

# Filter Use & Syntax

## Where to Add the Filters

1. Edit the file at `/media/fat/downloader.ini`
1. Add a line that starts with `filter =` under the `[mister]` section (if it doesn't exist, just create it).
1. Then, after `filter =`, add the filter terms themselves.

  - A list of official MiSTer filter terms [is available here](https://github.com/MiSTer-devel/Distribution_MiSTer)
  - You can also find terms for [Jotego Cores](https://github.com/jotego/jtcores_mister).

### Example

```
[mister]
filter = snes !cheats
```

  -  The filter above will download only the Super NES core, without its cheats, and nothing else.
  -  Anything listed after `filter =` will be downloaded, unless it's prefixed with an exclamation mark ❗ (which means NOT).
  -  Note that the symbols `-` and `_` are ignored by the filter, so terms like `pc_engine-cd` and `pcenginecd` are the same.
  -  Filter terms cannot have spaces in them.  `!pokemon mini` will be interpreted as *no* to pokemon, *yes* to mini.

## Positive and Negative Filters
**downloader** downloads everything by default.  Depending on your needs, it might make sense to simply filter out everything you don't want, or include everything you *do* want.

  -  ❗ If your filter has only negative terms, **downloader** will download everything *except your negative filters*.
  -  ‼️ If you include ***any positive terms*** then **downloader** will only download things you explicity include.

### Examples

  -  `filter = arcade !arcade-astrocade` will download only the arcade cores, except the astrocade core.
  -  `filter = arcade console` will download every arcade and console core, but nothing else.
  -  `filter= !computer` will download every core except computer cores.
  -  `filter = console !computer`  will only download console cores.  Even though !computer is explicity excluded, the positive `console` term is the *only* positive, and so it's the only inclusion.

👉 The `essential` cores will always be included unless you specifically remove them with `!essential`.  The `essential` cores include the MiSTer menus, etc, and should not be excluded for most purposes.  

#  Core Specificity
Several of the tags you can exlude are groups: `computer`, `console`, `arcade` etc.   Depending on your requirements it's possible to exclude certain cores within those groups.  You can, for example, disable all console cores `!console` but still download  `SNES NES` cores like so:  `filter = !console snes nes`.

  - `filter = !cheats !other !arcade-bankpanic` will download everything *except* `cheats`, `other` (which includes standalone systems like Game n Watch) and the bankpanic arcade core.
  - `filter = arcade !arcade-asteroids !arcade-cave` will only download arcade cores, except the asteroids and Cave cores.

### 👉 Many cores are responsible for more than one game.

The `Astrocade` core covers games like _Wizard of Wor_ and _Gorf_, and the `Cave` core covers _DonPachi_, _Dangun Feveron_, and so on.  You can usually find a list of every game handled by one core by searching for it.  Google `mister astrocade core` and the first result, usually on github, will almost always include a list of the games it runs.  For things like `console` cores this obviously isn't necessary - if you disable the Super NES core, you simply won't get Super NES.

If you disable a core that you have downloaded previously with **downloader** it will be deleted, along with all the associated files (MRAs, cores etc) but it won't remove your configuration settings.

# Database-scoped filters
If you add a filter under `[mister]` it will be global, so the filter will affect **all** databases.  If you put it under a different heading, for example `[distribution_mister]`, it will affect only to that database.  In the case of a duplicate filter entry, filters under database-scoped filters will override filters in the global filter (`[mister]`).

## Combining Filters 
If you want to include the global filter in another section, you can use `filter = [mister]` to include all terms under `[mister]`.  

For example, if the global filter under `[mister]` is `filter = console computer` and the `[distribution_mister]` filter is `filter = [mister] arcade`, the database-specific filter will inherit terms from the global filter and add the arcade term. The resulting filter will be `filter = console computer arcade`.

downloader.ini file illustrating previous example:
```
[mister]
filter = console computer

[distribution_mister]
filter = [mister] arcade
```

# Porting filters from the old Updater

Most of the terms from [this list](https://github.com/MiSTer-devel/Distribution_MiSTer#tags-that-you-may-use-with-download-filters-feature), are the same terms that you could use in the filters from the old updater. That means, for the most part, filters are compatible with the old updater format. Thus, the transition is very straightforward, as you can see in this video:

https://www.youtube.com/watch?v=0gdr5Vv3obc
