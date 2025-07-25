cwlVersion: v1.2
class: Workflow

$namespaces:
  s: https://schema.org/

$schemas:
 - https://schema.org/version/latest/schemaorg-current-http.rdf

s:author:
  - class: s:Person
    s:identifier: https://orcid.org/0000-0001-9290-2017
    s:email: mailto:iacopo.colonnelli@unito.it
    s:name: Iacopo Colonnelli

s:codeRepository: https://github.com/alpha-unito/cwl-1000genome-workflow
s:dateCreated: "2022-09-28"
s:license: https://spdx.org/licenses/Apache-2.0

requirements:
  ScatterFeatureRequirement: {}
  SubworkflowFeatureRequirement: {}

inputs:
  columns_file: File
  populations: File[]
  sift_files: File[]
  snp_files: File[]
  step: int
  total: int

outputs:
  overlap_files:
    type:
      type: array
      items:
        type: array
        items: File
    outputSource: chromosome/overlap_files
  freq_files:
    type:
      type: array
      items:
        type: array
        items: File
    outputSource: chromosome/freq_files

steps:
  chromosome:
    in:
        columns_file: columns_file
        step: step
        populations: populations
        sift_file: sift_files
        snp_file: snp_files
        total: total
    scatter: [ sift_file, snp_file ]
    scatterMethod: dotproduct
    out: [overlap_files, freq_files]
    run:
      class: Workflow
      inputs:
        columns_file: File
        step: int
        populations: File[]
        sift_file: File
        snp_file: File
        total: int
      outputs:
        overlap_files:
          type: File[]
          outputSource: mutation_overlap/output_file
        freq_files:
          type: File[]
          outputSource: frequency/output_file
      steps:
        get_chromosome:
          in:
            snp_file: snp_file
          out: [chromosome]
          run: clt/get_chromosome.cwl
        get_intervals:
          in:
            step: step
            total: total
          out: [counters, stops]
          run: clt/get_intervals.cwl
        individuals:
          in:
            input_file: snp_file
            columns_file: columns_file
            chromosome: get_chromosome/chromosome
            counter: get_intervals/counters
            stop: get_intervals/stops
            total: total
          scatter:
            - counter
            - stop
          scatterMethod: dotproduct
          out: [output_file]
          run: clt/individuals.cwl
        individuals_merge:
          in:
            chromosome: get_chromosome/chromosome
            individuals: individuals/output_file
          out: [output_file]
          run: clt/individuals_merge.cwl
        sifting:
          in:
            input_file: sift_file
            chromosome: get_chromosome/chromosome
          out: [output_file]
          run: clt/sifting.cwl
        mutation_overlap:
          in:
            input_file: individuals_merge/output_file
            chromosome: get_chromosome/chromosome
            population: populations
            sift_file: sifting/output_file
            columns_file: columns_file
          scatter: population
          out: [output_file]
          run: clt/mutation_overlap.cwl
        frequency:
          in:
            input_file: individuals_merge/output_file
            chromosome: get_chromosome/chromosome
            population: populations
            sift_file: sifting/output_file
            columns_file: columns_file
          scatter: population
          out: [output_file]
          run: clt/frequency.cwl
