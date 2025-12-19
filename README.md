# pandastim
<img align = "right" width = "120" src=".\resources\omr_sin_example.png ">


###  Legacy pandastim runs sans-stimbuddy on behavior rigs and such
###  Live exists as fake "static typing" and requires python 3.10+



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


### Notes on stim protocols
'all_omr_stims.hdf' - inverted on Bruker scope, 20 unique stims (cardinal, intercard, eye-specific, shearing), spatial freq = 70, speed is 0.025 mm/s
'sixteenstim.hdf' - need to check if inverted on scope, 14 unique stims (cardinal, intercard, eye-specific)
'forward_speed_tuning.hdf' - only forward gratings, different speeds, spatial freq = 70, speeds are 0.025, 0.04, 0.055 m/s