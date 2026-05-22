#/usr/bin/bash
DB=../backend/data/EBI-PDB
cd $DB
mkdir tmp_index
wget https://files.rcsb.org/pub/pdb/derived_data/pdb_seqres.txt.gz -O pdb_seqres.fasta.gz 
gunzip pdb_seqres.fasta.gz -f
../../soft/UNIX/blast+/bin/makeblastdb -in  pdb_seqres.fasta -dbtype prot   -parse_seqids -title "PDB Sequence Database" -out blast 
../../soft/mmseq2/mmseqs createdb  pdb_seqres.fasta mmseq2 
../../soft/mmseq2/mmseqs createindex mmseq2 tmp_index --threads 100 
rm -rf tmp_index
