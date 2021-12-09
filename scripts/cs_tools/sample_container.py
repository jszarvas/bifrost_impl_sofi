from pathlib import Path
from typing import Iterable


class SampleContainer:
    _species: str
    _sample_list_path: Path
    _samples: dict = {}

    def __init__(self, species: str, sample_list_path: Path):
        if ' ' in species:
            raise ValueError("species cannot contain blanks - please use '_' instead.")
        self._species = species
        self._sample_list_path = sample_list_path
        if self._sample_list_path.exists():
            print(f"Reading sample list in {str(self._sample_list_path)}")
            with open(self._sample_list_path, 'r') as sample_list:
                for (sample_name, file1, file2) in self.read_sample_list(sample_list):
                    if sample_name == 'sample':  # ignore header
                        continue
                    self.add_sample(sample_name, file1, file2)
        else:
            print(f"{str(self._sample_list_path)} did not exist, but will be created")

    def read_sample_list(self, sample_list):
        output = list()
        while True:
            try:
                line: str = next(sample_list)
                if len(line) > 1:  # If not in last line (which should only contain a '\n')
                    sample_name, file1, file2 = line.rstrip().split('\t')
                    output.append((sample_name, file1, file2))
            except StopIteration:
                break
        return output

    def add_sample(self, sample_name: str, file1: str, file2: str):
        self._samples[sample_name] = (file1, file2)

    def list_samples(self):
        items = ((k, v[0], v[1]) for k, v in self._samples.items())
        return items

    def save(self):
        with open(self._sample_list_path, 'w') as sample_list:
            sample_list.write('sample\tfq1\tfq2\n')
            for k, v in self._samples.items():
                line = '\t'.join((k, str(v[0]), str(v[1]))) + '\n'
                sample_list.write(line)
            sample_list.write('\n')
            
    def find_new_samples(self, fastq_dir: Path, metadata_file: Path):
        """
        Find samples of species in folder fastq_dir by reading metadata file.
        Species is filtered by the second column.
        Return a list of (sequence_id, file1, file2) where file1, file2 have full paths.
        """
        output = list()
        with open(metadata_file, 'r') as run_metadata_tsv:
            next(run_metadata_tsv)  # Ignore header
            for line in run_metadata_tsv:
                if line == '\n':  # Ignore blank lines
                    continue
                sample = line.rstrip().split('\t')
                try:
                    sample_species = sample[1]
                    if sample_species.replace(' ', '_') != self._species:
                        continue
                    sequence_id = sample[6]
                    file1_filename, file2_filename = sample[7].split('/')
                except (KeyError, IndexError) as e:
                    print(f"Error processing metadata file in {fastq_dir}. The thrown exception was:")
                    print(e)
                    print("The faulty sample was:")
                    print(sample)
                    print("Skipping the whole folder!")
                    return None
                file1_full_path = fastq_dir.joinpath(file1_filename)
                file2_full_path = fastq_dir.joinpath(file2_filename)
                try:
                    assert file1_full_path.exists()
                    assert file2_full_path.exists()
                    output.append((sequence_id, file1_full_path, file2_full_path))
                except AssertionError:
                    print("Error: one or both of these files do not exist:")
                    print(file1_full_path)
                    print(file2_full_path)
                    print("Skipping the whole folder!")
                    return None
        return output

    def print_samples(self, sample_iter: Iterable):
        print("(Sequence ID , File 1)")
        for sample in sample_iter:
            print(sample[0], sample[1])

    def maintain(self, fastq_dir: Path) -> bool:
        metadata_file = Path(fastq_dir.joinpath('run_metadata.tsv'))
        if not metadata_file.exists():
            print(f"Metadata file {metadata_file} does not exist - ignoring folder")
            return False
        fastq_dir = Path(fastq_dir)
        species = str(self._species).replace('_', ' ')
        new_samples = self.find_new_samples(fastq_dir, metadata_file)
        if new_samples is None:
            return False
        if len(new_samples) == 0:
            print(f"No {species} samples found in {fastq_dir}")
        else:
            print(f"{species} samples found:")
            self.print_samples(new_samples)
            for new_sample in new_samples:
                self.add_sample(*new_sample)
            self.save()
        return True
