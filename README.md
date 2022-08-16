# The  standardised environment for the hippocampus and entorhinal cortex models. 
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-3-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->



* [1 Introduction](#1-Introduction)
* [2 Installation ](#2-Installation)
* [3 The Project](#3-Project)
* [4 How to Contribute](#4-Contribute)
* [5 Cite ](#5-Cite)

## 1. Introduction

This framework will allow neuroscientists to easily contrast the different hippocampus and entorhinal cortex models against experimental observations. This new tool aims at standardising the methods of building and comparing models as well as reporting empirical evidences. The code is constructed of two main classes, an agent class and an environment class.  The agent can be thought of as the animal performing the experiment, and the environment as where the animal navigates and performs a task.  These two classes are allowed to interact to reproduce the full experimental setting.

We create this framework with the perspective that the neuroscience community should be able to continue its development by increasing the databases of model and experimental results without our intervention. Therefore, the software is made easy to use, facilitating future growth. This new environment will revolutionize how theoretical models are proposed in neuroscience and push for easy access and implementation of new ideas. 

## 2. Installation
For now, install using pip for local editing and testing
```
pip install --upgrade setuptools wheel 
python setup.py sdist bdist_wheel
pip install -e .
```


## 3. Project

Please refere to the Documents/ROADMAP.md to understand the state of the project and get an idea of the direction it is going in.
#### How to Run 

#### How to Run the comparaison board


## 4. Contribute

There are many ways to contribute to the porject. 
 1. Implement an hippocampal and entorhinal cortex models of your choice. ([Agent](https://github.com/ClementineDomine/EHC_model_comparison/tree/main/sehec/models))
    
    2. Add functionality to the Comparison Board to compare results to real experimental data. (Comparaison Board)
    
    
    3. Work on improving the environment ([Environement](https://github.com/ClementineDomine/EHC_model_comparison/tree/main/sehec/envs/arena))
    
    4. Add an experimental data set ([Experiment](https://github.com/ClementineDomine/EHC_model_comparison/tree/main/sehec/envs/experiment))

All contribution should be sumbited through a pull request that we will later acess. 
Before sending a pull request make sure you have: 

1.Checked the Lisencing frameworks. 

2. Followed them [Style Guide](https://github.com/ClementineDomine/EHC_model_comparison/tree/main/Documents).

3. Implemented and ran [Test](https://github.com/ClementineDomine/EHC_model_comparison/tree/main/sehec/test).

4. Commented your work 
    
All contributions to the repository are acknowledged through the all-contributors bot and in future publicaiton.
Refere to the README.md files found in each the modules for further details on how to contibute to them.


### 5. Cite 

See Documents/Citation for correct citation of this framework. 

## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tr>
    <td align="center"><a href="https://github.com/ClementineDomine"><img src="https://avatars.githubusercontent.com/u/18595111?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Clementine Domine</b></sub></a><br /><a href="#design-ClementineDomine" title="Design">🎨</a> <a href="#mentoring-ClementineDomine" title="Mentoring">🧑‍🏫</a></td>
    <td align="center"><a href="https://github.com/rodrigcd"><img src="https://avatars.githubusercontent.com/u/22643681?v=4?s=100" width="100px;" alt=""/><br /><sub><b>rodrigcd</b></sub></a><br /><a href="#design-rodrigcd" title="Design">🎨</a><a href="#mentoring-ClementineDomine" title="Mentoring">🧑‍🏫</a></td>
    <td align="center"><a href="https://github.com/LukeHollingsworth"><img src="https://avatars.githubusercontent.com/u/93782020?v=4?s=100" width="100px;" alt=""/><br /><sub><b>Luke Hollingsworth</b></sub></a><br /><a href="https://github.com/ClementineDomine/EHC_model_comparison/commits?author=LukeHollingsworth" title="Documentation">📖</a></td>
  </tr>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!
