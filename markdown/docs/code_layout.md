# cli.py

This is the main, executable, entrypoint that defines the root command.

The first thing it does when run is to check the [Environment](environment.md) and make sure of the following.

* Are we running in a venv?  If not, should we be?
* Do we have the bare-minimum modules to import the commands that should be viewable from this environment?

After those two conditions are met, it hands control over to the command execution engine.

You should be able to clone any project and run `./cli.py -h` to see everything that can be done with the project.
