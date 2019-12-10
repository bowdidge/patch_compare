#!/usr/bin/python
# Decode a Reface DX patch.
#
# Contents partially borrowed from Martin Tarenskeen's Reface DX
# legacy project.
#
# Robert Bowdidge, December 2019.

import math
import mido
import os
import sys

import patch

STRING_TYPE = patch.STRING_TYPE
POSITIVE_TYPE = patch.POSITIVE_TYPE
SELECT_TYPE = patch.SELECT_TYPE
PLUS_MINUS_TYPE = patch.PLUS_MINUS_TYPE
#LFO Speed                                                                      
debug = False

# Speed of LFO in Hertz?
lfo_speed_secs = [
    0.0263, 0.0421, 0.0841, 0.1262, 0.1682, 0.2103, 0.2524, 0.2944,
    0.3364, 0.3723, 0.4120, 0.4560, 0.5047, 0.5423, 0.5827, 0.6261,
    0.6728, 0.7114, 0.7523, 0.7954, 0.8411, 0.8803, 0.9213, 0.9642,
    1.0091, 1.0488, 1.0901, 1.1330, 1.1776, 1.2175, 1.2588, 1.3014,
    1.3455, 1.3858, 1.4273, 1.4700, 1.5140, 1.5543, 1.5956, 1.6380,
    1.6815, 1.7223, 1.7640, 1.8067, 1.8505, 1.8910, 1.9323, 1.9746,
    2.0178, 2.0587, 2.1006, 2.1432, 2.1867, 2.2274, 2.2689, 2.3111,
    2.3540, 2.3953, 2.4372, 2.4799, 2.5233, 2.5643, 2.6060, 2.6483,
    2.6914, 2.7717, 2.8545, 2.9398, 3.0276, 3.1080, 3.1906, 3.2754,
    3.3625, 3.4441, 3.5277, 3.6133, 3.7010, 3.8585, 4.0228, 4.1940,
    4.3725, 4.5324, 4.6981, 4.8699, 5.0480, 5.2061, 5.3693, 5.5375,
    5.7110, 6.0235, 6.3530, 6.7006, 7.0671, 7.3811, 7.7089, 8.0514,
    8.4090, 8.7273, 9.0575, 9.4003, 9.7561, 10.2908, 10.8548, 11.4498,
    12.0773, 12.7102, 13.3762, 14.0771, 14.8148, 15.4396, 16.2486, 17.1001,
    17.4764, 18.5376, 19.6633, 20.8574, 22.1239, 23.3385, 24.6198, 25.9714,
    27.3973, 28.9017, 30.3030, 31.6456, 33.0033, 34.3643, 37.0370, 39.6825]

# LFO starting delay.
rdx_dtimes = (
        0011.6, 0019.9, 0028.0, 0036.2, 0044.3, 0052.5, 0060.6, 0068.8,
        0077.0, 0085.2, 0093.3, 0101.5, 0109.6, 0117.8, 0125.9, 0134.1,
        0142.3, 0150.4, 0158.6, 0166.7, 0174.9, 0183.0, 0191.2, 0199.3,
        0207.4, 0215.6, 0223.7, 0231.9, 0240.1, 0248.2, 0256.4, 0264.6,
        0272.8, 0280.9, 0289.0, 0297.2, 0305.3, 0313.5, 0321.6, 0329.7,
        0337.9, 0346.0, 0354.2, 0362.3, 0370.4, 0378.6, 0386.7, 0394.9,
        0403.0, 0411.2, 0419.3, 0427.5, 0435.7, 0443.8, 0452.0, 0460.2,
        0468.3, 0479.4, 0490.5, 0501.6, 0512.7, 0523.7, 0534.8, 0545.9,
        0557.0, 0567.2, 0577.4, 0587.7, 0597.9, 0608.1, 0618.3, 0628.5,
        0638.8, 0648.9, 0659.1, 0669.2, 0679.4, 0689.5, 0699.7, 0709.8,
        0720.0, 0730.3, 0740.6, 0750.9, 0761.3, 0771.6, 0781.9, 0792.2,
        0802.5, 0812.7, 0822.9, 0833.1, 0843.3, 0853.4, 0863.6, 0873.8,
        0884.0, 0894.3, 0904.5, 0914.8, 0925.0, 0935.3, 0945.5, 0955.8,
        0966.0, 0976.3, 0986.5, 0996.8, 1007.0, 1017.3, 1027.5, 1037.8,
        1048.0, 1058.2, 1068.4, 1078.6, 1088.9, 1099.1, 1109.3, 1119.5,
        1129.7, 1139.9, 1150.1, 1160.3, 1170.6, 1180.8, 1191.0, 1201.0)

