source $BASE_DIR/settings/env_vars.sh
module load $ANACONDA_VERSION

python $BIFROST_SCRIPT_DIR/xlsx2csv/xlsx2csv.py -d 'tab' -f '%d-%m-%y' sofi_metadata.xlsx > sofi_metadata.tsv
python $BIFROST_SCRIPT_DIR/change_species.py -meta sofi_metadata.tsv -out sofi_metadata.tsv
