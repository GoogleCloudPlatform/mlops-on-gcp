# Scheduling log analyzer runs

This folder contains a simple CLI - `dms` - designed to facilitate triggering and scheduling of the Log Analyzer runs.

The `dms` CLI supports to commands: 
- `run` - The `run` command triggers an immediate run of the Log Analyzer template
- `schedule` - The `schedule` command schedules a future run of the Log Analyzer template. The `schedule` command relies on **Cloud Tasks** for managing the scheduling and execution of future runs. Before the `schedule` command can be used a **Cloud Tasks** queue and an associated service account must be set up - the setup instructions to follow.

To install the utility, execute `pip install --editable .` from this folder. After the installation is completed, type `dms --help` for more information.

