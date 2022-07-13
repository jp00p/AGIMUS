# Welcome to the AGIMUS Contribution Guide! ✨

Thank you for your interest in contributing to the AGIMUS project for [The USS Hood](https://drunkshimoda.com), a Discord server for the "Friends of DeSoto" aka Fans of [The Greatest Trek](https://gagh.biz) family of podcasts!

AGIMUS is our Discord bot and handles a lot of functionality for the server such as automatically assigning roles when folks introduce themselves, granting XP for fun rewards, and then some strange wacky stuff like automatically changing the color of some lights in the project founder jp00p's room when new messages are received.

In this guide you'll get an overview of the contribution workflow from opening issues, creating PRs, and submitting contributions for inclusion in the project!


## Getting Started

First thing's first, it's a good idea to familiarize yourself with the general project. Even if you won't be doing any coding yourself, a thorough read of the main [README](README.md) is recommended and contains some good overall information about what the bot can currently do.

If you have any questions or need some help, feel free to reach out on the Discord server in the [**"#megalomaniacal-computer-storage"**](https://discord.com/channels/689512841887481875/994412232052052089) channel!

## Getting Set Up With Github

To contribute to the project you'll need a Github account! The signup process is pretty simple and what you'd usually expect, you can start it at their [Signup Page](https://github.com/signup).

All kinds of help with Github itself can be found on their [docs site](https://docs.github.com).

### So What The Heck Is A PR?

A "PR" means a **Pull Request** and is terminology used in programming and Github specifically to indicate that you have changes that you'd like merged into the main code project.

Don't worry though, if you'd like to contribute documentation or general ideas you won't have to touch a single line of code!

### Forking

In order to create a new PR with your changes (code or otherwise), you'll need to "Fork" the repository. This means that you will create a new version of the repository within your own Github account that tracks the main repo. Changes you make to your Fork can then be submitted for inclusion in the main project.

Forking the repo can be done at the top right of the [main project page](https://github.com/jp00p/AGIMUS) by selecting the big ol' Fork button. We'd recommend you keep the default settings the same as what is presented when you do so.

Once done, you'll have a new Fork underneath your account which you can edit without affecting the main repository!

It's recommended before you make any new changes that you'd like to submit, that you Fetch the current main repo state. You can do this by clicking the **"Fetch Upstream"** dropdown button at the top right of your Fork's page and selecting **"Fetch and merge"**. This will bring in any changes from the "upstream" main repo to your Fork so that you are at the same baseline for the new changes you will make.


## Issues

Issues are what we use to track ideas, file bugs, or point out things that may need improvement in the project. You can find the [Issues tab](https://github.com/jp00p/AGIMUS/issues) at the top of the project's [Github page](https://github.com/jp00p/AGIMUS).

### Creating New Issues

If you have some ideas or notice a bug, feel free to submit an issue to track and it will be added to our list of items to tackle.

There are no hard rules on how to format your issue titles/descriptions but just try to be thorough and clear in what the desired resolution should be. [Markdown](https://www.markdownguide.org/basic-syntax) is fully supported and you can add screenshots or images directly into the description field by either dragging them in or by pasting.

### Solving An Issue

You're welcome to scan through our existing issues to find one which may interest you. As a general rule, we don't assign issues to anyone specifically. If you find an issue to work on, you are welcome to open a PR with a fix and reference the Issue # within your description.


## Contributing Documentation

Programmers are notoriously bad at creating and maintaining documentation, if you'd like to help out we'd love it! If you're not aware of how a feature currently works, feel free to submit a new Issue around what seems unclear and what kind of documentation would be useful in understanding it better.

### Markdown

**Markdown** is a syntax for easily formatting text. Markdown files are designated with a `.md` suffix and when viewed on Github will automatically be rendered with the formatting applied. This document itself is written in Markdown and may provide a good example for how to format your own documentation.

Full details on the syntax can be found on the [markdownguide.org site](https://www.markdownguide.org/basic-syntax).

### How To Submit Documentation

Luckily for non-coders, Github has a built-in interface you can use to update documentation files directly through the website!

To do so, navigate to your Fork and then locate the documentation file (typically an `.md`) you'd like to edit. At the top right of the page you should see a small pencil icon you can use to bring up an in-browser text editor you can edit the file with. As a bonus, `.md` files themselves even have a nice 'Preview' tab where you can see how the final text will be rendered.

> To edit this very file you're looking at on your Fork for example, navigate to your Fork and then the 'docs' directory, and then select the 'CONTRIBUTING.md' file.

Once you're happy with your changes navigate to the bottom of the page to the **"Commit changes"** section. Before going further, be sure to select the **"Create a new branch for this commit and start a pull request."** button. Use a descriptive branch name (no spaces) as well as a descriptive commit title and a good summary outlining your changes.

Once you're satisfied, go ahead and click on the **"Propose changes"** button to review your changes. If everything looks good, hit **"Create Pull Request"** and a new PR from your Fork to the main repo will be created! Someone should see it soon, but you can also gives a heads up in the Discord in the [**"#megalomaniacal-computer-storage"**](https://discord.com/channels/689512841887481875/994412232052052089) channel.


## Contributing Code

All code contributions and ideas are welcome! If you're of the nerdy programming type (for a Star Trek Podcast Fan Discord Server!?) please feel free to fork the repo and pull it down experiment with it on your own system.

The [README.md](README.md) should be relatively thorough on what steps need to be taken to get the project up and running, and you're welcome to ping us on the Discord in [**"#megalomaniacal-computer-storage"**](https://discord.com/channels/689512841887481875/994412232052052089) if you run into trouble!
