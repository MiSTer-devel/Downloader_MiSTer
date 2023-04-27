# How to use the filters

In a nutshell:
1. Edit the file at `/media/fat/downloader.ini`
2. Add a **filter** property under the `[mister]` section (if it doesn't exist, just create it).
3. Then, on the right side of the property, you will add the filter terms themselves.

<p align="center">
  <img src="https://user-images.githubusercontent.com/852246/149841563-78338772-d4ec-4321-8772-6bf79eb840b3.png" /> 
</p>
<p align="center"><i>This filter will only install four systems: NES, SNES, GB and GBA.</i></p>

As a filter term, you may put a list of space-separated names such as: core names, core categories, file types, etc. Specifically, [these are all the available terms](https://github.com/MiSTer-devel/Distribution_MiSTer#tags-that-you-may-use-with-download-filters-feature) that you may use right now.

Is also worth mentioning that symbols `-` and `_` within the term are ignored by the system. So in the eyes of Downloader, the terms `pc_engine-cd` and `pcenginecd` would be equivalent.

For negative filter terms, you would have to prepend an exclamation mark `!` before the term. In the following example, the filter is saying *"I want all the arcade, console and computer cores, except the Pong Arcade"*:

<p align="center">
  <img src="https://user-images.githubusercontent.com/852246/149841891-86f35c2f-10a2-4ed1-a08f-374f68dd921b.png" />
</p>
<p align="center"><i>The term 'arcade-pong' is negated, thus Pong files will be substracted from all previously matched files.</i></p>

You may also have a filter that only contains negative terms. In that case, the filter will get everything except the files matching these terms. In the next example, we take advantage of this to only remove *Cheats* and *Documentation* files, while keeping everything else:

https://www.youtube.com/watch?v=jBxls-yGtvI

### Database-scoped filters: Using the filter property in another section, other than [mister]
If you add a **filter** property under `[mister]` it will be global, so the filter will affect all databases. But you can constraint the filter so it only applies to a single database. For example, if you add the filter under the section `[distribution_mister]`, it will affect only to the **distribution_mister** database. And if both are defined at the same time, the database-scoped filters will always override whatever it is in the global filter (again, the one under `[mister]`).

If you want to use the global filter terms and add database-specific terms, include the special term `[mister]` in the database-specific filter. For example, if the global filter under `[mister]` is `filter = console computer` and the `[distribution_mister]` filter is `filter = [mister] arcade`, the database-specific filter will inherit terms from the global filter and add the arcade term. The resulting filter will be `filter = console computer arcade`.

### Porting filters from the old Updater

Most of the terms from [this list](https://github.com/MiSTer-devel/Distribution_MiSTer#tags-that-you-may-use-with-download-filters-feature), are the same terms that you could use in the filters from the old updater. That means, for the most part, filters are compatible with the old updater format. Thus, the transition is very straightforward, as you can see in this video:

https://www.youtube.com/watch?v=0gdr5Vv3obc
