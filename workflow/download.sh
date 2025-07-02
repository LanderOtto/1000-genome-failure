#!/bin/bash

start=$(date +'%s')

if [ "$#" -ne 1 ]; then
  >&2 echo "Usage: download.sh CHROMOSOMES"
  exit 1
fi

chrs=${1}
workdir=$(pwd)

mkdir -p "${workdir}/data/populations"
cd "${workdir}/data/populations" || exit
populations=("AFR" "ALL" "AMR" "EAS" "EUR" "GBR" "SAS")
for pop in "${populations[@]}"; do
  wget "https://raw.githubusercontent.com/pegasus-isi/1000genome-workflow/master/data/populations/${pop}"
done

mkdir -p "${workdir}/data/20130502/sifting"
cd "${workdir}/data/20130502" || exit
wget "https://raw.githubusercontent.com/pegasus-isi/1000genome-workflow/master/data/20130502/columns.txt"
for i in $(seq 1 "${chrs}"); do
  wget "https://raw.githubusercontent.com/pegasus-isi/1000genome-workflow/master/data/20130502/ALL.chr${i}.250000.vcf.gz"
  gunzip "ALL.chr${i}.250000.vcf.gz"
  wget -O "sifting/ALL.chr${i}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf.gz" \
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/supporting/functional_annotation/filtered/ALL.chr${i}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf.gz"
  gunzip "sifting/ALL.chr${i}.phase3_shapeit2_mvncall_integrated_v5.20130502.sites.annotation.vcf.gz"
done

cd "${workdir}" || exit

end=$(date +'%s')
echo "Done in $((end - start)) seconds."
