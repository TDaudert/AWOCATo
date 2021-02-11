# A Web-based Collaborative Annotation and Consolidation Tool (AWOCATo)

AWOCATo is a web-based annotation and consolidation tool for texts specifically designed to support a smooth annotation experience for researchers, annotators, and consolidators. It is developed in a modular way and supports the display of different front-ends. AWOCATo currently supports the following modi (with the corresponding features):
- Fine-grained scoring (aimed at sentiment analysis, however, it can be used for other floating point annotations. Features two fine-grained scores and textual spans)
- Sentiment-news (presents two texts (i.e. title and body). Features two fine-grained scores and textual spans)
- Binary classification
- Ternary classification
- Textual annotation (including spans)

Besides providing different annotation modi, AWOCATo also comes with a functionality to consolidate the annotations. While switching between annotation and consolidation only requires to change one binary variable in the configuration file, the front-end is replaced and users logging-in are presented with previously annotated texts. Further, AWOCATo accepts certain parameters such as the standard deviation and the minimum of required annotations and consolidates all texts satisfying these parameters automatically upfront. More information regarding technical specifications are stated in [configuration_manual.pdf](https://github.com/TDaudert/AWOCATo/blob/master/configuration_manual.pdf). A fast overview about how to start with AWOCATo is given in [quickstart.pdf](https://github.com/TDaudert/AWOCATo/blob/master/quickstart.pdf).

Graphical examples and a description of the interface can be found in the [original paper](https://www.aclweb.org/anthology/2020.lrec-1.872.pdf). 

## AWOCATo Structure

AWOCATo files come in the following structure. 

<img src="https://github.com/TDaudert/AWOCATo/blob/master/AWOCATo_structure.png"  width="250">


## Reference 
If you are using AWOCATo in your research, please don't forget to cite [this paper](https://www.aclweb.org/anthology/2020.lrec-1.872.pdf):

~~~
@inproceedings{daudert2020web,
  title={A Web-based Collaborative Annotation and Consolidation Tool},
  author={Daudert, Tobias},
  booktitle={Proceedings of The 12th Language Resources and Evaluation Conference},
  pages={7053--7059},
  month = "5 " # may,
  year={2020},
  address = "Marseille, France",
  url = "https://www.aclweb.org/anthology/2020.lrec-1.872.pdf"
}
~~~
## License 
This tool is openly available for non-commercial use under the [Attribution-NonCommercial-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Contact 
If you have any questions or suggestions, you can contact Tobias Daudert (tobias.daudert@insight-centre.org).

## Disclaimer 
AWOCATo is an experimental software designed to aid research. The author is not responsible for any damages related to or inflicted by its use.