cwlVersion: v1.2
class: ExpressionTool

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
s:programmingLanguage: JavaScript

requirements:
  InlineJavascriptRequirement: {}

inputs:
  lists:
    type:
      type: array
      items:
        type: array
        items: File

outputs:
  files:
    type:
      type: array
      items:
        type: array
        items: File 

expression: |
  ${
    return {"files": inputs.lists};
  }
