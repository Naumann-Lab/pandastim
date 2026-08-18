import json
import os
import sys
from pathlib import Path

import numpy as np
import math
from datetime import datetime as dt
import pandas as pd
import logging
import time
from direct.gui.OnscreenText import OnscreenText  # for binocular stim
from direct.showbase import ShowBaseGlobal
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (CardMaker, ClockObject, ColorBlendAttrib, TransparencyAttrib,
                          PStatClient, Texture, TextureStage, TransformState,
                          WindowProperties)

from pandastim import utils
from pandastim.stimuli import stimulus_details, textures



class StimulusSequencing(ShowBase):
    """
    this is the base class for chaining multiple stimuli together

    doesnt actually do anything on its own

    subclass this out for specific use cases

    """

    def __init__(self, params_path="default", buddy=None):
        super().__init__()


        #T^T: basically what i need is to put a socket right here to talk w improv!
        # add: print("Listening for Improv Connection") maybe not tho, maybe buddy does everything
        
        # if we have a stimbuddy start a task running
        self.buddy = buddy
        if self.buddy:
            self.taskMgr.add(self.buddy_task, "buddy")


        print("MONOCULAR STIMULUS DETAILS:", stimulus_details.MonocularStimulusDetails())

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
            case stimulus_details.MaskedStimulusDetailsPack():
                self.set_masked()
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
        elif (
            not np.isnan(self.current_stimulus.hold_after)
            and move_monocular_task.time >= self.current_stimulus.hold_after
        ):
            pass
        else:
            self.new_position = (
                -move_monocular_task.time
            ) * self.current_stimulus.velocity
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
        elif (
            not np.isnan(self.current_stimulus.hold_after[0])
            and move_binocular_task.time >= self.current_stimulus.hold_after[0]
        ):
            new_position_left = self.new_position[0]
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
        elif (
            not np.isnan(self.current_stimulus.hold_after[1])
            and move_binocular_task.time >= self.current_stimulus.hold_after[1]
        ):
            new_position_right = self.new_position[1]
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

    def set_masked(self):
        self.masked_stims = {}
        for n, masked_stim in enumerate(self.current_stimulus.masked_stim_details):
            x = masked_stim.position[0]
            y = masked_stim.position[1]

            ## CREATE TEXTURE STAGES ##
            tex_size = masked_stim.texture.texture_size
            tex = masked_stim.texture.texture

            texture_stage = TextureStage(f"texture_stage_{n}")
            mask = Texture(f"mask_texture_{n}")
            mask.setup2dTexture(
                tex_size[0], tex_size[1], Texture.T_unsigned_byte, Texture.F_luminance
            )
            mask_stage = TextureStage(f"mask_array_{n}")

            ## CREATE CARDS ###
            cardmaker = CardMaker("stimcard")
            cardmaker.setFrameFullscreenQuad()
            self.setBackgroundColor((0, 0, 0, 1))
            card = self.aspect2d.attachNewNode(cardmaker.generate())
            card.setScale(self.scale)

            # card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
            card.setAttrib(
                ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
            ## CREATE MASK ARRAYS ##
            mask_array = 255 * np.ones(
                (tex_size[0], tex_size[1]), dtype=np.uint8
            )
            xMaskMin = int(tex_size[0] * masked_stim.masking[0])
            xMaskMax = int(tex_size[0] * masked_stim.masking[1])
            yMaskMin = int(tex_size[1] * masked_stim.masking[2])
            yMaskMax = int(tex_size[1] * masked_stim.masking[3])
            mask_array[xMaskMin:xMaskMax, yMaskMin:yMaskMax] = 0

            ## ADD TEXTURE STAGES TO CARDS ##
            mask.setRamImage(mask_array)
            card.setTexture(texture_stage, tex)

            ## Multiply the texture stages together ##
            mask_stage.setCombineRgb(
                TextureStage.CMModulate,
                TextureStage.CSTexture,
                TextureStage.COSrcColor,
                TextureStage.CSPrevious,
                TextureStage.COSrcColor,
            )

            card.setTexture(mask_stage, mask)

            card.setTransparency(TransparencyAttrib.MAlpha)
            card.setAlphaScale(masked_stim.transparency)

            ### Do the transform things ###
            card.setTexRotate(
                texture_stage,
                masked_stim.angle + self.default_params["rotation_offset"],
            )
            card.setTexPos(texture_stage, x, y, 0)
            self.masked_stims[n] = {"card": card,
                                    "texture_stage": texture_stage,
                                    "x": x,
                                    "y": y,
                                    "finished": False}
        self.taskMgr.add(self.move_masks, "move_masks")

    def move_masks(self, move_mask_task):
        #to account for the time difference between protocol sending stimuli and moving mask, if a different
        #stim got send, end this immediately
        # if type(self.current_stimulus) != stimulus_details.MaskedStimulusDetailsPack:
        #     #get previous cards from the previous mask stims
        #     return move_mask_task.done

        finisheds = 0
        for masked_stim in self.masked_stims.values():
            if masked_stim["finished"] == True:
                finisheds += 1
        if finisheds == len(self.masked_stims):
            self.clear_cards()
            return move_mask_task.done

        for n, masked_stim in enumerate(self.current_stimulus.masked_stim_details):
            card = self.masked_stims[n]['card']
            texture_stage = self.masked_stims[n]['texture_stage']
            xPos = self.masked_stims[n]["x"]
            yPos = self.masked_stims[n]["y"]

            if move_mask_task.time <= masked_stim.stationary_time:
                pass
            elif move_mask_task.time >= masked_stim.duration != -1:
                if self.default_params["hold_onfinish"]:
                    if move_mask_task.time >= masked_stim.hold_after + masked_stim.duration:
                        card.detach_node()
                        self.masked_stims[n]['finished'] = True
                    if np.isnan(masked_stim.hold_after):
                        card.detach_node()
                        self.masked_stims[n]['finished'] = True
                else:
                    card.detach_node()
                    self.masked_stims[n]['finished'] = True

            else:
                new_position = (
                        -move_mask_task.time * masked_stim.velocity
                )
                card.setTexPos(
                    texture_stage,
                    new_position + xPos,
                    yPos,
                    0,
                )  # u, v, w

        return move_mask_task.cont

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
            try:
                for n, m in self.masked_stims.items():
                    m.card.detach_node()
            except:
                pass

            self.taskMgr.remove("move_monocular")
            self.taskMgr.remove("move_binocular")
            self.taskMgr.remove("move_masks")
            self.current_stimulus = None

    def trs_transform(self):
        """
        trs = translate-rotate-scale transform for mask stage
        panda3d developer rdb contributed to this code
        """
        ## highly recommend not monkeying with this too much

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
        print("MONOCULAR STIMULUS DETAILS:", stimulus_details.MonocularStimulusDetails())


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
                .joinpath(
                    r"Lib\site-packages\pandastim\resources\params\default_params.json"
                )
            )
            if os.path.exists(default_params_path):
                with open(default_params_path) as json_file:
                    self.default_params = json.load(json_file)
            else:
                self.default_params = None
                logging.error("no default parameters found")
        else:
            if os.path.exists(params_path):
                with open(params_path) as json_file:
                    self.default_params = json.load(json_file)
            else:
                self.default_params = None
                logging.error("no default parameters found")

        if not self.default_params:
            logging.info("initializing non-loaded params")
            self.default_params = {
                "rotation_offset": -90,
                "window_size": [1024, 1024],
                "window_position": [400, 400],
                "fps": 60,
                "window_undecorated": False,
                "center": [0, 0],
                "window_foreground": True,
                "window_title": "Pandastim",
                "profile_on": False,
                "projecting_fish": False,
                "hold_onfinish": True,
                "publish_port": 5010,
                "scale" : 8
            }

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

        self.setBackgroundColor(0, 0, 0)  # this makes the background true black

        ShowBaseGlobal.base.win.requestProperties(self.window_props)

        if self.default_params["profile_on"]:
            PStatClient.connect()
            ShowBaseGlobal.base.setFrameRateMeter(True)



