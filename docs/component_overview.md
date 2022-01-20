# Bifrost component overview

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
