# bifrost_impl_sofi

Bifrost implementation scripts for SOFI.

This repo was formerly named "test_app_computerome".

## Bifrost command flow

cron -> cron_run.sh -> start.sh

start.sh (sources env_vars.sh) -> $BIFROST_CONFIG_DIR/check_and_launch_runs.py

### check_and_launch_runs.py
Main launcher that contains logic of which samples should be processed

checks input folders: $BIFROST_RAW_DATA_MNT/20\d\d/Run_name

compares to output folders $BIFROST_OUTPUT_DIR/20\d\d/Run_name

if input directory does not have a corresponding output directory, launch bifrost:
qsub -F year, run_name, config_dir $BIFROST_CONFIG_DIR/launch_bifrost.sh

### launch_bifrost.sh
- creates run_directory = output directory
- links input directory to $BIFROST_OUTPUT_DIR/samples.
- runs bifrost_run_launcher component through singularity
  - initializes run and samples in DB (in initialize_run of pipeline.py)
  - creates run_script.sh
- executes run_script.sh

### bifrost_run_launcher component
run_pipeline\
controls flow

initialize_run\
Initializes run and samples in the bifrost database

generate_run_script\
Creates run_script.sh to launch remaining components from Pre, Per and Post scripts in config dir

#### How to call bifrost_run_launcher
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

### run_script.sh
Launches components to queue system



## Bifrost component Overview

pipeline.smk contains the component specific commands. For simple components, this is the only thing that needs editing.

launcher.py runs snakemake, which processes pipeline.smk - so launcher.py is where to set up any additional snakemake options.

launcher.py is again launched from __main__.py, which is set as the entrypoint in the Dockerfile.
The dockerfile also sets up the docker build environment with all the requirements, as well as the entrypoint for execution. 

For testing and local execution bifrost components have their docker setup defined in docker-compose.yaml in the main Bifrost repo. 
This setup includes 
 - build information (which usually don't need to be changed between components)
 - runtime information
   - mounted volumes (file system points that should be accessible)
   - environment variables
   - dependencies (on bifrost_db)
   - default entry point (set up for testing)

On computerome the same is handled by the run launcher and specifically the run scripts (/scripts/runscripts/per.sh).


## Updating component databases
Resfinder, mlst, virulencefinder, and plasmidfinder all have 'databases' associated with them which are a list of genes. Thiese lists are periodically upded with new variants or genes based off ongoing research. We will be using the ones based on CGE going forward. You can see an example of this at:
bifrost_cge_resfinder/Dockerfile at 35883b968d7b81f633c165253be0895e859a3325 · ssi-dk/bifrost_cge_resfinder (github.com)

where there is the following
``` 
RUN \ 
    git clone https://git@bitbucket.org/genomicepidemiology/resfinder_db.git && \
    cd resfinder_db && \ 
    git checkout 3bfc4a3 && \
    python3 INSTALL.py kma_index;
```
The checkout here is based on a hash and the date of the hash is recoded into the config.yml as the resource version. This is currently a manual process. So when a database needs to be updated the checkout should point to a newer hash and the resource version updated as well. In terms of the docker images on DockerHub you'll see this in components that use this with v(code version)__(resource version). All databases should now be placed in /bifrost/components/(component_name)/resources/ which is a path determined in the dockerfile and accessed via the config.yaml.