class SequencingWithPause(StimulusSequencing):
    """
    this one can pause
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._print_counter = 0

        self.paused = False
        self.set_stimulus()

        self.accept("pause", self.pause)
        self.accept("unpause", self.unpause)

    def set_stimulus(self):
        # match stimulus to stimulus details type
        if not self.paused:
            super().set_stimulus()
            # print(self._print_counter)
            self._print_counter += 1
        else:
            self.buddy.proceed_alignment()

    def pause(self):
        self.paused = True
        if not self.current_stimulus:
            self.buddy.proceed_alignment()

    def unpause(self):
        if self.paused:
            self.paused = False
            self.clear_cards()
            self.set_stimulus()

    def buddy_task(self, buddytask):
        self.buddy.pauseStatus(self.paused)
        self.buddy.position(self.new_position)
        self.buddy.stimulus(self.current_stimulus)
        self.buddy.broadcaster()
        return buddytask.cont

    

class BrukerStimulus(SequencingWithPause):
    """
    this one works with head embedded behavior on a behavior rig, also talk to Stytra via a Stytrabuddy
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curr_id = 0
        self.next_stimulus = None #T^T


    def set_monocular(self):
        #PLAYGROUND
        tex = self.current_stimulus.texture.texture

        ## CREATE TEXTURE STAGES ##
        self.texture_stage = TextureStage("texture_stage")

        ## CREATE CARDS ###
        cardmaker = CardMaker("stimcard")
        cardmaker.setFrameFullscreenQuad()

        self.setBackgroundColor((0, 0, 0, 0))
        self.card = self.aspect2d.attachNewNode(cardmaker.generate())
        self.card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))

        # ADD TEXTURE STAGES TO CARDS
        self.card.setTexture(self.texture_stage, tex)

        ### Do the transform things ###
        self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle)
        self.card.setTexTransform(self.texture_stage, self.stage_transform)

        self.taskMgr.add(self.move_monocular, "move_monocular")

    def move_monocular(self, move_monocular_task):
        if move_monocular_task.time <= self.current_stimulus.stationary_time:
            # self.new_position = 0
            pass
        elif move_monocular_task.time >= self.current_stimulus.duration != -1:
            self.clear_cards()
            self.new_position = 0
            return move_monocular_task.done
        elif (
            not np.isnan(self.current_stimulus.hold_after)
            and move_monocular_task.time >= self.current_stimulus.hold_after
        ):
            pass
        else:#finally moving monucular
            #MATT CODE THAT WORKS
            self.new_position = (
                move_monocular_task.time - self.current_stimulus.stationary_time
            ) * self.current_stimulus.velocity
            self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle, self.new_position)
            self.card.setTexTransform(
                self.texture_stage, self.stage_transform
            )
            # self.card.setTexPos(
            #     self.texture_stage, self.new_position + self.center_x, self.center_y, 0
            # )  # u, v, w
        return move_monocular_task.cont

    def set_binocular(self):
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
            + self.current_stimulus.angle[0]#because that binocular stim is set up relative to the strip
            + self.rotation_offset
        )
        self.right_angle = (
            self.current_stimulus.strip_angle
            + self.current_stimulus.angle[1]#because that binocular stim is set up relative to the strip
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
        elif (
            not np.isnan(self.current_stimulus.hold_after[0])
            and move_binocular_task.time >= self.current_stimulus.hold_after[0]
        ):
            new_position_left = self.new_position[0]
        else:
            new_position_left = (move_binocular_task.time * self.current_stimulus.velocity[0])#remove -time because it works now
            self.left_card.setTexPos(
                self.left_texture_stage,
                new_position_left + self.current_stimulus.position[0],
                self.current_stimulus.position[1],
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
        elif (
            not np.isnan(self.current_stimulus.hold_after[1])
            and move_binocular_task.time >= self.current_stimulus.hold_after[1]
        ):
            new_position_right = self.new_position[1]
        else:
            new_position_right = (move_binocular_task.time * self.current_stimulus.velocity[1])#remove -time because it works now
            self.right_card.setTexPos(
                self.right_texture_stage,
                new_position_right + self.current_stimulus.position[0],
                self.current_stimulus.position[1],
                0,
            )  # u, v, w

        self.new_position = new_position_left, new_position_right

        if move_binocular_task.time >= max(
            self.current_stimulus.duration[0], self.current_stimulus.duration[1]
        ):
            self.clear_cards()
            return move_binocular_task.done

        return move_binocular_task.cont

    def set_masked(self):
        self.masked_stims = {}
        for n, masked_stim in enumerate(self.current_stimulus.masked_stim_details):
            x = masked_stim.position[0]
            y = masked_stim.position[1]

            ## CREATE TEXTURE STAGES ##
            tex_size = masked_stim.texture.texture_size
            tex = masked_stim.texture.texture

            texture_stage = TextureStage(f"texture_stage_{n}")
            mask = Texture(f"mask_texture_{n}")
            mask.setup2dTexture(
                tex_size[0], tex_size[1], Texture.T_unsigned_byte, Texture.F_luminance
            )
            mask_stage = TextureStage(f"mask_array_{n}")

            ## CREATE CARDS ###
            cardmaker = CardMaker("stimcard")
            cardmaker.setFrameFullscreenQuad()
            self.setBackgroundColor((0, 0, 0, 1))
            card = self.aspect2d.attachNewNode(cardmaker.generate())
            #card.setScale(self.scale)

            # card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))
            card.setAttrib(
                ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha, ColorBlendAttrib.OOne))
            ## CREATE MASK ARRAYS ##
            mask_array = 255 * np.ones(
                (tex_size[0], tex_size[1]), dtype=np.uint8
            )
            xMaskMin = int(tex_size[0] * masked_stim.masking[0])
            xMaskMax = int(tex_size[0] * masked_stim.masking[1])
            yMaskMin = int(tex_size[1] * masked_stim.masking[2])
            yMaskMax = int(tex_size[1] * masked_stim.masking[3])
            mask_array[xMaskMin:xMaskMax, yMaskMin:yMaskMax] = 0

            ## ADD TEXTURE STAGES TO CARDS ##
            mask.setRamImage(mask_array)
            card.setTexture(texture_stage, tex)

            ## Multiply the texture stages together ##
            mask_stage.setCombineRgb(
                TextureStage.CMModulate,
                TextureStage.CSTexture,
                TextureStage.COSrcColor,
                TextureStage.CSPrevious,
                TextureStage.COSrcColor,
            )

            card.setTexture(mask_stage, mask)

            card.setTransparency(TransparencyAttrib.MAlpha)
            card.setAlphaScale(masked_stim.transparency)

            ### Do the transform things ###
            stage_transform = self.trs_transform_mono(masked_stim.angle)
            card.setTexTransform(texture_stage, stage_transform)
            # card.setTexRotate(
            #     texture_stage,
            #     masked_stim.angle + self.default_params["rotation_offset"],
            # )
            # card.setTexPos(texture_stage, x, y, 0)
            self.masked_stims[n] = {"card": card,
                                    "texture_stage": texture_stage,
                                    "x": x,
                                    "y": y,
                                    "finished": False}
        self.taskMgr.add(self.move_masks, "move_masks")

    def move_masks(self, move_mask_task):
        #to account for the time difference between protocol sending stimuli and moving mask, if a different
        #stim got send, end this immediately
        # if type(self.current_stimulus) != stimulus_details.MaskedStimulusDetailsPack:
        #     #get previous cards from the previous mask stims
        #     return move_mask_task.done

        finisheds = 0
        for masked_stim in self.masked_stims.values():
            if masked_stim["finished"] == True:
                finisheds += 1
        if finisheds == len(self.masked_stims):
            self.clear_cards()
            return move_mask_task.done

        for n, masked_stim in enumerate(self.current_stimulus.masked_stim_details):
            card = self.masked_stims[n]['card']
            texture_stage = self.masked_stims[n]['texture_stage']
            xPos = self.masked_stims[n]["x"]
            yPos = self.masked_stims[n]["y"]

            if move_mask_task.time <= masked_stim.stationary_time:
                pass
            elif move_mask_task.time >= masked_stim.duration != -1:
                if self.default_params["hold_onfinish"]:
                    if move_mask_task.time >= masked_stim.hold_after + masked_stim.duration:
                        card.detach_node()
                        self.masked_stims[n]['finished'] = True
                    if np.isnan(masked_stim.hold_after):
                        card.detach_node()
                        self.masked_stims[n]['finished'] = True
                else:
                    card.detach_node()
                    self.masked_stims[n]['finished'] = True

            else:
                new_position = (move_mask_task.time - masked_stim.stationary_time) * masked_stim.velocity
                stage_transform = self.trs_transform_mono(masked_stim.angle, new_position)
                card.setTexTransform(
                    texture_stage, stage_transform
                )
                # new_position = (
                #         -move_mask_task.time * masked_stim.velocity
                # )
                # card.setTexPos(
                #     texture_stage,
                #     new_position + xPos,
                #     yPos,
                #     0,
                # )  # u, v, w

        return move_mask_task.cont


    def trs_transform(self):
        """
        trs = translate-rotate-scale transform for mask stage
        panda3d developer rdb contributed to this code
        """
        ## highly recommend not monkeying with this too much
        self.bin_center_x = 1 * self.center_y * self.scale
        self.bin_center_y = -1 * self.center_x * self.scale

        self.mask_position_uv = (self.bin_center_x, self.bin_center_y)

        pos = 0.5 + self.mask_position_uv[0], 0.5 + self.mask_position_uv[1]
        center_shift = TransformState.make_pos2d((-pos[0], -pos[1]))
        scale = TransformState.make_scale2d(1 / self.scale)
        rotate = TransformState.make_rotate2d(self.current_stimulus.strip_angle + self.strip_angle)#added the new strip angle
        translate = TransformState.make_pos2d((0.5, 0.5))

        return translate.compose(rotate.compose(scale.compose(center_shift)))

    def trs_transform_mono(self, stimulus_angle, new_position = 0):
        """
        trs = translate-rotate-scale transform for mask stage
        panda3d developer rdb contributed to this code
        """
        #calculate new_position in x and y direction
        angle = math.radians(self.strip_angle + stimulus_angle
                                              +self.rotation_offset)
        x_offset = math.sin(angle) * new_position
        y_offset = math.cos(angle) * new_position

        ## highly recommend not monkeying with this too much
        self.bin_center_x = 1 * (self.center_y + y_offset) * self.scale
        self.bin_center_y = -1 * (self.center_x + x_offset) * self.scale

        self.mask_position_uv = (self.bin_center_x, self.bin_center_y)

        pos = 0.5 + self.mask_position_uv[0], 0.5 + self.mask_position_uv[1]
        center_shift = TransformState.make_pos2d((-pos[0], -pos[1]))
        scale = TransformState.make_scale2d(1 / self.scale)
        rotate = TransformState.make_rotate2d(self.strip_angle + stimulus_angle
                                              +self.rotation_offset)
        translate = TransformState.make_pos2d((0.5, 0.5))

        return translate.compose(rotate.compose(scale.compose(center_shift)))

    def set_transforms(self):
        match self.current_stimulus:
            case stimulus_details.MonocularStimulusDetails():
                #MATT OG CODE THAT WORKS
                # self.card.setTexPos(self.texture_stage, self.center_x, self.center_y, 0)
                # self.card.setTexRotate(self.texture_stage,
                #    self.current_stimulus.angle
                #    + self.rotation_offset + 90
                #    + self.angle_rotation)
                #PLAYGROUND
                self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle)
                self.card.setTexTransform(
                    self.texture_stage, self.stage_transform
                )
            case stimulus_details.MaskedStimulusDetailsPack():
                for n in range(len(self.masked_stims)):
                    self.stage_transform = self.trs_transform_mono(self.current_stimulus.masked_stim_details[n].angle)
                    self.masked_stims[n]['card'].setTexTransform(
                        self.masked_stims[n]['texture_stage'], self.stage_transform
                    )
            case stimulus_details.BinocularStimulusDetails():
                self.mask_transform = self.trs_transform()
                self.left_angle = (
                    self.current_stimulus.angle[0]
                    + self.rotation_offset+90#because that binocular stim is set up relative to the strip
                    + self.angle_rotation
                )
                self.right_angle = (
                    self.current_stimulus.angle[1]
                    + self.rotation_offset+90#because that binocular stim is set up relative to the strip
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

    def update_stimulus(self):
        if self.current_stimulus is not None:
            if len(self.updating_info) == 1:
                # this is theta
                self.angle_rotation = self.updating_info[0]
                self.strip_angle = self.angle_rotation + self.rotation_offset
                self.set_transforms()
            elif len(self.updating_info) == 2:
                # this is X, Y
                self.center_x, self.center_y = self.updating_info
                self.set_transforms()
            elif len(self.updating_info) == 3:
                # this is X, Y, Theta
                self.center_x, self.center_y, self.angle_rotation = self.updating_info
                self.strip_angle = self.angle_rotation + self.rotation_offset
                self.set_transforms()

    def clear_cards(self):
        super().clear_cards()

    def buddy_task(self, buddytask):
        """talk to a stytrabuddy about what task the buddy should do"""
        self.buddy.pauseStatus(self.paused)
        self.buddy.position(self.new_position)
        self.fresh_stim = self.buddy.stimulus()
        # print(self.fresh_stim)


        #T^T : I think this is like THE core thing that needs to change
        self.updating, self.updating_info = self.buddy.request_updating()
        self.next_stimulus = self.buddy.request_stimulus()#request next stimulus from buddy


        #T^T DITTO
        if self.next_stimulus is not None:#if there is a stimulus change
            if isinstance(self.next_stimulus, stimulus_details.MonocularStimulusDetails)\
                or isinstance(self.next_stimulus, stimulus_details.BinocularStimulusDetails)\
                or isinstance(self.next_stimulus, stimulus_details.MaskedStimulusDetailsPack):#handles input of stimulus object
                self.clear_cards()
                self.current_stimulus = self.buddy._stim
                self.next_stimulus = None
                self.set_stimulus()
            else:
                print('stim input to stimulus.py has to be an object belong to stimulus_details class')
        elif self.updating:
            self.update_stimulus()
        self.buddy.broadcaster()#slight delay of one round in reporting new stimulus because we have to wait till buddy is updated faster

        return buddytask.cont

class TailLockedStimulus(BrukerStimulus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curr_id = 0
        self.next_stimulus = None
        self.strip_angle = 0 #ERR!!!! WARNING!!!! THIS IS PROBABLY WRONG
        self.curr_right_angle = self.curr_left_angle = self.new_position_left = self.new_position_right = 0

    def set_monocular(self):
        #PLAYGROUND
        tex = self.current_stimulus.texture.texture

        ## CREATE TEXTURE STAGES ##
        self.texture_stage = TextureStage("texture_stage")

        ## CREATE CARDS ###
        cardmaker = CardMaker("stimcard")
        cardmaker.setFrameFullscreenQuad()

        self.setBackgroundColor((0, 0, 0, 0))
        self.card = self.aspect2d.attachNewNode(cardmaker.generate())
        self.card.setAttrib(ColorBlendAttrib.make(ColorBlendAttrib.M_add))

        # ADD TEXTURE STAGES TO CARDS
        self.card.setTexture(self.texture_stage, tex)

        ### Do the transform things ###
        self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle)
        self.card.setTexTransform(self.texture_stage, self.stage_transform)

        self.curr_pos = 0

        self.taskMgr.add(self.move_monocular, "move_monocular")

    def move_monocular(self, move_monocular_task):
        if move_monocular_task.time <= self.current_stimulus.stationary_time:
            step = 0
            pass
        elif move_monocular_task.time >= self.current_stimulus.duration != -1:
            self.clear_cards()
            self.new_position = 0
            return move_monocular_task.done
        elif (
            not np.isnan(self.current_stimulus.hold_after)
            and move_monocular_task.time >= self.current_stimulus.hold_after
        ):
            step = 0
        else:
            step = ShowBaseGlobal.globalClock.getDt() * self.current_stimulus.velocity
        self.curr_pos += step
        self.new_position = self.curr_pos
        self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle, self.new_position)
        self.card.setTexTransform(
            self.texture_stage, self.stage_transform
        )

        return move_monocular_task.cont

    def set_binocular(self):
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
            + self.current_stimulus.angle[0]#because that binocular stim is set up relative to the strip
            + self.rotation_offset
        )
        self.right_angle = (
            self.current_stimulus.strip_angle
            + self.current_stimulus.angle[1]#because that binocular stim is set up relative to the strip
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
        self.curr_pos_right = self.current_stimulus.position[0]
        self.curr_pos_left = self.current_stimulus.position[0]
        self.taskMgr.add(self.move_binocular, "move_binocular")

    def move_binocular(self, move_binocular_task):
        ### LEFT SIDE ###
        if move_binocular_task.time <= self.current_stimulus.stationary_time[0]:
            step_left = 0
        elif move_binocular_task.time >= self.current_stimulus.duration[0] != -1:
            if self.default_params["hold_onfinish"]:
                step_left = 0
            else:
                self.left_card.detach_node()
                new_position_left = None
        elif (
            not np.isnan(self.current_stimulus.hold_after[0])
            and move_binocular_task.time >= self.current_stimulus.hold_after[0]
        ):
            step_left = 0
        else:
            step_left =  ShowBaseGlobal.globalClock.getDt() * self.current_stimulus.velocity[0]

        new_position_left = self.curr_pos_left + step_left
        self.left_card.setTexPos(
            self.left_texture_stage,
            new_position_left,
            self.current_stimulus.position[1],
            0,
        )  # u, v, w

        ### RIGHT SIDE ###
        if move_binocular_task.time <= self.current_stimulus.stationary_time[1]:
            step_right = 0
        elif move_binocular_task.time >= self.current_stimulus.duration[1] != -1:
            if self.default_params["hold_onfinish"]:
                step_right = 0
            else:
                self.right_card.detach_node()
                new_position_right = None
        elif (
            not np.isnan(self.current_stimulus.hold_after[1])
            and move_binocular_task.time >= self.current_stimulus.hold_after[1]
        ):
            step_right = 0
        else:
            step_right = ShowBaseGlobal.globalClock.getDt() * self.current_stimulus.velocity[1]

        new_position_right = self.curr_pos_right + step_right
        self.right_card.setTexPos(
            self.right_texture_stage,
            new_position_right,
            self.current_stimulus.position[1],
            0,
        )  # u, v, w

        self.new_position = new_position_left, new_position_right

        if move_binocular_task.time >= max(
            self.current_stimulus.duration[0], self.current_stimulus.duration[1]
        ):
            self.clear_cards()
            return move_binocular_task.done

        return move_binocular_task.cont

    def translate_cards_live(self):
        match self.current_stimulus:
            case stimulus_details.MonocularStimulusDetails():

                step = ShowBaseGlobal.globalClock.getDt() * self.forward_swimming * math.cos(self.current_stimulus.angle)
                self.curr_pos += step
                self.new_position = self.curr_pos
                self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle, self.new_position)
                self.card.setTexTransform(
                self.texture_stage, self.stage_transform
            )
            case stimulus_details.BinocularStimulusDetails():
                step_right  = (math.cos(self.curr_right_angle) * self.forward_swimming) * ShowBaseGlobal.globalClock.getDt()
                step_left  = (math.cos(self.curr_left_angle) * self.forward_swimming) * ShowBaseGlobal.globalClock.getDt()     
                self.curr_pos_right += step_right
                self.curr_pos_left += step_left
                self.right_card.setTexPos(
                    self.right_texture_stage,
                    self.curr_pos_right,
                    self.current_stimulus.position[1],
                    0,
                )
                self.left_card.setTexPos(
                    self.left_texture_stage,
                    self.curr_pos_left,
                    self.current_stimulus.position[1],
                    0,
                )
            case stimulus_details.MaskedStimulusDetailsPack():
                print("Sorry, MaskedStimulusDetails have not been implemented")
            case _:
                print(
                    f"{self.current_stimulus.__class__} -- Stimulus type not understood, transform failed"
                )

    def set_transforms(self):

        match self.current_stimulus:
            case stimulus_details.MonocularStimulusDetails():

                self.stage_transform = self.trs_transform_mono(self.current_stimulus.angle + self.turning)
                self.card.setTexTransform(
                    self.texture_stage, self.stage_transform
                )
            case stimulus_details.MaskedStimulusDetailsPack():
                for n in range(len(self.masked_stims)):
                    self.stage_transform = self.trs_transform_mono(self.current_stimulus.masked_stim_details[n].angle)
                    self.masked_stims[n]['card'].setTexTransform(
                        self.masked_stims[n]['texture_stage'], self.stage_transform
                    )
            case stimulus_details.BinocularStimulusDetails():
                self.mask_transform = self.trs_transform()
                self.left_angle = (
                    self.current_stimulus.angle[0]
                    + self.rotation_offset+90#because that binocular stim is set up relative to the strip
                    + self.angle_rotation
                )
                self.right_angle = (
                    self.current_stimulus.angle[1]
                    + self.rotation_offset+90#because that binocular stim is set up relative to the strip
                    + self.angle_rotation
                )

                # Left texture
                self.left_card.setTexTransform(
                    self.left_mask_stage, self.mask_transform
                )
                self.left_card.setTexScale(self.left_texture_stage, 1 / self.scale)
                self.curr_left_angle  = self.left_angle + self.turning
                self.left_card.setTexRotate(self.left_texture_stage, self.curr_left_angle)

                # Right texture
                self.right_card.setTexTransform(
                    self.right_mask_stage, self.mask_transform
                )
                self.right_card.setTexScale(self.right_texture_stage, 1 / self.scale)
                self.curr_right_angle = self.right_angle + self.turning
                self.right_card.setTexRotate(self.right_texture_stage, self.curr_right_angle)

            case _:
                print(
                    f"{self.current_stimulus.__class__} -- Stimulus type not understood, transform failed"
                )

    def update_stimulus(self):

        if len(self.updating_info) == 2:
            self.turning = self.updating_info[0]
            self.forward_swimming = self.updating_info[1]
            self.translate_cards_live()
            self.set_transforms()
        else:
            print(f"ERR: Recieved data is of length {len(self.updating_info)}.  It expected to be of length 2.")

        #NOTE: might dip in to this if I do a fish-locked strip angle
        # if self.current_stimulus is not None:
        #     if len(self.updating_info) == 1:
        #         # this is theta
        #         self.angle_rotation = self.updating_info[0]
        #         self.strip_angle = self.angle_rotation + self.rotation_offset
        #         self.set_transforms()
        #     elif len(self.updating_info) == 2:
        #         # this is X, Y
        #         self.center_x, self.center_y = self.updating_info
        #         self.set_transforms()
        #     elif len(self.updating_info) == 3:
        #         # this is X, Y, Theta
        #         self.center_x, self.center_y, self.angle_rotation = self.updating_info
        #         self.strip_angle = self.angle_rotation + self.rotation_offset
        #         self.set_transforms()
