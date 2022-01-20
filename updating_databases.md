# Updating component databases
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
