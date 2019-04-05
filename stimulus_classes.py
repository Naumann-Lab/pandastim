"""
pandastim/stimulus_classes.py
Classes to present visual stimuli in pandastim
Two main classes: 
    FullFieldStatic() -- show nonmoving textures
    FullFieldDrift() -- show textures that translate on each frame refresh

Part of pandastim package: https://github.com/EricThomson/pandastim 

Component types:
https://www.panda3d.org/reference/python/classpanda3d_1_1core_1_1Texture.html#a81f78fc173dedefe5a049c0aa3eed2c0
    T_unsigned_byte 	(1byte = 8 bits: 0 to 255)
    T_unsigned_short (2 bytes (16 bits): 0 to 65535, but this is platform dependent)
    T_float 	 (floats: not sure if single (32 bit) or double (64 bit))
    T_unsigned_int_24_8 	 (packed: one 24 bit for depth, one 8 bit for stencil)
    T_int 	(signed int)
    T_byte 	(signed byte: from -128 to 127)
    T_short 	(signed short: 2 bytes from -32768 to 32767)
    T_half_float (2 bytes: may sometimes be good if you are inside the 0-1 range)
    T_unsigned_int (4 bytes (32 bits): from 0 to ~4 billion)   

"""
import sys
import numpy as np 
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import Texture, CardMaker, TextureStage
from panda3d.core import WindowProperties, ColorBlendAttrib, TransformState
from direct.showbase import ShowBaseGlobal  #global vars defined by p3d
from direct.task import Task
import textures
from direct.gui.OnscreenText import OnscreenText   #for binocular stim
        
class FullFieldDrift(ShowBase):
    """
    Show drifting texture forever.
    Takes in texture array and other parameters, and shows texture drifting indefinitely.
    Texture array can be grayscale or rgb.
    
    Usage:
        FullFieldStatic(texture_array, 
                        angle = 0, 
                        velocity = 0.1,
                        window_size = 512, 
                        texture_size = 512)
        
    Note(s): 
        Positive angles are clockwise, negative ccw.
        Velocity is in NDC, so 1.0 is the entire window width (i.e., super-fast).
        Make texture_size a power of 2: this makes the GPU happier.
        Textures are automatically scaled to fit window_size.
        The texture array can be np.uint8 or np.uint16, and 2d (gray) or NxNx3 (rgb)
    """
    def __init__(self, texture_array, angle = 0, velocity = 0.1, 
                 window_size = 512, texture_size = 512):
        super().__init__()
        
        self.texture_array = texture_array
        self.texture_dtype = type(self.texture_array.flat[0])
        self.ndims = self.texture_array.ndim
        self.angle = angle
        self.velocity = velocity
        
        #Set window title (need to update with each stim) and size
        self.window_properties = WindowProperties()
        self.window_properties.setSize(window_size, window_size)
        self.window_properties.setTitle("FullFieldDrift")
        ShowBaseGlobal.base.win.requestProperties(self.window_properties)  #base is a panda3d global
        
        #Create texture stage
        self.texture = Texture("stimulus")
               
        #Select Texture ComponentType (e.g., uint8 or whatever)
        if self.texture_dtype == np.uint8:
            self.texture_component_type = Texture.T_unsigned_byte
        elif self.texture_dtype == np.uint16:
            self.texture_component_type = Texture.T_unsigned_short
        
        #Select Texture Format (color or b/w etc)
        if self.ndims == 2:
            self.texture_format = Texture.F_luminance #grayscale
            self.texture.setup2dTexture(texture_size, texture_size, 
                                   self.texture_component_type, self.texture_format)  
            self.texture.setRamImageAs(self.texture_array, "L") 
        elif self.ndims == 3:
            self.texture_format = Texture.F_rgb8
            self.texture.setup2dTexture(texture_size, texture_size, 
                                   self.texture_component_type, self.texture_format)  
            self.texture.setRamImageAs(self.texture_array, "RGB") 
        else:
            raise ValueError("Texture needs to be 2d or 3d")
       
        self.textureStage = TextureStage("drifting")
                                                                    
        #Create scenegraph
        cm = CardMaker('card1')
        cm.setFrameFullscreenQuad()
        self.card1 = self.aspect2d.attachNewNode(cm.generate())  
        self.card1.setTexture(self.textureStage, self.texture)  #ts, tx
       
        #Transform the model(s)
        self.card1.setScale(np.sqrt(2))
        self.card1.setR(self.angle)
        
        if self.velocity != 0:
            #Add task to taskmgr to translate texture 
            self.taskMgr.add(self.moveTextureTask, "moveTextureTask")
        
    #Move the texture
    def moveTextureTask(self, task):
        new_position = -task.time*self.velocity
        self.card1.setTexPos(self.textureStage, new_position, 0, 0) #u, v, w
        return Task.cont          

