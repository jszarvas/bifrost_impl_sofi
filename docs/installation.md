# Installation

1. Clone https://github.com/ssi-dk/test_app_computerome into a directory.

2. Create settings/env_vars.sh and settings/singularity_settings.sh from the templates (or copy from an existing installation)
   and edit them to fit the new installation.

3. Go to scripts/singularity and run qsub download_current_images.sh

4. Set up cron job to execute scripts/cron_run.sh

5. Possibly set up relevant indexes on DB