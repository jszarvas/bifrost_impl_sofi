# bifrost_impl_sofi

Bifrost implementation scripts for SOFI.

This repo was formerly named "test_app_computerome".

## Rerun components
To rerun specific samples and components across the Surveillance of Food-bourne Infections (SOFI) platform, the pipeline includes.
1. Building a config file that specifies what to rerun
2. A rerunning pipeline taking the created config file and based on the information, creates a qsub job with specified resources which runs a snakemake command for any given information.

There are two approaches of generating the config file 
### Auto-discover from mongoDB 
By connecting to the mongoDB using a query, its possible to extract different documents across different collections, and rerunning those

List database names to check proper connection
```
python connect_db.py --dbname

succesfully connected to MongoDB
Available databases:
- sofi-dev
```

List collcetions within a given database to identify which collection to query
```
python connect_db.py --dbname sofi-dev --collectionname

succesfully connected to MongoDB
Available collections in sofi-dev:
- projects
- sap_lims_metadata
- samples
- users
- sap_analysis_results
- products
- sample_components
- accounts
- sap_tbr_metadata
- results_debug
- nearest_neighbors
- debug
- sofi_species_to_mlstschema_mapping
- verification_tokens
- fs.chunks
- fs.files
- hpc_jobs
- components
- tree_calculations
- sap_broker_queue
- dist_calculations
- workspaces
- records
- snp
- runs
- sap_pii
- results_snp
```

Query the database and collection, storing it in a json format for development purpose
```
python connect_db.py --dbname sofi-dev --collectionname samples --query "{'name':'test_ecoli_single___1704H39235'}" --json ecolitest.json
```

Query the database and collection creating the correct config format for rerunning pipeline

#### one sample - based on name
```
python connect_db.py --dbname sofi-dev --collectionname samples --query "{'name':'test_ecoli_single___1704H39235'}" --create_config --output configs/test_ecoli_single___1704H39235_config.yaml

Successfully connected to MongoDB.
Query matched 1 document(s).
Config file 'configs/test_ecoli_single___1704H39235_config.yaml' created successfully.
```

#### several samples - based on partial match on names
```
python connect_db.py --dbname sofi-dev --collectionname samples --query "{\"name\": {\"\$regex\": \"testrun_ec\", \"\$options\": \"i\"}}" --create_config --output configs/testrun_ec_config.yaml

Successfully connected to MongoDB.
Query matched 21 document(s).
Config file 'configs/testrun_ec_config.yaml' created successfully.
```
#### several sample - based on species
```
python connect_db.py --dbname sofi-dev --collectionname samples --query "{\"categories.sample_info.summary.provided_species\": {\"\$regex\": \"Escherichia coli\", \"\$options\": \"i\"}}" --create_config --output configs/ecoli_provided_species.yaml

Successfully connected to MongoDB.
Query matched 24 document(s).
Config file 'configs/ecoli_provided_species.yaml' created successfully.
```
#### Validate config file structure
```
python validate_configs.py configs/testrun_ec_config.yaml configs/test_ecoli_single___1704H39235_config.yaml

[OK]     configs/testrun_ec_config.yaml
[OK]     configs/test_ecoli_single___1704H39235_config.yaml
```



### Manual control of samples and components
