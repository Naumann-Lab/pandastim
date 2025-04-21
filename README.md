# pandastim
<img align = "right" width = "120" src=".\resources\omr_sin_example.png ">


###  Live exists as fake "static typing" and requires python 3.10+, enabled on behavior rigs with freely swimming eye tracking



Cross-platform Python package for generating visual stimuli using the [Panda3d](https://www.panda3d.org/) library, a Python game-engine developed by Disney.

### Installation
This assumes you are using Anaconda and Python 3:

    conda create --name pstim
    conda activate pstim
    conda install numpy scipy matplotlib zeromq
    pip install panda3d zmq pandas qdarkstyle

Once you've got your environment squared away, you can install pandastim by heading to the directory where you want it installed, and run:    

    git clone https://github.com/Naumann-Lab/pandastim.git
    
To test the installation, try running one of the examples in [examples/)


### Stytra Requirement
Adapted Stytra from the Vilim Štih et al. @portugueslab
Modified Stytra included in the stytra folder, but needs to be moved outside of the pandastim folder when installed
