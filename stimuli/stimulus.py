"""
pandastim/stimuli.py

Classes to present visual stimuli in pandastim (subclasses of ShowBase, which
implements the main event loop in panda3d).

stimuli consist of textures and parameters relating to stimulus motion

Example Classes given as TexMoving and BinocularMoving -- use a sequencer for experiments

Part of pandastim package: https://github.com/mattdloring/pandastim
"""
import json
import sys
import os
from pathlib import Path

import numpy as np
from direct.gui.OnscreenText import OnscreenText  # for binocular stim
from direct.showbase import ShowBaseGlobal
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (CardMaker, ClockObject, ColorBlendAttrib,
                          PStatClient, Texture, TextureStage, TransformState,
                          WindowProperties)

from pandastim import utils
from pandastim.stimuli import stimulus_details


class StimulusSequencing(ShowBase):
    """
    this is the base class for chaining multiple stimuli together

    doesnt actually do anything on its own

    subclass this out for specific use cases

    """

    def __init__(self, stimuli=None, params_path="default", buddy=None):
        super().__init__()

        self.stimuli = stimuli

        # if we have a stimbuddy start a task running
        self.buddy = buddy
        if self.buddy:
            self.taskMgr.add(self.buddy_task, "buddy")

        self.load_params(params_path)
        self.format_window()
        self.enable_params()

        self.current_stimulus = None
        self.running = True

    def set_stimulus(self):
        # match stimulus to stimulus details type
        match self.current_stimulus:
            case stimulus_details.MonocularStimulusDetails():
                self.set_monocular()
            case stimulus_details.BinocularStimulusDetails():
                self.set_binocular()
            case None:
                pass
            case _:
                print(
                    f"{self.current_stimulus.__class__} -- Stimulus type not understood"
                )

    def set_monocular(self):
        cardmaker = CardMaker("stimcard")
        cardmaker.setFrameFullscreenQuad()

        # create tex stage
        self.texture_stage = TextureStage("texture_stage")

        # create card
        self.card = self.aspect2d.attachNewNode(cardmaker.generate())
        self.card.setScale(self.scale)
        self.card.setColor((1, 1, 1, 1))

        self.card.setTexture(self.texture_stage, self.current_stimulus.texture.texture)

        # set tex transforms
        self.card.setTexRotate(
            self.texture_stage,
            self.current_stimulus.angle + self.default_params["rotation_offset"],
        )
        self.card.setTexPos(self.texture_stage, self.center_x, self.center_y, 0)
        self.taskMgr.add(self.move_monocular, "move_monocular")

    def move_monocular(self, move_monocular_task):
        if move_monocular_task.time <= self.current_stimulus.stationary_time:
            # self.new_position = 0
            pass
        elif move_monocular_task.time >= self.current_stimulus.duration != -1:
            self.clear_cards()
            self.new_position = 0
            return move_monocular_task.done
        else:
            self.new_position = (
                (-move_monocular_task.time) * self.current_stimulus.velocity
            )
            self.card.setTexPos(
                self.texture_stage, self.new_position + self.center_x, self.center_y, 0
            )  # u, v, w
        return move_monocular_task.cont

    def set_binocular(self):

        self.center_x = self.current_stimulus.position[0]
        self.center_y = self.current_stimulus.position[1]

        tex_1_size = self.current_stimulus.texture[0].texture_size
        tex_2_size = self.current_stimulus.texture[1].texture_size
        tex_1 = self.current_stimulus.texture[0].texture
        tex_2 = self.current_stimulus.texture[1].texture

        ## CREATE TEXTURE STAGES ##
        self.left_texture_stage = TextureStage("left_texture_stage")
        self.left_mask = Texture("left_mask_texture")
        self.left_mask.setup2dTexture(
            tex_1_size[0], tex_1_size[1], Texture.T_unsigned_byte, Texture.F_luminance
        )
        self.left_mask_stage = TextureStage("left_mask_array")

        self.right_texture_stage = TextureStage("right_texture_stage")
        self.right_mask = Texture("right_mask_texture")
        self.right_mask.setup2dTexture(
            tex_2_size[0], tex_2_size[1], Texture.T_unsigned_byte, Texture.F_luminance
        )
        self.right_mask_stage = TextureStage("right_mask_stage")

        ## CREATE CARDS ###
        cardmaker = CardMaker("stimcard")
        cardmaker.setFrameFullscreenQuad()

        self.setBackgroundColor((0, 0, 0, 1))
        self.left_card = self.aspect2d.attachNewNode(cardmaker.generate())
        self.left_card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.right_card = self.aspect2d.attachNewNode(cardmaker.generate())
        self.right_card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))

        # CREATE MASK ARRAYS
        self.left_mask_array = 255 * np.ones(
            (tex_1_size[0], tex_1_size[1]), dtype=np.uint8
        )
        self.left_mask_array[
            :, (tex_1_size[1] // 2) - self.current_stimulus.strip_width // 2 :
        ] = 0

        self.right_mask_array = 255 * np.ones(
            (tex_2_size[0], tex_2_size[1]), dtype=np.uint8
        )
        self.right_mask_array[
            :, : (tex_2_size[1] // 2) + self.current_stimulus.strip_width // 2
        ] = 0

        if self.default_params["projecting_fish"]:
            ### DANGER ZONE ###
            ### currently assumes 1024 textures ###
            self.left_mask_array[506:515, 511:512] = 120
            self.right_mask_array[506:515, 512:513] = 120
            self.left_mask_array[514:516, 510:512] = 255
            self.right_mask_array[514:516, 512:514] = 255
            ### END DANGER ZONE ###

        # ADD TEXTURE STAGES TO CARDS
        self.left_mask.setRamImage(self.left_mask_array)
        self.left_card.setTexture(self.left_texture_stage, tex_1)

        # Multiply the texture stages together
        self.left_mask_stage.setCombineRgb(
            TextureStage.CMModulate,
            TextureStage.CSTexture,
            TextureStage.COSrcColor,
            TextureStage.CSPrevious,
            TextureStage.COSrcColor,
        )

        self.left_card.setTexture(self.left_mask_stage, self.left_mask)


        # ADD TEXTURE STAGES TO CARDS
        self.right_mask.setRamImage(self.right_mask_array)
        self.right_card.setTexture(self.right_texture_stage, tex_2)

        # Multiply the texture stages together
        self.right_mask_stage.setCombineRgb(
            TextureStage.CMModulate,
            TextureStage.CSTexture,
            TextureStage.COSrcColor,
            TextureStage.CSPrevious,
            TextureStage.COSrcColor,
        )

        self.right_card.setTexture(self.right_mask_stage, self.right_mask)


        ### Do the transform things ###
        self.mask_transform = self.trs_transform()

        self.left_angle = (
            self.current_stimulus.strip_angle
            + self.current_stimulus.angle[0]
            + self.rotation_offset
        )
        self.right_angle = (
            self.current_stimulus.strip_angle
            + self.current_stimulus.angle[1]
            + self.rotation_offset
        )

        self.left_card.setTexTransform(self.left_mask_stage, self.mask_transform)
        self.right_card.setTexTransform(self.right_mask_stage, self.mask_transform)

        # Left texture
        self.left_card.setTexScale(self.left_texture_stage, 1 / self.scale)
        self.left_card.setTexRotate(self.left_texture_stage, self.left_angle)

        # Right texture
        self.right_card.setTexScale(self.right_texture_stage, 1 / self.scale)
        self.right_card.setTexRotate(self.right_texture_stage, self.right_angle)

        # start the movement once everything is set up
        self.taskMgr.add(self.move_binocular, "move_binocular")

    def move_binocular(self, move_binocular_task):
        ### LEFT SIDE ###
        if move_binocular_task.time <= self.current_stimulus.stationary_time[0]:
            new_position_left = 0
        elif move_binocular_task.time >= self.current_stimulus.duration[0] != -1:
            if self.default_params["hold_onfinish"]:
                new_position_left = self.new_position[0]
            else:
                self.left_card.detach_node()
                new_position_left = None
        else:
            new_position_left = (
                -move_binocular_task.time * self.current_stimulus.velocity[0] * 2
            )
            self.left_card.setTexPos(
                self.left_texture_stage,
                new_position_left + self.center_x,
                self.center_y,
                0,
            )  # u, v, w

        ### RIGHT SIDE ###
        if move_binocular_task.time <= self.current_stimulus.stationary_time[1]:
            new_position_right = 0
        elif move_binocular_task.time >= self.current_stimulus.duration[1] != -1:
            if self.default_params["hold_onfinish"]:
                new_position_right = self.new_position[1]
            else:
                self.right_card.detach_node()
                new_position_right = None
        else:
            new_position_right = (
                -move_binocular_task.time * self.current_stimulus.velocity[1] * 2
            )
            self.right_card.setTexPos(
                self.right_texture_stage,
                new_position_right + self.center_x,
                self.center_y,
                0,
            )  # u, v, w

        self.new_position = new_position_left, new_position_right

        if move_binocular_task.time >= max(
            self.current_stimulus.duration[0], self.current_stimulus.duration[1]
        ):
            self.clear_cards()
            return move_binocular_task.done

        return move_binocular_task.cont

    def clear_cards(self):
        try:
            self.card.detach_node()
        except:
            pass
        try:
            self.left_card.detach_node()
        except:
            pass
        try:
            self.right_card.detach_node()
        except:
            pass

        self.taskMgr.remove("move_monocular")
        self.taskMgr.remove("move_binocular")
        self.current_stimulus = None

    def trs_transform(self):
        """
        trs = translate-rotate-scale transform for mask stage
        panda3d developer rdb contributed to this code
        """

        ## highly recommend not monkeying with this too much
        # print([self.center_x, self.center_y], [self.bin_center_x, self.bin_center_y])
        self.bin_center_x = 1 * self.center_y * self.scale
        self.bin_center_y = -1 * self.center_x * self.scale

        self.mask_position_uv = (self.bin_center_x, self.bin_center_y)

        pos = 0.5 + self.mask_position_uv[0], 0.5 + self.mask_position_uv[1]
        center_shift = TransformState.make_pos2d((-pos[0], -pos[1]))
        scale = TransformState.make_scale2d(1 / self.scale)
        rotate = TransformState.make_rotate2d(self.current_stimulus.strip_angle)
        translate = TransformState.make_pos2d((0.5, 0.5))

        return translate.compose(rotate.compose(scale.compose(center_shift)))

    def set_transforms(self):
        match self.current_stimulus:
            case stimulus_details.MonocularStimulusDetails():
                self.card.setTexRotate(
                    self.texture_stage,
                    self.current_stimulus.angle + self.angle_rotation,
                )
                self.card.setTexPos(self.texture_stage, self.center_x, self.center_y, 0)

            case stimulus_details.BinocularStimulusDetails():
                self.mask_transform = self.trs_transform()
                self.left_angle = (
                    self.current_stimulus.angle[0]
                    + self.rotation_offset
                    + self.angle_rotation
                )
                self.right_angle = (
                    self.current_stimulus.angle[1]
                    + self.rotation_offset
                    + self.angle_rotation
                )

                # Left texture
                self.left_card.setTexTransform(
                    self.left_mask_stage, self.mask_transform
                )
                self.left_card.setTexScale(self.left_texture_stage, 1 / self.scale)
                self.left_card.setTexRotate(self.left_texture_stage, self.left_angle)

                # Right texture
                self.right_card.setTexTransform(
                    self.right_mask_stage, self.mask_transform
                )
                self.right_card.setTexScale(self.right_texture_stage, 1 / self.scale)
                self.right_card.setTexRotate(self.right_texture_stage, self.right_angle)

            case _:
                print(
                    f"{self.current_stimulus.__class__} -- Stimulus type not understood, transform failed"
                )

    def buddy_task(self, buddytask):
        self.buddy.position(self.new_position)
        self.buddy.stimulus(self.current_stimulus)
        self.buddy.broadcaster()
        return buddytask.cont

    def load_params(self, params_path):
        if params_path == "default":
            default_params_path = (
                Path(sys.executable)
                .parents[0]
                .joinpath(r"Lib\site-packages\pandastim\resources\params\default_params.json")
            )
            if os.path.exists(default_params_path):
                with open(default_params_path) as json_file:
                    self.default_params = json.load(json_file)
            else:
                self.default_params = None
                logging.error('no default parameters found')
        else:
            if os.path.exists(params_path):
                with open(params_path) as json_file:
                    self.default_params = json.load(json_file)
            else:
                self.default_params = None
                logging.error('no default parameters found')

        if not self.default_params:
            self.logging.info('initializing non-loaded params')
            self.default_params = {
                "rotation_offset": -90, "window_size": [1024, 1024], "window_position": [400, 400], "fps": 60,
                "window_undecorated": False, "center": [0, 0], "window_foreground": True, "window_title": "Pandastim",
                "profile_on": False, "projecting_fish": False, "hold_onfinish": True, "publish_port": 5010}

    def enable_params(self):
        self.scale = np.sqrt(self.default_params["scale"])
        self.center_x = self.default_params["center"][0]
        self.center_y = self.default_params["center"][1]
        self.rotation_offset = self.default_params[
            "rotation_offset"
        ]  # rig / implementation specific offset
        self.angle_rotation = 0  # for changing angles on the fly
        self.new_position = 0  # for tracking position on the fly

    def format_window(self):
        ShowBaseGlobal.globalClock.setMode(ClockObject.MLimited)
        ShowBaseGlobal.globalClock.setFrameRate(self.default_params["fps"])

        self.window_props = WindowProperties()

        self.window_props.setTitle(self.default_params["window_title"])
        self.window_props.setSize(tuple(self.default_params["window_size"]))

        self.window_props.set_undecorated(self.default_params["window_undecorated"])
        self.disable_mouse()
        self.window_props.set_foreground(self.default_params["window_foreground"])
        self.window_props.set_origin(tuple(self.default_params["window_position"]))

        self.setBackgroundColor(0, 0, 0) # this makes the background true black

        ShowBaseGlobal.base.win.requestProperties(self.window_props)

        if self.default_params["profile_on"]:
            PStatClient.connect()
            ShowBaseGlobal.base.setFrameRateMeter(True)

class OpenLoopStimulus(StimulusSequencing):
    def __init__(self, stimuli, *args, **kwargs):
        """
        An open-loop implementation that expects to be fed a sequence of stimuli
        :param stimuli: generally a list of stimuli in expected order
        :param args/kwargs: generally different default parameters & a save path
        """

        super().__init__(stimuli, *args, **kwargs)
        self.curr_id = 0
        self.current_stimulus = self.stimuli[self.curr_id]
        self.set_stimulus()

    def clear_cards(self):
        super().clear_cards()

        self.curr_id += 1
        try:
            self.current_stimulus = self.stimuli[self.curr_id]
        except IndexError:
            self.running = False
            if self.buddy:
                self._running = self.running
            sys.exit()

        self.set_stimulus()


### TEX MOVING AND BINOCULAR MOVING FOR EXAMPLES ON HOW TO MOVE ###
class TexMoving(ShowBase):
    """
    Shows single wholefield texture drifting across the window at specified velocity and angle.
    Mostly useful for testing purposes
    Usage:
        tex = SinGreyTex()
        stim_details = MonocularStimulusDetails(stim_name=str(tex), angle=0, velocity=0.1)
        stim_show = TexMoving()
        stim_show.run()
    Note(s):
        Positive angles are clockwise, negative ccw.
        Velocity is normalized to window size, so 1.0 is the entire window width (i.e., super-fast).
    """

    def __init__(
        self,
        stimulus_details,
        window_name="TexMoving",
        window_size=None,
        profile=False,
        fps=60,
    ):
        super().__init__()

        self.stimulus_details = stimulus_details
        assert isinstance(
            self.stimulus_details, stimtypes.MonocularStimulusDetails
        ), "class must be monocular stimulus details"

        if window_size is None:
            window_size = self.stimulus_details.texture_size
        if not hasattr(window_size, "__iter__"):
            window_size = tuple([window_size, window_size])
        self.window_size = window_size

        # Set frame rate (fps)
        ShowBaseGlobal.globalClock.setMode(ClockObject.MLimited)
        ShowBaseGlobal.globalClock.setFrameRate(fps)

        # Set up profiling if desired
        if profile:
            PStatClient.connect()  # this will only work if pstats is running: see readme
            ShowBaseGlobal.base.setFrameRateMeter(True)  # Show frame rate

        # Window properties set up
        self.window_properties = WindowProperties()
        self.window_properties.set_size(self.window_size)

        self.window_properties.setTitle(window_name)
        ShowBaseGlobal.base.win.requestProperties(self.window_properties)

        # Create scenegraph, attach stimulus to card.
        cm = CardMaker("card")
        cm.setFrameFullscreenQuad()
        self.card = self.aspect2d.attachNewNode(cm.generate())

        # Scale is so it can handle arbitrary rotations and shifts in binocular case
        self.card.setScale(np.sqrt(8))
        self.card.setColor(
            (1, 1, 1, 1)
        )  # makes it bright when bright (default combination with card is add)

        self.texture_stage = TextureStage("texture_stage")
        self.card.setTexture(self.texture_stage, self.stimulus_details.texture.texture)
        self.card.setTexRotate(self.texture_stage, self.stimulus_details.angle)

        if self.stimulus_details.velocity != 0:
            self.taskMgr.add(self.moveTextureTask, "moveTextureTask")

    def moveTextureTask(self, task):
        new_position = -task.time * self.stimulus_details.velocity
        self.card.setTexPos(self.texture_stage, new_position, 0, 0)  # u, v, w
        return Task.cont


class BinocularMoving(ShowBase):
    """
    Show binocular drifting textures.
    Takes in texture object and other parameters, and shows texture drifting indefinitely.
    Mostly useful for debugging
    Usage:
        BinocularDrift(texture_object,
                        stim_angles = (0, 0),
                        strip_angle = 0,
                        position = (0,0),
                        velocities = (0,0),
                        strip_width = 2,
                        window_size = 512,
                        window_name = 'FunStim',
                        profile_on  = False)
    Note(s):
        - angles are (left_texture_angle, right_texture_angle): >0 is cw, <0 ccw
        - Make texture_size a power of 2: this makes the GPU happier.
        - position is x,y in card-based coordinates (from [-1 1]), so (.5, .5) will be in middle of top right quadrant
        - Velocity is in card-based units, so 1.0 is the entire window width (i.e., super-fast).
        - strip_width is just the width of the strip down the middle. It can be 0. Even is better.
        - The texture array can be 2d (gray) or NxNx3 (rgb) with unit8 or uint16 elements.
    """

    def __init__(
        self,
        stimulus_details,
        window_name="BinocularMoving",
        window_size=None,
        profile=False,
        fps=60,
    ):
        super().__init__()

        self.stimulus_details = stimulus_details
        assert isinstance(
            self.stimulus_details, stimtypes.BinocularStimulusDetails
        ), "class must be binocular stimulus details"

        if window_size is None:
            window_size = self.stimulus_details.texture_size
        if not hasattr(window_size, "__iter__"):
            window_size = tuple([window_size, window_size])
        self.window_size = window_size

        self.mask_position_card = self.stimulus_details.position

        self.mask_position_uv = (
            utils.card2uv(self.mask_position_card[0]),
            utils.card2uv(self.mask_position_card[1]),
        )

        # Set frame rate (fps)
        ShowBaseGlobal.globalClock.setMode(ClockObject.MLimited)
        ShowBaseGlobal.globalClock.setFrameRate(fps)

        # Set up profiling if desired
        if profile:
            PStatClient.connect()  # this will only work if pstats is running
            ShowBaseGlobal.base.setFrameRateMeter(True)  # Show frame rate
            # Following will show a small x at the center
            self.title = OnscreenText(
                "x",
                style=1,
                fg=(1, 1, 1, 1),
                bg=(0, 0, 0, 0.8),
                pos=self.mask_position_card,
                scale=0.05,
            )

        # Window properties set up
        self.window_properties = WindowProperties()
        self.window_properties.set_size(self.window_size)

        self.window_properties.setTitle(window_name)
        ShowBaseGlobal.base.win.requestProperties(self.window_properties)

        # CREATE MASK ARRAYS
        self.left_mask_array = 255 * np.ones(
            self.stimulus_details.texture_size, dtype=np.uint8
        )
        self.left_mask_array[
            :,
            self.stimulus_details.texture_size[1] // 2
            - self.stimulus_details.strip_width // 2 :,
        ] = 0
        self.right_mask_array = 255 * np.ones(
            self.stimulus_details.texture_size, dtype=np.uint8
        )
        self.right_mask_array[
            :,
            : self.stimulus_details.texture_size[1] // 2
            + self.stimulus_details.strip_width // 2,
        ] = 0

        # TEXTURE STAGES FOR LEFT CARD
        self.left_texture_stage = TextureStage("left_texture_stage")
        # Mask
        self.left_mask = Texture("left_mask_texture")
        self.left_mask.setup2dTexture(
            self.stimulus_details.texture_size[0],
            self.stimulus_details.texture_size[1],
            Texture.T_unsigned_byte,
            Texture.F_luminance,
        )
        self.left_mask.setRamImage(self.left_mask_array)
        self.left_mask_stage = TextureStage("left_mask_array")
        # Multiply the texture stages together
        self.left_mask_stage.setCombineRgb(
            TextureStage.CMModulate,
            TextureStage.CSTexture,
            TextureStage.COSrcColor,
            TextureStage.CSPrevious,
            TextureStage.COSrcColor,
        )
        # TEXTURE STAGES FOR RIGHT CARD
        self.right_texture_stage = TextureStage("right_texture_stage")
        # Mask
        self.right_mask = Texture("right_mask_texture")
        self.right_mask.setup2dTexture(
            self.stimulus_details.texture_size[0],
            self.stimulus_details.texture_size[1],
            Texture.T_unsigned_byte,
            Texture.F_luminance,
        )
        self.right_mask.setRamImage(self.right_mask_array)
        self.right_mask_stage = TextureStage("right_mask_stage")
        # Multiply the texture stages together
        self.right_mask_stage.setCombineRgb(
            TextureStage.CMModulate,
            TextureStage.CSTexture,
            TextureStage.COSrcColor,
            TextureStage.CSPrevious,
            TextureStage.COSrcColor,
        )
        # CREATE CARDS/SCENEGRAPH
        cm = CardMaker("stimcard")
        cm.setFrameFullscreenQuad()
        # self.setBackgroundColor((0,0,0,1))
        self.left_card = self.aspect2d.attachNewNode(cm.generate())
        self.right_card = self.aspect2d.attachNewNode(cm.generate())
        self.left_card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
        self.right_card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))

        # ADD TEXTURE STAGES TO CARDS
        self.left_card.setTexture(
            self.left_texture_stage, self.stimulus_details.texture[0].texture
        )
        self.left_card.setTexture(self.left_mask_stage, self.left_mask)
        self.right_card.setTexture(
            self.right_texture_stage, self.stimulus_details.texture[1].texture
        )
        self.right_card.setTexture(self.right_mask_stage, self.right_mask)
        self.setBackgroundColor(
            (0, 0, 0, 1)
        )  # without this the cards will appear washed out

        # TRANSFORMS
        self.scale = np.sqrt(8)

        # Masks
        self.mask_transform = self.trs_transform()
        self.left_card.setTexTransform(self.left_mask_stage, self.mask_transform)
        self.right_card.setTexTransform(self.right_mask_stage, self.mask_transform)
        # Left texture
        self.left_card.setTexScale(self.left_texture_stage, 1 / self.scale)
        self.left_card.setTexRotate(
            self.left_texture_stage, self.stimulus_details.angle[0]
        )
        # Right texture
        self.right_card.setTexScale(self.right_texture_stage, 1 / self.scale)
        self.right_card.setTexRotate(
            self.right_texture_stage, self.stimulus_details.angle[1]
        )

        # Set dynamic transforms
        self.taskMgr.add(self.textures_update, "move_both")

    # Move both textures
    def textures_update(self, task):
        if self.stimulus_details.velocity[0] == 0:
            pass
        elif self.stimulus_details.stationary_time[0] == 0:
            left_tex_position = (
                -task.time * self.stimulus_details.velocity[0]
            )  # negative b/c texture stage
            self.left_card.setTexPos(self.left_texture_stage, left_tex_position, 0, 0)
        else:
            if task.time >= self.stimulus_details.stationary_time[0]:
                left_tex_position = (
                    -task.time * self.stimulus_details.velocity[0]
                )  # negative b/c texture stage
                self.left_card.setTexPos(
                    self.left_texture_stage, left_tex_position, 0, 0
                )

        if self.stimulus_details.velocity[1] == 0:
            pass
        elif self.stimulus_details.stationary_time[1] == 0:
            right_tex_position = (
                -task.time * self.stimulus_details.velocity[1]
            )  # negative b/c texture stage
            self.right_card.setTexPos(
                self.right_texture_stage, right_tex_position, 0, 0
            )
        else:
            if task.time >= self.stimulus_details.stationary_time[1]:
                right_tex_position = (
                    -task.time * self.stimulus_details.velocity[1]
                )  # negative b/c texture stage
                self.right_card.setTexPos(
                    self.right_texture_stage, right_tex_position, 0, 0
                )
        return task.cont

    def trs_transform(self):
        """
        trs = translate rotate scale transform for mask stage
        rdb contributed to this code
        """
        pos = 0.5 + self.mask_position_uv[0], 0.5 + self.mask_position_uv[1]
        center_shift = TransformState.make_pos2d((-pos[0], -pos[1]))
        scale = TransformState.make_scale2d(1 / self.scale)
        rotate = TransformState.make_rotate2d(self.stimulus_details.strip_angle)
        translate = TransformState.make_pos2d((0.5, 0.5))
        return translate.compose(rotate.compose(scale.compose(center_shift)))

### ENDS EXAMPLE CLASSES ###
