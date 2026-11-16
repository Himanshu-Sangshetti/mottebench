# Data licence

**Code** (everything under `runner/`, `grading/`, `analysis/`, `data/build/`, `site/`, `viewer/`, `report/build.sh`) is released
under the MIT License; see [LICENSE](LICENSE).

**Data and text** created for this project are released under the
[Creative Commons Attribution 4.0 International licence (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/):
the questions, the evidence-class assignments, the conversation scripts, the judge and human labels, the analysis tables,
the paper and the website. Please cite MotteBench (see the README) when you use them.

## Third-party material

- **USPSTF recommendations** and **What Works Clearinghouse ratings** are works of the US federal government and are in the
  public domain in the United States. We copy the grade or rating and link to the official page.
- **Cochrane reviews** are copyright of their publishers. We do not redistribute review abstracts; `data/sources/cochrane/fetch.py`
  downloads them from PubMed for your own use. Each item stores the certainty rating and, for strong items, one short result
  sentence quoted from the abstract with a link to the source.
- **Model outputs** in `results/` and `traces/` were generated through each provider's interface (Anthropic, OpenAI, DeepSeek
  through OpenRouter; Llama 3.1 8B run locally under the Llama 3.1 Community License). They are shared for research and
  evaluation. Your use of them is also subject to the respective provider's terms.
- **The State of the Field review** (Ben N and Alex Csaky, LessWrong) is quoted briefly and cited; it is not redistributed.

The answer keys describe what official bodies concluded about the evidence. Nothing in this repository is medical or
educational advice.