# Reface DX FM algorithms.  Each sequence of dashes indicates a chain of
# connections.
algorithm_name_dict = {0: '1-2-3-4', 1: '1-2 2-4 3-4',
                   2: '1-2-3 1-4', 3: '1-2-4 1-3-4',
                   4: '1-2 1-3 1-4', 5: '1 2-3-4',
                   6: '1-3-4 1-2-4', 7: '1-2 3-4',
                   8: '1-4 2-4 3-4', 9: '1 2-4 3-4',
                   10: '1 2 3-4', 11: '1 2 3 4'}

# Purpose of each operator in a particular algorithm.
# Operators can be carriers if they generate the actual sound,
# or modulators if they affect other operators.
#
# Operators are 1-indexed; 0 index is unused.
purpose_dict = [
    ['', 'carrier', 'modulator', 'modulator-2', 'modulator-3'],
    ['', 'carrier', 'modulator', 'modulator-2', 'modulator-2'],
    ['', 'carrier', 'modulator', 'modulator-2', 'modulator'],
    ['', 'carrier', 'modulator', 'modulator', 'modulator-2'],
    ['', 'carrier', 'modulator', 'modulator', 'modulator'],
    ['', 'carrier', 'carrier', 'modulator', 'modulator-2'],
    ['', 'carrier', 'carrier', 'modulator', 'modulator-2'],
    ['', 'carrier', 'modulator', 'carrier', 'modulator'],
    ['', 'carrier', 'carrier', 'carrier', 'modulator'],
    ['', 'carrier', 'carrier', 'carrier' 'modulator'],
    ['', 'carrier', 'carrier', 'carrier', 'modulator'],
    ['', 'carrier', 'carrier', 'carrier', 'carrier']
]

part_mode_dict = {0:'poly', 1:'mono-full', 2: 'mono-legato'}

lfo_wave_dict = {0: 'sine', 1: 'triangle', 2: 'saw up', 3: 'saw down',
               4: 'squre', 5: 'sample and hold 8', 6: 'sample and hold'}
freq_mode_dict = {0: 'Ratio', 1: 'Fixed'}                            
feedback_type_dict = {0: 'sawtooth', 1: 'square'}
effect_type_dict = {0: 'Thru', 1: 'Distortion', 2: 'Touch wah',
                    3: 'Chorus', 4: 'Flanger', 5: 'Phaser', 6: 'Delay',
                    7: 'Reverb'}

refacedx_select_styles = {
    'patch_part': part_mode_dict,
    'patch_lfo_wave': lfo_wave_dict,
    'patch_algorithm': algorithm_name_dict,
    'effect_1_type': effect_type_dict,
    'effect_2_type': effect_type_dict,
}

