source /home/projects/fvst_ssi_dtu/test_apps/settings/env_vars.sh
module load $ANACONDA_VERSION

python $BIFROST_SCRIPT_DIR/xlsx2csv/xlsx2csv.py -d 'tab' -f '%d-%m-%y' run_metadata.xlsx > run_metadata.tsv
python $BIFROST_SCRIPT_DIR/change_species.py -meta run_metadata.tsv -out run_metadata.tsv
