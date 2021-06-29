#!/usr/bin/env python3
import pandas as pd
import argparse


def parse_args() -> object:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument('-meta', '--run_metadata_tsv',
                        required=True,
                        help='Meta data to be translated')
    parser.add_argument('-out', '--output',
                        required=True,
                        help='Output file')
    args: argparse.Namespace = parser.parse_args()
    species_convert(args)

def species_convert(args: object) -> None:
    species_translation_dict = {
        "A.baumannii": "Acinetobacter baumannii",
        "B.pertussis": "Bordetella pertussis",
        "C.coli": "Campylobacter coli",
        "C.jejuni": "Campylobacter jejuni",
        "C.freundii": "Citrobacter freundii",
        "C.difficile": "Clostridioides difficile",
        "Cronobacter": "Cronobacter sakazakii",
        "E.faecalis": "Enterococcus faecalis",
        "E.faecium": "Enterococcus faecium",
        "E.coli": "Escherichia coli",
        "H.influenzae": "Haemophilus influenzae",
        "K.oxytoca": "Klebsiella oxytoca",
        "K.pneumoniae": "Klebsiella pneumoniae",
        "K.variicola": "Klebsiella variicola",
        "L.pneumophila": "Legionella pneumophila",
        "Listeria": "Listeria monocytogenes",
        "N.gonorrhoeae": "Neisseria gonorrhoeae",
        "Meningococcus": "Neisseria meningitidis",
        "P.aeruginosa": "Pseudomonas aeruginosa",
        "Salmonella": "Salmonella enterica",
        "S.aureus": "Staphylococcus aureus",
        "S.capitis": "Staphylococcus capitis",
        "S.epidermidis": "Staphylococcus epidermidis",
        "S.pseudintermedius": "Staphylococcus pseudintermedius",
        "S.sciuri": "Staphylococcus sciuri",
        "S.simulans": "Staphylococcus simulans",
        "S.xylosus": "Staphylococcus xylosus",
        "S.agalactiae": "Streptococcus agalactiae",
        "S.pneumoniae": "Streptococcus pneumoniae",
        "S.pseudopneumoniae": "Streptococcus pseudopneumoniae",
        "Gr.A.Streptococcus": "Streptococcus pyogenes",
        "Y.aleksiciae": "Yersinia aleksiciae",
        "Yersinia": "Yersinia enterocolitica",
        "C.perfringens": "Clostridium perfringens",
        "E.cloacae": "Enterobacter cloacae",
        "S.lugdunensis": "Staphylococcus lugdunensis",
        "C.butyricum": "Clostridium butyricum",
        "S.uberis": "Streptococcus uberis",
        "V.vulnificus": "Vibrio vulnificus",
        "B.cereus": "Bacillus cereus",
        "S.sonnei": "Shigella sonnei",
        "V.cholerae": "Vibrio cholerae",
        "A.pittii": "Acinetobacter pittii",
        "A.phocae": "Arcanobacterium phocae",
        "P.stuartii": "Providencia stuartii",
        "S.equi": "Streptococcus equi",
        "C.farmeri": "Citrobacter farmeri",
        "C.botulinum": "Clostridium botulinum",
        "C.diphtheriae": "Corynebacterium diphtheriae",
        "A.pleuropneumoniae": "Actinobacillus pleuropneumoniae",
        "S.hyicus": "Staphylococcus hyicus",
        "S.chromogenes": "Staphylococcus chromogenes",
        "S.vitulinus": "Staphylococcus vitulinus",
        "P.mirabilis": "Proteus mirabilis",
        "F.tularensis": "Francisella tularensis",
        "K.aerogenes": "Klebsiella aerogenes",
        "P.rettgeri": "Providencia rettgeri",
        "B.melitensis": "Brucella melitensis",
        "M.tuberculosis": "Mycobacterium tuberculosis",
        "S.agnetis": "Staphylococcus agnetis",
        "S.haemolyticus": "Staphylococcus haemolyticus",
        "S.lentus": "Staphylococcus lentus",
        "S.arlettae": "Staphylococcus arlettae",
        "S.equorum": "Staphylococcus equorum",
        "N.nova": "Nocardia nova",
        "B.cepacia": "Burkholderia cepacia",
        "C.mobile": "Carnobacterium mobile",
        "J.arthritidis": "Jeotgalibaca arthritidis",
        "J.porci": "Jeotgalibaca porci",
        "V.parahaemolyticus": "Vibrio parahaemolyticus",
        "P.lautus ": "Paenibacillus lautus ",
        "P.odeiifer": "Paenibacillus",
        "M.arosiense": "Mycobacterium arosiense",
        "K.quasipneumoniae": "Klebsiella quasipneumoniae",
        "M.morganii": "Morganella morganii",
        "S.anginosus": "Streptococcus anginosus",
        "S.mutans": "Streptococcus mutans",
        "S.warneri": "Staphylococcus warneri",
        "A.ursingii": "Acinetobacter ursingii",
        "B.pseudomallei": "Burkholderia pseudomallei",
        "A.urinae": "Aerococcus urinae",
        "S.gordonii": "Streptococcus gordonii",
        "C.ulcerans": "Corynebacterium ulcerans",
        "S.simiae": "Staphylococcus simiae",
        "C.fetus": "Campylobacter fetus",
        "L.adecarboxylata": "Leclercia adecarboxylata",
        "L.lactis": "Lactococcus lactis",
        "C.koseri": "Citrobacter koseri",
        "A.johnsonii": "Acinetobacter johnsonii"
    }

    capital_species_translation_dict = {}
    for key in species_translation_dict:
        capital_species_translation_dict[str(key).upper()] = species_translation_dict[key]

    df = pd.read_table(args.run_metadata_tsv)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    sample_key = "SampleID"
    samples_no_index = df[df[sample_key].isna()].index
    df = df.drop(samples_no_index)

    if key in ("Organism", "provided species"):
        try:
            df["Organism"] = df["Organism"].str.replace(" ", "").str.upper().map(capital_species_translation_dict)
        except KeyError:
            pass
    df.to_csv(args.output, sep="\t", index=False)

if __name__ == "__main__":
    parse_args()