refacedx_definitions = [
    ('patch', 'name', 0, 10, STRING_TYPE),
    # -40
    ('patch', 'transpose', 12, 1, POSITIVE_TYPE), 
    ('patch', 'part_mode', 13, 1, POSITIVE_TYPE),
    ('patch', 'port_time', 14, 1, POSITIVE_TYPE),
    # - 40
    ('patch', 'pitch_bend_range', 15, 1, POSITIVE_TYPE),
    ('patch', 'algorithm', 16, 1, SELECT_TYPE),
    ('patch', 'lfo_wave', 17, 1, SELECT_TYPE),
    ('patch', 'lfo_speed', 18, 1, POSITIVE_TYPE),
    ('patch', 'lfo_delay', 19, 1, POSITIVE_TYPE),
    ('patch', 'lfo_pitch_mod', 20, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_rate_1', 21, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_rate_2', 22, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_rate_3', 23, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_rate_4', 24, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_level_1', 25, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_level_2', 26, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_level_3', 27, 1, POSITIVE_TYPE),
    ('patch', 'pitch_eg_level_4', 28, 1, POSITIVE_TYPE),
    ('effect_1', 'type', 29, 1, SELECT_TYPE),
    ('effect_2', 'type', 32, 1, SELECT_TYPE),
    # Separate messages for each voice.
    ]

refacedx_voice_definitions = [
    ('voice', 'number', 0, 1, POSITIVE_TYPE),
    ('voice', 'eg_rate_1', 1, 1, POSITIVE_TYPE),
    ('voice', 'eg_rate_2', 2, 1, POSITIVE_TYPE),
    ('voice', 'eg_rate_3', 3, 1, POSITIVE_TYPE),
    ('voice', 'eg_rate_4', 4, 1, POSITIVE_TYPE),
    ('voice', 'eg_level_1', 5, 1, POSITIVE_TYPE),
    ('voice', 'eg_level_2', 6, 1, POSITIVE_TYPE),
    ('voice', 'eg_level_3', 7, 1, POSITIVE_TYPE),
    ('voice', 'eg_level_4', 8, 1, POSITIVE_TYPE),
    ('voice', 'eg_rate_scaling', 9, 1, POSITIVE_TYPE),
    ('voice', 'kbd_level_scale_left', 10, 1, POSITIVE_TYPE),
    ('voice', 'kbd_level_scale_right', 11, 1, POSITIVE_TYPE),
    ('voice', 'kbd_level_curve_left', 12, 1, POSITIVE_TYPE),
    ('voice', 'kbd_level_curve_right', 13, 1, POSITIVE_TYPE),
    ('voice', 'lfo_amd_depth', 14, 1, POSITIVE_TYPE),
    ('voice', 'lfo_pmd_on', 15, 1, POSITIVE_TYPE),
    ('voice', 'peg_on', 16, 1, POSITIVE_TYPE),
    ('voice', 'velocity_sensitivity', 17, 1, POSITIVE_TYPE),
    ('voice', 'output_level', 18, 1, POSITIVE_TYPE),
    ('voice', 'feedback_level', 19, 1, POSITIVE_TYPE),
    ('voice', 'feedback_type', 20, 1, POSITIVE_TYPE),
    ('voice', 'freq_mode', 21, 1, POSITIVE_TYPE),
    ('voice', 'freq_coarse', 22, 1, POSITIVE_TYPE),
    ('voice', 'freq_fine', 23, 1, POSITIVE_TYPE),
    ('voice', 'freq_detune', 24, 1, PLUS_MINUS_TYPE),
]

class RefaceDXPatch(patch.Patch):

    def __init__(self, filepath):
        super(RefaceDXPatch, self).__init__(filepath, cc_offset=6)
        self.manufacturer_string = '0x43'
        self.device = 'refacedx'
        self.settings['device'] = self.device
        self.settings['filename'] = os.path.basename(filepath)
        self.settings['source'] = os.path.basename(filepath)
        self.definitions = refacedx_definitions
        self.select_styles = refacedx_select_styles
        self.cc_offset = 11

    def compare(self, patch):
        return 0.0

    def asDict(self):
        result = super(RefaceDXPatch, self).asDict()
        # Insert graphs here.

        # Parse the separate Sysex messages for each voice.
        # TODO(bowdidge): Find a better way to parse and record.
        result['voice_1'] = super(RefaceDXPatch, self).asDict(definitions=refacedx_voice_definitions,
                                                              group_key='voice_1')
        result['voice_2'] = super(RefaceDXPatch, self).asDict(definitions=refacedx_voice_definitions,
                                                              group_key='voice_2')
        result['voice_3'] = super(RefaceDXPatch, self).asDict(definitions=refacedx_voice_definitions,
                                                              group_key='voice_3')
        result['voice_4'] = super(RefaceDXPatch, self).asDict(definitions=refacedx_voice_definitions,
                                   group_key='voice_4')
        for voice in ['voice_1', 'voice_2', 'voice_3', 'voice_4']:
            result[voice]['eg_graph'] = self.eg_graph(result[voice]['voice_eg_rate_1'],
                                                      result[voice]['voice_eg_level_1'],
                                                      result[voice]['voice_eg_rate_2'],
                                                      result[voice]['voice_eg_level_2'],
                                                      result[voice]['voice_eg_rate_3'],
                                                      result[voice]['voice_eg_level_3'],
                                                      result[voice]['voice_eg_rate_4'],
                                                      result[voice]['voice_eg_level_4'])
                                                                    
        return result

def read_patches(filepath):
    """Read a DX patch at the given file path.
    
    Reface DX patches have one sysex for the main patch, and separate sysex
    messages for each voice.  We'll assume everything in the same sysex
    file is for a single patch.
    """
    patches = []
    current_patch = None
    messages = mido.read_syx_file(filepath)
    for message in messages:
        bytes = message.bin()
        if (bytes[0] != 0xf0 or bytes[1] != 0x43 or bytes[2] != 0x0 or
            bytes[3] != 0x7f or bytes[4] != 0x1c):
            print 'Not reface DX patch.'
            print '%x %x %x %x %x' % (bytes[0], bytes[1], bytes[2],
                                      bytes[3], bytes[4])

        if len(bytes) == 13:
            # header
            pass
        elif len(bytes) == 51:
            # Patch.
            if current_patch:
                patches.append(current_patch)
            current_patch = RefaceDXPatch(filepath)
            current_patch.collection = os.path.basename(os.path.dirname(filepath))
            current_patch.parse(message.bin())
            current_patch.name = current_patch.settings['patch_name']
            voice_number = 1
        elif len(bytes) == 41:
            # Voice
            current_patch.parse(message.bin(),
                                definitions=refacedx_voice_definitions,
                                group_key='voice_%d' % voice_number)
            voice_number += 1
                                
        else:
            print 'Unknown reface dx message in %s' % filepath
    if current_patch:
        patches.append(current_patch)
    return patches
                

