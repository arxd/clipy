# Environment

This is a broad term, and often used interchangeably with [targets](configuration.md#page-config), but it is a different concept in clipy.
An environment is *where* cli.py is being executed and what it can import.

* Is it running in a development environment on your laptop?
* Is it running in a docker container executing a specific tooling function?
* Is it running on the production server or device?

The environment determines which modules python has access to, as well as other things like network access.
In a dev environment you might need a different set of modules from the prod environment.
Are you running with a python venv, or using the system python?

Which modules are available determines which commands are executable in an environment.
Because, obviously, if the command can’t import the modules it needs, then it can’t run.

There is a distinction to be made between the ability to import a command, and run a command.
Even if you can’t run a command (because of a missing libary), it is helpful to be able to import the command so that you can read, and display, its help documentation.
The local/dev environment is where the user interacts dynamically with cli.py, so in that environment, all commands need to be importable (even if not runnable) so that documentation can be generated.
In other environments, like production, it may be fine if you can’t import all commands, since only a subset of the commands may be used.
