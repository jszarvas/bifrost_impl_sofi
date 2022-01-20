# Bifrost command flow (TODO: make this more elaborated)

cron -> cron_run.sh -> start.sh
start.sh (sources env_vars.sh) -> $BIFROST_CONFIG_DIR/check_and_launch_runs.py

## check_and_launch_runs.py
Main launcher that contains logic of which samples should be processed

checks input folders: $BIFROST_RAW_DATA_MNT/20\d\d/Run_name

compares to output folders $BIFROST_OUTPUT_DIR/20\d\d/Run_name

if input directory does not have a corresponding output directory, launch bifrost like this:

`qsub -F year, run_name, config_dir $BIFROST_CONFIG_DIR/launch_bifrost.sh`

## launch_bifrost.sh
- creates run_directory = output directory
- links input directory to $BIFROST_OUTPUT_DIR/samples.
- runs bifrost_run_launcher component through singularity
  - initializes run and samples in DB (in initialize_run of pipeline.py)
  - creates run_script.sh
- executes run_script.sh

## bifrost_run_launcher component
run_pipeline\
controls flow

initialize_run\
Initializes run and samples in the bifrost database

generate_run_script\
Creates run_script.sh to launch remaining components from Pre, Per and Post scripts in config dir

### How to call bifrost_run_launcher
```
singularity run \
    -B $BIFROST_RUN_DIR,$BIFROST_CONFIG_DIR,$BIFROST_READS_DIR \
    --userns \
    $BIFROST_IMAGE_DIR/bifrost_run_launcher__v2_2_3__ \
        -pre $BIFROST_CONFIG_DIR/launcher_scripts/pre.sh \
        -per $BIFROST_CONFIG_DIR/launcher_scripts/per.sh \
        -post $BIFROST_CONFIG_DIR/launcher_scripts/post.sh \
        -colmap $BIFROST_CONFIG_DIR/colmap.json \
        -reads $BIFROST_RUN_DIR/samples \
        -meta $BIFROST_READS_DIR/run_metadata.tsv \
        -name $BIFROST_RUN_NAME \
        -out $BIFROST_RUN_DIR
```

## run_script.sh
Launches components to queue system