class FullFieldStatic(FullFieldDrift):
    """
    Show a single full-field texture.
    Child of FullFieldDrift, with velocity fixed at 0.
    
    FullFieldStatic(texture_array, 
                    angle = 0, 
                    window_size = 512, 
                    texture_size = 512)
    """
    def __init__(self, texture_array, angle = 0, window_size = 512, texture_size = 512):
        self.velocity = 0
        super().__init__(texture_array, angle, self.velocity, window_size, texture_size)
        self.window_properties.setTitle("FullFieldStatic")
        ShowBaseGlobal.base.win.requestProperties(self.window_properties)  #base is a panda3d global
        
class BinocularDrift(ShowBase):
    """
    Show binocular drifting textures forever.
    Takes in texture array and other parameters, and shows texture drifting indefinitely.
    Texture array can be grayscale or rgb, uint8 or uint16.
    
    Usage:
        BinocularDrift(texture_array, 
                        stim_angles = (0, 0), 
                        mask_angle = 0, 
                        position = (0,0),
                        velocities = (0,0),
                        band_radius = 2,
                        window_size = 512, 
                        texture_size = 512)
        
    Note(s): 
        angles are (left_texture_angle, right_texture_angle): >  is cw, < 0 cc2
        Velocity is in NDC, so 1.0 is the entire window width (i.e., super-fast).
        Make texture_size a power of 2: this makes the GPU happier.
        position is x,y in NDC (from [-1 1]), so (.5, .5) will be in middle of top right quadrant
        band_radius is just the half-width of the band in the middle. It can be 0.
        The texture array can be 2d (gray) or NxNx3 (rgb) with unit8 or uint16 elements.
    """
    def __init__(self, texture_array, stim_angles = (0, 0), mask_angle = 0, position = (0,0), 
                 velocities = (0,0), band_radius = 2, window_size = 512, texture_size = 512):
        super().__init__()

        self.mask_position_ndc = position
        self.mask_position_uv = (self.ndc2uv(self.mask_position_ndc[0]), 
                                 self.ndc2uv(self.mask_position_ndc[1]))
        self.scale = np.sqrt(8)  #so it can handle arbitrary rotations and shifts
        self.texture_array = texture_array
        self.texture_dtype = type(self.texture_array.flat[0])
        self.ndims = self.texture_array.ndim
        self.left_texture_angle = stim_angles[0]
        self.right_texture_angle = stim_angles[1]
        self.left_velocity = velocities[0]
        self.right_velocity = velocities[1]
        self.mask_angle = mask_angle #this will change fairly frequently
               
        #Set window title and size
        self.window_properties = WindowProperties()
        self.window_properties.setSize(window_size, window_size)
        self.window_properties.setTitle("BinocularDrift")
        ShowBaseGlobal.base.win.requestProperties(self.window_properties)  #base is a panda3d global
        
        #CREATE MASK ARRAYS
        self.left_mask_array = 255*np.ones((texture_size,texture_size), dtype=np.uint8)    
        self.left_mask_array[:, texture_size//2 - band_radius :] = 0  
        self.right_mask_array = 255*np.ones((texture_size,texture_size), dtype=np.uint8)    
        self.right_mask_array[:, : texture_size//2 + band_radius] = 0  
        
   
        ##SET UP TEXTURE
        self.texture = Texture("stimulus")
        #Select Texture ComponentType (e.g., uint8 or whatever)
        if self.texture_dtype == np.uint8:
            self.texture_component_type = Texture.T_unsigned_byte
        elif self.texture_dtype == np.uint16:
            self.texture_component_type = Texture.T_unsigned_short
            
        #Select Texture Format (color or b/w etc)
        if self.ndims == 2:
            self.texture_format = Texture.F_luminance #grayscale
            self.texture.setup2dTexture(texture_size, texture_size, 
                                   self.texture_component_type, self.texture_format)  
            self.texture.setRamImageAs(self.texture_array, "L") 
        elif self.ndims == 3:
            self.texture_format = Texture.F_rgb8
            self.texture.setup2dTexture(texture_size, texture_size, 
                                   self.texture_component_type, self.texture_format)  
            self.texture.setRamImageAs(self.texture_array, "RGB") 
        else:
            raise ValueError("Texture needs to be 2d or 3d") 

        #TEXTURE STAGES FOR LEFT CARD: TEXTURE AND MASK
        self.left_texture_stage = TextureStage('left_texture_stage')       
        #Mask
        self.left_mask = Texture("left_mask_texture")
        self.left_mask.setup2dTexture(texture_size, texture_size, 
                                               Texture.T_unsigned_byte, Texture.F_luminance) 
        self.left_mask.setRamImage(self.left_mask_array)  
        self.left_mask_stage = TextureStage('left_mask_array')
        #Multiply the texture stages together
        self.left_mask_stage.setCombineRgb(TextureStage.CMModulate, 
                                    TextureStage.CSTexture, 
                                    TextureStage.COSrcColor,
                                    TextureStage.CSPrevious, 
                                    TextureStage.COSrcColor)    
                   
        #TEXTURE STAGES FOR RIGHT CARD
        self.right_texture_stage = TextureStage('right_texture_stage')       
        #Mask
        self.right_mask = Texture("right_mask_texture")
        self.right_mask.setup2dTexture(texture_size, texture_size, 
                                               Texture.T_unsigned_byte, Texture.F_luminance) 
        self.right_mask.setRamImage(self.right_mask_array)  
        self.right_mask_stage = TextureStage('right_mask_stage')
        #Multiply the texture stages together
        self.right_mask_stage.setCombineRgb(TextureStage.CMModulate, 
                                    TextureStage.CSTexture, 
                                    TextureStage.COSrcColor,
                                    TextureStage.CSPrevious, 
                                    TextureStage.COSrcColor)    
                                             
        #CREATE CARDS/SCENEGRAPH
        cm = CardMaker('stimcard')
        cm.setFrameFullscreenQuad()
        self.setBackgroundColor((0,0,0,1))  
        self.left_card = self.aspect2d.attachNewNode(cm.generate())
        self.right_card = self.aspect2d.attachNewNode(cm.generate())
        self.left_card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.right_card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        
        #ADD TEXTURE STAGES TO CARDS
        self.left_card.setTexture(self.left_texture_stage, self.texture)  
        self.left_card.setTexture(self.left_mask_stage, self.left_mask)
        self.right_card.setTexture(self.right_texture_stage, self.texture)  
        self.right_card.setTexture(self.right_mask_stage, self.right_mask)
        
        #TRANSFORMS
        #Left texture mask
        self.mask_transform = self.trs_transform()
        self.left_card.setTexTransform(self.left_mask_stage, self.mask_transform)
        self.right_card.setTexTransform(self.right_mask_stage, self.mask_transform)
        #Left texture
        self.left_card.setTexScale(self.left_texture_stage, 1/self.scale)
        self.left_card.setTexRotate(self.left_texture_stage, self.left_texture_angle)
        #Right texture
        self.right_card.setTexScale(self.right_texture_stage, 1/self.scale)
        self.right_card.setTexRotate(self.right_texture_stage, self.right_texture_angle)

        #Set dynamic transforms (note this will turn into if/elif with four options)
        if self.left_velocity != 0 and self.right_velocity != 0:
            print("Moving both textures")
            self.taskMgr.add(self.textures_update, "move_both")
        elif self.left_velocity != 0 and self.right_velocity == 0:
            print("Moving left texture")
            self.taskMgr.add(self.left_texture_update, "move_left")
        elif self.left_velocity == 0 and self.right_velocity != 0:
            print("Moving right texture")
            self.taskMgr.add(self.right_texture_update, "move_right")


        self.title = OnscreenText("x",
                                  style = 1,
                                  fg = (1,1,1,1),
                                  bg = (0,0,0,.8),
                                  pos = self.mask_position_ndc, 
                                  scale = 0.05)
          
    #Move the texture
    def textures_update(self, task):
        left_tex_position = -task.time*self.left_velocity #negative b/c texture stage
        right_tex_position = -task.time*self.right_velocity
        self.left_card.setTexPos(self.left_texture_stage, left_tex_position, 0, 0) 
        self.right_card.setTexPos(self.right_texture_stage, right_tex_position, 0, 0)
        return task.cont
    
    def left_texture_update(self, task):
        left_tex_position = -task.time*self.left_velocity #negative b/c texture stage
        self.left_card.setTexPos(self.left_texture_stage, left_tex_position, 0, 0) 
        return task.cont
    
    def right_texture_update(self, task):
        right_tex_position = -task.time*self.right_velocity
        self.right_card.setTexPos(self.right_texture_stage, right_tex_position, 0, 0)
        return task.cont

    def trs_transform(self):
        """ trs = translate rotate scale transform for mask stage 
        panda3d developer rdb contributed to this code: it is counterintuitive,
        but it is the only way we could get all the transforms to work!"""        
        pos = 0.5 + self.mask_position_uv[0], 0.5 + self.mask_position_uv[1]
        center_shift = TransformState.make_pos2d((-pos[0], -pos[1]))
        scale = TransformState.make_scale2d(1/self.scale)
        rotate = TransformState.make_rotate2d(self.mask_angle)
        translate = TransformState.make_pos2d((0.5, 0.5))
        return translate.compose(rotate.compose(scale.compose(center_shift)))
    
    def ndc2uv(self, val):
        """ from model-based normalized device coordinates to texture-based uv-coordinates"""
        return 0.5*val
    
    def uv2ndc(self, val):
        """ from texture-based uv-coordinates to model-based normalized device coordinates"""
        return 2*val
  

class BinocularStatic(BinocularDrift):
    """
    Show static  binocular drifting textures forever.
    Child of BinocularDrift, with velocities automatically set to (0,0)
    
        BinocularDrift(texture_array, 
                        stim_angles = (0, 0), 
                        mask_angle = 0,
                        position = (0,0),
                        band_radius = 3,
                        window_size = 512, 
                        texture_size = 512)
    """

    def __init__(self, texture_array, stim_angles = (0, 0), mask_angle = 0,  
                 position = (0, 0), band_radius = 3, window_size = 512, texture_size = 512):
        self.velocities = (0, 0)
        super().__init__(texture_array, stim_angles, mask_angle, position, self.velocities, 
                         band_radius, window_size, texture_size)
        self.window_properties.setTitle("BinocularStatic")
        ShowBaseGlobal.base.win.requestProperties(self.window_properties)  #base is a panda3d global
     

class FullFieldDriftExperiment(ShowBase):
    """
    Doc here
    To do: make texture_size and window_size inputs.
    """
    def __init__(self, texture_function, stim_params, experiment_structure,
                 window_size = 512, texture_size = 512):
        super().__init__()
        self.events = experiment_structure['event_values']
        self.event_change_times = experiment_structure['event_change_times']
        self.event_durations = experiment_structure['event_durations']
        self.current_event_num = 0
        self.num_events = len(self.events)
        self.stim_params = stim_params
        self.texture_size = texture_size
        self.window_size = window_size
        self.bgcolor = (0.5, 0.5, 0.5, 1)
        
        #Window properties
        self.windowProps = WindowProperties()
        self.windowProps.setSize(self.window_size, self.window_size)
        self.set_title("FFDE Initializing")
        
        #Create scenegraph
        cm = CardMaker('card1')
        cm.setFrameFullscreenQuad()
        self.card1 = self.aspect2d.attachNewNode(cm.generate())  
        self.card1.setScale(np.sqrt(8))
        self.card1.setColor(self.bgcolor)  #make this an add mode

        self.taskMgr.add(self.move_texture_task, "move_texture")
        self.taskMgr.add(self.set_texture_task, "set_texture")
        
    @property
    def current_event_ind(self):
        """ returns index of current event (e.g., -1 for baseline, 1 for sine xyz)
        typical events = [-1 2 0 1 -1 1 0 2] so events[5] = 1"""
        return self.events[self.current_event_num]
    
    @property
    def current_stim_params(self):
        """ returns actual value of current event """
        return self.stim_params[self.current_event_ind]
    
       
    def set_texture_task(self, task):
        """ doc here"""
        if task.time <= event_change_times[-1]:
            if task.time >= self.event_change_times[self.current_event_num]:
                self.current_event_num += 1
                if self.current_event_ind  == -1:
                    self.card1.setColor(self.bgcolor)  
                    self.card1.clearTexture(self.texture_stage)  #turn off stage
                    self.set_title("FFDE {0}: {1}".format(self.current_event_num, "baseline"))
                    
                else:
                    texture_params = self.current_stim_params['kwargs']
                    texture_array = texture_function(**texture_params)
                    texture_dtype = type(texture_array.flat[0])
                    texture_ndims = texture_array.ndim

                    #Create texture stage
                    self.texture = Texture("stim_texture")
                    
                    #ComponentType depends on dtype (uint8 or whatever)
                    if texture_dtype == np.uint8:
                        texture_component_type = Texture.T_unsigned_byte
                    elif texture_dtype == np.uint16:
                        texture_component_type = Texture.T_unsigned_short
                    else:
                        raise ValueError("Texture needs to be uint8 or uint16. Let me know if you have others.")

                    #Texture format depends on ndims
                    if texture_ndims == 2:
                        texture_format = Texture.F_luminance #grayscale
                        provided_format = "L"
                    elif texture_ndims == 3:
                        texture_format = Texture.F_rgb8
                        provided_format = "RGB"
                    else:
                        raise ValueError("Texture needs to be 2d or 3d (rgb). Let us know if you have others.")
            

                    self.texture.setup2dTexture(texture_size, texture_size, 
                                           texture_component_type, texture_format)  
                    self.texture.setRamImageAs(texture_array, provided_format)  
                    self.texture_stage = TextureStage('stim_texture_stage')
                                       
                    self.card1.setColor((1, 1, 1, 1))  
                    self.card1.setTexture(self.texture_stage, self.texture) 
                    self.card1.setR(self.current_stim_params['angle']) 
                    self.set_title("FFDE {0}: {1}".format(self.current_event_num,  self.current_event_ind))

            return task.cont 
        else:
            return task.done  

    def move_texture_task(self, task):
        """doc here"""         
        if task.time <= event_change_times[-1]:
            if self.current_event_ind != -1:
                new_position = -task.time*self.current_stim_params['velocity']
                self.card1.setTexPos(self.texture_stage, new_position, 0, 0) #u, v, w
            return task.cont #taskMgr will continue to call task
        else:
            print("Last stimulus has been shown")
            self.set_title("FFDE Done")
            #Put text into arena
            return task.done  #taskMgr will not call task
        
    def set_title(self, title):
        self.windowProps.setTitle(title)
        ShowBaseGlobal.base.win.requestProperties(self.windowProps)  #base is a panda3d global
        
    def plot_timeline(self):
        """ plots step plot of stimulus versus time"""
        full_time = np.arange(0, self.event_change_times[-1], 0.5)
        full_stimulus = -1*np.ones(len(full_time))
        event_num = 0
        for time_ind in range(len(full_time)):
            time_val = full_time[time_ind]
            if time_val >= event_change_times[event_num]:
                event_num += 1             
            full_stimulus[time_ind] =  all_events[event_num]
        plt.step(full_time, full_stimulus)
        plt.yticks(np.arange(-1, np.max(full_stimulus)+1, 1))
        plt.xlabel('Time (s)')
        plt.ylabel('Stimulus')
        plt.title('Stimuli over full experiment (-1 is baseline)')
        plt.show()   
        
#%%
if __name__ == '__main__':
    
    usage_note = "\nCommand line arguments:\n1: To test FullFieldStatic() [default]\n2: FullfieldDrift()\n"
    usage_note += "3: BinocularStatic()\n4: BinocularDrift()\n5: Experiment"
    
    if len(sys.argv) == 1:
        print(sys.argv[0], ": ", usage_note)
        test_case = '1'
        
    else:
        test_case = sys.argv[1]
        
    if test_case == '1':
        #Test FullFieldStatic()
        stim_params = {'spatial_freq': 15, 'angle': -45}
        texture_size = 512
        window_size = 512
        texture = textures.grating_texture(texture_size, stim_params['spatial_freq'])
        pandastim_static = FullFieldStatic(texture, angle = stim_params["angle"], 
                                            window_size = window_size, texture_size = texture_size)
        pandastim_static.run()
        
    elif test_case == '2':
        #Test FullFieldDrift()
        stim_params = {'velocity': 0.125, 'spatial_freq': 10, 'angle': 40}
        texture_size = 512
        window_size = 512
        tex_array = textures.sin_texture(texture_size, stim_params['spatial_freq'])
        pandastim_drifter = FullFieldDrift(tex_array, angle = stim_params["angle"], 
                                           velocity = stim_params["velocity"], window_size = window_size, 
                                           texture_size = texture_size)
        pandastim_drifter.run()
        
    elif test_case == '3':
                   
        stim_params = {'spatial_freq': 20, 'stim_angles': (30, 90), 
                       'position': (0, 0), 'band_radius': 1}
        mask_angle = 45  #this will change frequently in practice so not in dict
        texture_size = 512
        window_size = 512  
        texture = textures.grating_texture(texture_size, stim_params['spatial_freq'])
        binocular_static = BinocularStatic(texture, 
                                           stim_angles = stim_params["stim_angles"],
                                           mask_angle = mask_angle,
                                           position = stim_params["position"], 
                                           band_radius = stim_params['band_radius'],
                                           window_size = window_size,
                                           texture_size = texture_size)
        binocular_static.run()
        
    elif test_case == '4':
        stim_params = {'spatial_freq': 25, 'stim_angles': (-45, 90), 'velocities': (.03, .01), 
                       'position': (0.1, -.4), 'band_radius': 2}
        mask_angle = 25
        texture_size = 512
        window_size = 512  
        texture = textures.sin_texture(texture_size, stim_params['spatial_freq'])
    
        binocular_drifting = BinocularDrift(texture, 
                                           stim_angles = stim_params["stim_angles"],
                                           mask_angle = mask_angle,
                                           position = stim_params["position"], 
                                           velocities = stim_params["velocities"],
                                           band_radius = stim_params['band_radius'],
                                           window_size = window_size,
                                           texture_size = texture_size)
        binocular_drifting.run()
    elif test_case == '5':
        from itertools import zip_longest
        from os import makedirs
        data_dir = Path(r'C:\Users\Eric\AppData\pandastim')
        try:
            makedirs(data_dir)
        except FileExistsError:
            print("Storing data in", data_dir, ", which already exists.")
        save_basename = r'ffd_experiment_data';
        window_size = 512
        texture_size = window_size 
        texture_function =  textures.sin_texture; 
        stim_params = [{'angle': -20, 'velocity': 0.10, 'kwargs': {'spatial_frequency': 15, 'texture_size': texture_size}},
                       {'angle':  20, 'velocity': -0.08, 'kwargs': {'spatial_frequency': 10, 'texture_size': texture_size}},
                       {'angle':  90, 'velocity': 0.05,  'kwargs': {'spatial_frequency': 5, 'texture_size': texture_size}}]
        #Arrays of stimulus values and durations
        stimulus_values = [2, 1, 0, 1, ]
        stim_durations =  [4, 4, 2, 3,]
        delay_durations = [4, 2, 3, 2,]  #time after each stimulus to show baseline
        initial_baseline_duration = [2] #time before first stimulus to show baseline
        baseline_durations = initial_baseline_duration + delay_durations
        num_stim = len(stim_durations)    
        num_baselines = len(baseline_durations)
        #Create list of all events, including baseline as -1
        all_events = [y for x in zip_longest(-1*np.ones(num_baselines), stimulus_values) for y in x if y is not None]
        #Derive event structure
        event_durations =  [y for x in zip_longest(baseline_durations, stim_durations) for y in x if y is not None]
        event_change_times = np.cumsum(event_durations)   #-1 because final baseline never ends
        num_event_changes = len(event_change_times)
        num_events = num_event_changes
        experiment_structure = {'event_values': all_events,  
                                'event_durations': event_durations, 
                                'event_change_times': event_change_times}   #redundant, contained in event_durs              
        exp_app = FullFieldDriftExperiment(texture_function, stim_params, experiment_structure,
                                       window_size = window_size, texture_size = texture_size,
                                       save_path = None)
        #app.plot_timeline()
        exp_app.run()
        
    else:
        print(usage_note)

