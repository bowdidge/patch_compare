#!/usr/bin/env python2.7
#
# Decode a patch for an Access Virus.
#
# Taken from a combination of Access documents (Virus C reference manual, odd
# CC lists) and personal examination.
#
# Robert Bowdidge, December 2019.
#
# Expected:
#
# Sysex single dump
# f0 00 20 33   SYSEX, MFF
# 01 xx         device number
# 10 xx         bank number
# 7f            program number
# 0c
# 20
# xx CC 0

import math
import mido
import os

import patch

categories = {0: 'off', 1: 'lead', 2: 'bass', 3: 'pad',
              4: 'decay', 5: 'pluck', 6: 'acid', 7: 'classic',
              8: 'arpeggiator', 9: 'EFX', 10: 'drums', 11: 'percussion',
              14: 'Favourites 1',
              17: 'organ', 18: 'piano', 19: 'string', 20: 'FM',
              21: 'digital'}

arpeggio_rates = {0: 'off', 1: '1/128', 2: '1/64', 3: '1/48',
                  4: '3/128', 5: '1/32', 6: '1/24', 7: '3/64',
                  8: '1/16', 9: '1/12', 10: '3/32', 11: '1/8',
                  12: '1/6', 13: '3/16', 14: '1/4', 15: '1/3',
                  16: '3/8', 17: '1/2'}

lfo_rates={0: 'off', 1: '1/64', 2: '1/32', 3: '1/24',
           4: '3/64', 5: '1/16', 6: '1/12', 7: '3/32',
           8: '1/8', 9: '1/6', 10: '3/16', 11: '1/4',
           12: '1/3', 13: '1/2', 14: '2/3', 15: '3/4',
           16: '1/1', 17: '2/1', 18: '4/1', 19: '8/1',
           20: '16/1'}

mod_sources = {0: 'Off',
               1: 'Pitch Bend',
               2: 'Chan Pressure',
               3: 'Mod Wheel',  # verif
               4: 'Breath',
               5: 'Controller 3',
               6: 'Foot Pedal',
               7: 'Data Entry',
               8: 'Balance',
               9: 'Controller 9',
               10: 'Expression',
               11: 'Controller 12',
               12: 'Controller 13',
               13: 'Controller 14',
               14: 'Controller 15',
               15: 'Controller 16',
               16: 'Hold Pedal',
               17: 'Portamento Sw',
               18: 'Sost Pedal',
               19: 'Amp Envelope',
               20: 'Filter Envelope',
               21: 'LFO 1 bipolar',
               22: 'LFO 2 bipolar',
               23: 'LFO 3 bipolar',
               24: 'Velocity On',
               25: 'Velocity Off',
               26: 'Keyfollow',
               27: 'Random',
               28: 'Arp Input',
               # End of Virus C choices.
               29: 'Envelope 3',
               30: 'LFO 2 unipolar',
               31: 'LFO 3 unipolar',
               32: '1% Constant',
               33: 'Arp Input',
               34: 'AnaKey1 Fine',
               35: 'AnaKey2 Fine',
               36: 'AnaKey1 Coarse',
               37: 'AnaKey2 Coarse',
               39: 'Envelope 4',
               98: '10% Constant',
               # Not seen yet
               101: 'LFO 1 unipolar',
               102: 'Velocity Off',
               103: 'LFO 3 unipolar',
               }

mod_dests = {0: 'Off',
             1: 'Patch Volume',
             2: 'Osc 1 Interpolation',
             3: 'Panorama',
             4: 'Transpose',
             5: 'Portamento',
             6: 'Osc 1 Shape/Index',
             7: 'Osc 1 Pulse Width',
             8: 'Osc 1 Wave Select',
             9: 'Osc 1 Pitch',
             10: 'Slot 6 Amount 3',
             11: 'Osc 2 Shape/Index',
             12: 'Osc 2 Pulse Width',
             13: 'Osc 2 Wave Select',
             14: 'Osc 2 Pitch',
             15: 'Osc 2 Detune',
             16: 'Osc 2 FM Amount',
             18: 'FiltEnv>FM/Sync',
             19: 'Osc 2 Interpolation',
             20: 'Osc Balance',
             21: 'Sub Osc Volume',
             22: 'Osc Volume',
             23: 'Noise Volume',
             24: 'Filter 1 Cutoff',
             25: 'Filter 2 Cutoff',
             26: 'Filter 1 Resonance',  # Verif
             27: 'Filter 2 Resonance',
             28: 'Filter 1 Env Amount',
             29: 'Filter 2 Env Amount',
             30: 'Slot 5 Amount 2',
             31: 'Slot 5 Amount 3',
             32: 'Filter Balance',
             33: 'Filter Env Attack',
             34: 'Filter Env Decay',
             35: 'Filter Env Sustain',
             36: 'Filter Env Slope',
             37: 'Filter Env Release',
             38: 'Amp Env Attack',
             39: 'Amp Env Decay',
             40: 'Amp Env Sustain',
             41: 'Amp Env Slope',
             42: 'Amp Env Release',
             43: 'LFO 1 Rate',
             44: 'LFO 1 Contour',
             45: 'LFO 1>Osc 1 Pitch',
             46: 'LFO 1>Osc 2 Pitch',
             49: 'LFO 1>Filter Gain',
             50: 'LFO 2 Rate',
             51: 'LFO 2 Contour',
             52: 'LFO 2>Shape',
             53: 'LFO 2>FM Amount',
             54: 'LFO 2>Cutoff 1',
             55: 'LFO 2>Cutoff 2',
             56: 'LFO 2>Panorama',  # 03 19 16
             57: 'LFO 3 Rate',
             58: 'LFO 3 Assign Amt',
             59: 'Unison Detune',
             60: 'Pan Spread',
             61: 'Unison LFO Phase',
             62: 'Chorus Mix',
             63: 'Chorus Mod Rate',
             64: 'Chorus Mod Depth',
             65: 'Chorus Delay',
             66: 'Chorus Feedback',
             67: 'Delay Send',
             68: 'Delay Time',
             69: 'Delay Feedback',
             70: 'Delay Mod Rate',
             71: 'Delay Mod Depth',
             72: 'Reverb Send',
             73: '-reserved (73)-',
             74: '-reserved (74)-',
             75: 'Slot 6 Amount 2',
             76: 'Slot 4 Amount 2',
             77: 'Slot 4 Amount 3',
             78: 'Filterbank Reso',
             79: 'Filterbank Poles',
             82: 'Slot 1 Amount 1',
             83: 'Slot 2 Amount 1',
             84: 'Slot 2 Amount 2',
             85: 'Slot 3 Amount 1',
             86: 'Slot 3 Amount 2',
             87: 'Slot 3 Amount 3',
             88: '-reserved(88)-',
             89: 'Punch Intensity',
             90: 'Ring Modulator',
             91: 'Noise Color',
             92: 'Delay Colorization',
             94: 'Slot 1 Amount 3',
             95: 'Distortion Intensity',
             96: 'FreqShifter Freq',
             97: 'Osc 3 Volume',
             98: 'Osc 3 Pitch',
             99: 'Osc 3 Detune',
             100: 'LFO 1 Assign Amount',
             101: 'LFO 2 Assign Amount',
             102: 'Phaser Mix',
             103: 'Phaser Mod Rate',
             104: 'Phaser Mod Frequency',
             105: 'Phaser Frequency',
             106: 'Phaser Feedback',
             108: 'Reverb Time',
             113: 'Surround Balance',
             114: 'Arp Note Length',
             117: 'EQ Mid Gain',
             118: 'EQ Mid Frequency',
             120: 'Slot 4 Amount 1',
             121: 'Slot 5 Amount 1',
             122: 'Slot 6 Amount 1',
             123: 'Osc 1 F-Shift',
             124: 'Osc 2 F-Shift',
             125: 'Osc 1 F-Spread',
             126: 'Osc 2 F-Spread',
             127: 'Distortion Mix',
             }

soft_knob_functions = {0: 'Off',
                       1: 'Modulation Wheel',
                       2: 'Breath',
                       3: 'Control 03',
                       4: 'Foot',
                       5: 'Data Entry',
                       6: 'Balance',
                       7: 'Control 09',
                       8: 'Expression',
                       9: 'Control 12',
                       10: 'Controller 13',
                       11: 'Controller 14',
                       12: 'Controller 15',
                       13: 'Controller 16',
                       14: 'Patch Volume',
                       15: 'Channel Volume',
                       16: 'Panorama',
                       17: 'Transpose',
                       18: 'Portamento',
                       19: 'Unison Detune',
                       20: 'Unison Pan Spread',
                       21: 'Unison LFO Phase',
                       22: 'Chorus Mix',
                       23: 'Chorus Rate',
                       24: 'Chorus Depth',
                       25: 'Chorus Delay',
                       26: 'Chorus Feedback',
                       27: 'Effect Send',
                       28: 'DelayTime',
                       29: 'Delay Feedback',
                       30: 'Delay Rate',
                       31: 'Delay Depth',
                       32: 'Osc 1 Wave Select',
                       33: 'Osc 1 Pulse Width',
                       34: 'Osc 1 Semitone',
                       35: 'Osc 1 Keyfollow',
                       36: 'Osc 2 Wave Select',
                       37: 'Osc 2 Pulse Width',
                       38: 'Osc 2 Env Amount',
                       39: 'FM Env Amount',
                       40: 'Filter 2 Env Amount',
                       41: 'Filter 1 Key Follow',
                       42: 'Filter 2 Key Follow',
                       43: 'LFO 1 Symmetry',
                       44: 'LFO 1 > Osc 1',
                       45: 'LFO 1 > Osc 2',
                       46: 'LFO 1 > Pulse Width',
                       47: 'LFO 1 Resonance',
                       57: 'LFO 2 > Cutoff 1',
                       73: 'Assign 2 Amount 1',
                       81: 'Filterbank Slope',
                       82: 'Ring Modulator',
                       83: 'LFO 2 > Panorama',
                       85: 'Analog Boost Int',
                       87: 'Distortion Intensity',
                       88: 'FreqShifter Freq',
                       94: 'Phaser Mix',
                       96: 'Phaser Depth',
                       98: 'Phaser Feedback',
                       101: 'Reverb Damping',
                       106: 'Arp Pattern',
                       109: 'Arp Swing',
                       112: 'EQ Mid Gain',
                       118: 'Effect Send (Revb)',
                       127: 'Freq Shifter Mix',
                       }
soft_knob_names = {0: '>Para',
                   1: 'EqMid',
                   3: '+5ths',
                   5: '+Octave',
                   7: 'ArpMode',
                   8: 'ArpOct',
                   9: 'Attack',
                   11: 'Tone',
                   12: 'Cutoff',
                   13: 'Decay',
                   14: 'Delay',
                   15: 'Depth',
                   16: 'Destroy',
                   17: 'Detune',
                   18: 'Dissolve',
                   19: 'Distort',
                   21: 'Effects',
                   22: 'Width',
                   23: 'Energy',
                   26: 'EqMid',
                   28: 'Fear',
                   29: 'Filter',
                   30: 'FM',
                   31: 'Glide',
                   33: 'Hype',
                   34: 'Infect',
                   35: 'Length',
                   36: 'Mix',
                   37: 'Morph',
                   38: 'Mutate',
                   39: 'Noise',
                   40: 'Open',
                   41: 'Orbit',
                   42: 'Flanger',
                   43: 'Phaser',
                   45: 'Pitch',
                   46: 'Pulsate',
                   49: 'Rate',
                   50: 'Release',
                   51: 'Reso',
                   52: 'Reverb',
                   53: 'Scream',
                   54: 'Shape',
                   55: 'Sharpen',
                   56: 'Slow',
                   57: 'Soften',
                   59: 'SubOsc',
                   61: 'Sweep',
                   62: 'Swing',
                   64: 'Thinner',
                   65: 'Tone',
                   66: 'Tremolo',
                   67: 'Chorus',
                   69: 'Warmth',
                   70: 'Warp',
                   71: 'Width',
                   72: 'Bite',
                   73: 'Soften',
                   74: 'RingMod',
                   75: 'Phatter',
                   77: 'Modulate',
                   78: 'Party!',
                   80: 'F-Shift',
                   81: 'F-Spread',
                   83: 'Muscle',
                   86: 'Comb',
                   89: 'Elevate',
                   118: 'Infect',
                   0x5e: 'Chorus'
}

wave_shape = {}
wave_shape[0] = 'Spectral Wave'
for i in range(1,63):
    wave_shape[i] = 'Wave>Saw %d%%' % (i * 100 / 64)
wave_shape[64] = 'Sawtooth'
for i in range(65, 126):
    wave_shape[i] = 'Saw>Pulse %d%%' % ((i - 64) * 100 / 64)
wave_shape[127] = 'Pulse'

# Spectral waves are different from wavetables.
# Guesses about types from
# http://www.infekted.org/virus/showthread.php?t=25580&page=2.
spectral_waveforms = {
    0: 'Sine',
    1: 'Tri',
    2: 'Wave 3',
    3: 'Wave 4',
    4: 'Piano',
    5: 'Wave 6',
    6: 'Vocal',
    7: 'Violin',
    8: 'Acid',
    19: 'Wave 10',
    10: 'Wave 11',
    11: 'Wave 12',
    12: 'Piano 2',
    13: 'Bell',
    14: 'Vocal 2',
    15: 'Metal',
    16: 'Violin 2',
    17: 'Wave 18',
    18: 'Reed',
    19: 'Guitar',
    20: 'Violin 3',
    21: 'Violin 4',
    22: 'Bass',
    23: 'Wave 24',
    24: 'Wave 25',
    25: 'Wind',
    26: 'Violin 5',
    27: 'Brass',
    28: 'Violin 6',
    29: 'Mallet',
    30: 'Wave 31',
    31: 'Wave 32',
    32: 'Wave 33',
    33: 'Wave 34',
    34: 'Wave 35',
    35: 'Wave 36',
    36: 'Violin 7',
    37: 'Brass 2',
    38: 'Violin 8',
    39: 'Violin 9',
    40: 'Bass/Guitar/Vocal',
    41: 'Bell 2',
    42: 'Piano 3',
    43: 'Reed 2',
    44: 'Wave 45',
    45: 'Bell 3',
    46: 'Organ',
    47: 'Organ 2',
    48: 'Organ 3',
    49: 'Wave 50',
    50: 'Bass 2',
    51: 'Violin/Vocal',
    52: 'Bell 4',
    53: 'Piano/Violin',
    54: 'Piano 4',
    55: 'Piano 5',
    56: 'Saw/Sync',
    57: 'Bell',
    58: 'Bass 2',
    59: 'Bass 3',
    60: 'FM',
    61: 'FM 2',
    62: 'FM 3',
    63: 'FM/Violin',
}
waveforms = {0: 'Sine',
             1: 'HarmoncSweep', 2: 'GlassSweep',
             8: 'Opposition',
             12: 'Robot Wars',
             16: 'Waterphone',
             27: 'Majestix',
             29: 'Resynater',
             31: 'Sawsalito',
             39: 'Buzzpartout',
             41: 'Overbones',
             42: 'Pulsechecker',
             46: 'Didgitalis',
             47: 'Evil',
             50: 'Release',
             52: 'EatPulse',
             54: 'Sine System',
             58: 'Pling Saw',
             63: 'Formantera',
             70: 'Solenoid',
             89: 'Whizzfizz',
             93: 'Fibonice',
             94: 'FIbonasty',
             96: 'Blinder',}

access_select_styles = {
    'osc1_mode': {0: 'Classic',
                  1: 'Hypersaw',
                  2: 'Wavetable',
                  3: 'Wave PWM',
                  4: 'Grain Simple',
                  5: 'Grain Complex',
                  6: 'Formant Simple',
                  7: 'Formant Complex'
                  },
    'osc2_mode': {0: 'Classic',
                  1: 'Hypersaw',
                  2: 'Wavetable',
                  3: 'Wave PWM',
                  4: 'Grain Simple',
                  5: 'Grain Complex',
                  6: 'Formant Complex',
                  },
    'osc1_shape': wave_shape,
    'osc2_shape': wave_shape,

    'osc1_wave': waveforms,
    'osc1_spectral_wave': spectral_waveforms,
    'osc2_wave': waveforms,
    'osc2_spectral_wave': spectral_waveforms,
    'subosc_shape': {0: 'square', 1: 'triangle' },
    'osc3_mode': {0: 'Off', 1: 'Osc2Slave', 2: 'Saw', 3: 'Pulse',
                  4: 'Sine', 5: 'Triangle'},
    'patch_category_1': categories,
    'patch_category_2': categories,
    'patch_keymode':  {0: 'poly', 1: 'mono1', 2: 'mono2', 3: 'mono3',
                       4: 'mono4', 5: 'hold'},
    'filter1_mode': {0: 'lowpass', 1:'highpass', 2:'bandpasss', 3:'bandstop'},
    'filter2_mode': {0: 'lowpass', 1:'highpass', 2:'bandpasss', 3:'bandstop'},
    'filter_saturation_curve': {0: 'Off', 1: 'Light', 2: 'Soft', 3: 'Middle',
                                4: 'Hard', 5: 'Digital', 6: 'Shaper'},
    'filter_routing': {0: 'Ser4', 1: 'Ser6', 2: 'Par4', 3: 'Split'},
    'lfo1_mode': {0: 'poly', 1: 'mono'},
    'lfo1_shape': {0: 'Sine', 1: 'Tri', 2: 'Saw', 3: 'Square', 4:'S&H',
                   5: 'S&G'},
    'lfo2_mode': {0: 'poly', 1: 'mono'},
    'lfo3_shape': {0: 'Sine', 1: 'Tri', 2: 'Saw', 3: 'Square', 4:'S&H',
                   5: 'S&G'},
    'osc_fm_mode': {0: 'Pos-Tri', 1: 'Tri', 2: 'Wave', 3: 'Noise',
                    4: 'In L' , 5: 'In L+R', 6: 'In R',
                    7: 'In R', 8: 'In R', 9: 'In R', 10: 'In R',
                    11: 'In R', 12: 'In R', 13: 'In R', 14: 'In R',
                    15: 'In R'},
    'input_mode': {0: 'Off', 1: 'Dynamic', 2:'Static'},
    'input_follower_mode': {0: 'Off', 1: 'In L', 2: 'In L+R'},
    'input_select': {0: 'In1 L', 1: 'In1 L+R', 2: 'In1 R'},
    'chorus_lfo_shape': {0: 'Sine', 1: 'Tri', 2: 'Saw', 3: 'Square',
                         4: 'S&H', 5: 'S&G'},
    'delay_lfo_shape': {0: 'Sine', 1: 'Tri', 2: 'Saw', 3: 'Square',
                         4: 'S&H', 5: 'S&G'},
    'arpeggio_mode': { 0: 'Off', 1: 'Up', 2: 'Down', 3: 'Up&Down',
                       4: 'AsPlayed', 5: 'Random', 6: 'Chord'},
    'control_bender_scale': {0: 'linear', 1: 'exponential'},
    'control_smooth_mode': {0: 'Off', 1: 'On', 2: 'Auto', 3: 'Note'},
    # Goes through 12.
    'vocoder_mode': {0: 'Off', 1: 'Osc', 2: 'OscHold', 3: 'Noise', 4: 'In L',
                     5: 'In L+R'},
    'filter_select': {0: 'Filt1', 1: 'Filt2', 2: 'Filt1+2'},
    'arpeggio_clock': arpeggio_rates,
    'lfo1_clock': lfo_rates,
    'lfo2_clock': lfo_rates,
    'delay_clock': lfo_rates,
    'lfo3_clock': lfo_rates,
    'distortion_curve': {0: 'Off', 1: 'Light', 2: 'Soft', 3: 'Middle',
                         4: 'Hard', 5: 'Digital', 6: '???',
                         9: 'Rate Reducer',
                         12: 'Wide',
                         21: 'Curry Overdrive',
                         22: 'Saffron Overdrive',},
    'lfo3_destination': {0: 'Osc 1 Pitch', 1: 'Osc 1+2 Pitch',
                         2: 'Osc 2 Pitch', 3:'Osc 1+2 Pulsewidth',
                         4: 'Osc2 Pulsewidth', 5: 'Sync Phase' },
    'lfo1_assign_dest': mod_dests,
    'lfo2_assign_dest': mod_dests,
    'mod_matrix_1_source': mod_sources,
    'mod_matrix_2_source': mod_sources,
    'mod_matrix_3_source': mod_sources,
    'mod_matrix_4_source': mod_sources,
    'mod_matrix_5_source': mod_sources,
    'mod_matrix_6_source': mod_sources,

    'mod_matrix_1_dest_1': mod_dests,
    'mod_matrix_1_dest_2': mod_dests,
    'mod_matrix_1_dest_3': mod_dests,

    'mod_matrix_2_dest_1': mod_dests,
    'mod_matrix_2_dest_2': mod_dests,
    'mod_matrix_2_dest_3': mod_dests,

    'mod_matrix_3_dest_1': mod_dests,
    'mod_matrix_3_dest_2': mod_dests,
    'mod_matrix_3_dest_3': mod_dests,

    'mod_matrix_4_dest_1': mod_dests,
    'mod_matrix_4_dest_2': mod_dests,
    'mod_matrix_4_dest_3': mod_dests,

    'mod_matrix_5_dest_1': mod_dests,
    'mod_matrix_5_dest_2': mod_dests,
    'mod_matrix_5_dest_3': mod_dests,

    'mod_matrix_6_dest_1': mod_dests,
    'mod_matrix_6_dest_2': mod_dests,
    'mod_matrix_6_dest_3': mod_dests,


    'soft_knob_function_1': soft_knob_functions,
    'soft_knob_function_2': soft_knob_functions,
    'soft_knob_function_3': soft_knob_functions,
    'soft_knob_name_1': soft_knob_names,
    'soft_knob_name_2': soft_knob_names,
    'soft_knob_name_3': soft_knob_names,
    'unison_mode': {0: 'Off', 1: 'Twin', 2: '3', 3: '4', 4: '5',
                    5: '6', 6: '7', 7: '8'},
    'phaser_mode': {0: 'Off', 1: '1 Stage', 2: '2 Stages', 3: '3 Stages',
                    4: '4 Stages', 5: '5 Stages', 6: '6 Stages'},
    'delay_mode': {0: 'Off',
                   1: 'Simple Delay',
                   2: 'Ping Pong 2:1',
                   3: 'Ping Pong 4:3',
                   4: 'Ping Pong 4:1',
                   5: 'Ping Pong 8:7',
                   6: 'Pattern 1+1',
                   7: 'Pattern 2+1',
                   8: 'Pattern 3+1',
                   9: 'Pattern 4+1',
                   10: 'Pattern 5+1',
                   11: 'Pattern 2+3',
                   12: 'Pattern 2+5',
                   13: 'Pattern 3+2',
                   14: 'Pattern 3+3',
                   15: 'Pattern 3+4',
                   16: 'Pattern 3+5',
                   17: 'Pattern 4+3',
                   18: 'Pattern 4+5',
                   19: 'Pattern 5+2',
                   20: 'Pattern 5+3',
                   21: 'Pattern 5+4',
                   22: 'Pattern 5+5',
                   },

    'reverb_room': {6: 'Hall', 19: 'Large Room'},
    'patch_delay_reverb_mode': {0: 'Off', 1: 'Delay', 2: 'Reverb',
                                3: 'Delay+Reverb'},
}

POSITIVE_TYPE=patch.POSITIVE_TYPE
NONE_TYPE=patch.NONE_TYPE
PLUS_MINUS_TYPE=patch.PLUS_MINUS_TYPE
PLUS_MINUS_PERCENT_TYPE=patch.PLUS_MINUS_PERCENT_TYPE
PERCENT_TYPE=patch.PERCENT_TYPE
SELECT_TYPE=patch.SELECT_TYPE
ON_OFF_TYPE=patch.ON_OFF_TYPE
STRING_TYPE=patch.STRING_TYPE

access_definitions = [
    # 'block', 'label', offset, bytes, type
    # TODO(bowdidge): Provide a key for values displayed in other ways such
    # as time delays.
    # TODO(bowdidge): Just subtract cc offset.
    ('patch', 'bank', -2, 1, POSITIVE_TYPE),
    ('patch', 'bank_offset', -1, 1, POSITIVE_TYPE),
    ('patch', 'portamento', 5, 1, POSITIVE_TYPE),
    ('patch', 'channel_volume', 7, 1, POSITIVE_TYPE),
    ('patch', 'pan', 10, 1, PLUS_MINUS_PERCENT_TYPE),
    # Wave to saw to pulse.
    ('osc1', 'shape', 17, 1, SELECT_TYPE),
    ('osc1', 'pulsewidth', 18, 1, POSITIVE_TYPE),
    # sine, triangle, wave.
    ('osc1', 'wave', 19, 1, SELECT_TYPE),
    ('osc1', 'spectral_wave', 19, 1, SELECT_TYPE),

    # Adjusts pitch of oscillator.
    ('osc1', 'semitones', 20, 1, PLUS_MINUS_TYPE),

    # How much pitch of oscillator 1 follows keyboard.
    # Normal tuning is 96.
    ('osc1', 'keyfollow', 21, 1, PLUS_MINUS_TYPE),

    # For Hypersaw, parameter is called density, and indicates number of
    # sawtooth waves combined.
    ('osc2', 'shape', 22, 1, SELECT_TYPE),

    # For Hypersaw, called Spread.  Detunes individual sawtooths.
    ('osc2', 'pulsewidth', 23, 1, POSITIVE_TYPE),
    ('osc2', 'wave', 24, 1, SELECT_TYPE),
    ('osc2', 'spectral_wave', 24, 1, SELECT_TYPE),
    ('osc2', 'semitones', 25, 1, PLUS_MINUS_TYPE),
    ('osc2', 'detune', 26, 1, PLUS_MINUS_TYPE),

    # Intensity of frequency modulation.
    ('osc2', 'fm_amount', 27, 1, POSITIVE_TYPE),

    # Whether oscillator  and 2 get sync'd curves.
    ('osc2', 'sync', 28, 1, ON_OFF_TYPE),

    # How much the filter envelope modulates the pitch of oscillator 2.
    # Can also be done with mod matric.
    ('osc2', 'fltenv_pitch', 29, 1, PLUS_MINUS_TYPE),

    # How much the filter envelope affects FM.
    ('osc2', 'filtenv_fm', 30, 1, PLUS_MINUS_TYPE),
    ('osc2', 'keyfollow', 31, 1, PLUS_MINUS_TYPE),
    # 32: Bank select

    # Balance between oscillator 1 and 2.
    ('osc', 'balance', 33, 1, PLUS_MINUS_PERCENT_TYPE),

    # Difference between subosc and oscillator 3?
    ('subosc', 'volume', 34, 1, POSITIVE_TYPE),
    ('subosc', 'shape', 35, 1, SELECT_TYPE),
    ('osc', 'volume', 36, 1, POSITIVE_TYPE),
    ('noise', 'volume', 37, 1, POSITIVE_TYPE),
    ('ring_modulator', 'volume', 38, 1, POSITIVE_TYPE),
    ('noise', 'color', 39, 1, POSITIVE_TYPE),
    ('filter1', 'cutoff', 40, 1, POSITIVE_TYPE),
    ('filter2', 'cutoff', 41, 1, POSITIVE_TYPE),
    ('filter1', 'resonance', 42, 1, POSITIVE_TYPE),
    ('filter2', 'resonance', 43, 1, POSITIVE_TYPE),
    ('filter1', 'env', 44, 1, POSITIVE_TYPE),
    ('filter2', 'env', 45, 1, POSITIVE_TYPE),
    ('filter1', 'keyfollow', 46, 1, PLUS_MINUS_TYPE),
    ('filter2', 'keyfollow', 47, 1, PLUS_MINUS_TYPE),
    ('filter', 'balance', 48, 1, PLUS_MINUS_TYPE),
    ('filter', 'saturation_curve', 49, 1, SELECT_TYPE),
    ('filter1', 'mode', 51, 1, SELECT_TYPE),
    ('filter2', 'mode', 52, 1, SELECT_TYPE),
    ('filter', 'routing', 53, 1, SELECT_TYPE),
    ('filter', 'attack', 54, 1, POSITIVE_TYPE),
    ('filter', 'decay', 55, 1, POSITIVE_TYPE),
    ('filter', 'sustain', 56, 1, POSITIVE_TYPE),
    # Whether sound rises or falls during sustain.
    ('filter', 'sustain_time', 57, 1, POSITIVE_TYPE),
    ('filter', 'release', 58, 1, POSITIVE_TYPE),
    ('amplifier', 'attack', 59, 1, POSITIVE_TYPE),
    ('amplifier', 'decay', 60, 1, POSITIVE_TYPE),
    ('amplifier', 'sustain', 61, 1, POSITIVE_TYPE),
    ('amplifier', 'sustain_time', 62, 1, POSITIVE_TYPE),
    ('amplifier', 'release', 63, 1, POSITIVE_TYPE),
    # 64: hold pedal
    # 65: port pedal
    # 66: sost pedal
    ('lfo1', 'rate', 67, 1, POSITIVE_TYPE),
    ('lfo1', 'shape', 68, 1, SELECT_TYPE),
    ('lfo1', 'envmode', 69, 1, ON_OFF_TYPE),
    ('lfo1', 'mode', 70, 1, SELECT_TYPE),
    ('lfo1', 'symmetry', 71, 1, POSITIVE_TYPE),
    ('lfo1', 'keyfollow', 72, 1, PLUS_MINUS_TYPE),
    ('lfo1', 'trigphase', 73, 1, POSITIVE_TYPE),
    ('lfo1', 'osc1', 74, 1, PLUS_MINUS_PERCENT_TYPE),
    ('lfo1', 'osc2', 75, 1, PLUS_MINUS_PERCENT_TYPE),
    # PW 1+2
    ('lfo1', 'pulsewidth', 76, 1, POSITIVE_TYPE),
    # LFO 1+2
    ('lfo1', 'resonance', 77, 1, POSITIVE_TYPE),
    ('lfo1', 'filter_gain', 78, 1, POSITIVE_TYPE),
    ('lfo2', 'rate', 79, 1, POSITIVE_TYPE),
    # 80?
    ('lfo2', 'envmmode', 81, 1, ON_OFF_TYPE),
    ('lfo2', 'mode', 82, 1, SELECT_TYPE),
    ('lfo2', 'symmetry', 83, 1, POSITIVE_TYPE),
    ('lfo2', 'keyfollow', 84, 1, PLUS_MINUS_TYPE),
    ('lfo2', 'trigphase', 85, 1, POSITIVE_TYPE),
    ('lfo2', 'shape', 86, 1, POSITIVE_TYPE),
    ('lfo2', 'fm_amount', 87, 1, POSITIVE_TYPE),
    ('lfo2', 'filter1', 88, 1, POSITIVE_TYPE),
    ('lfo2', 'filter2', 89, 1, POSITIVE_TYPE),
    ('lfo2', 'panorama', 90, 1, PLUS_MINUS_PERCENT_TYPE),
    ('patch', 'volume', 91, 1, POSITIVE_TYPE),
    # 92?
    ('patch', 'transpose', 93, 1, PLUS_MINUS_TYPE),
    ('patch', 'keymode', 94, 1, SELECT_TYPE),
    # 95? 96?
    ('unison', 'mode', 97, 1, SELECT_TYPE),
    ('unison', 'detune', 98, 1, PLUS_MINUS_TYPE),
    ('unison', 'panspread', 99, 1, PERCENT_TYPE),
    ('unison', 'lfophase', 100, 1, POSITIVE_TYPE),

    ('input', 'mode', 101, 1, SELECT_TYPE),
    ('input', 'select', 102, 1, SELECT_TYPE),

    ('chorus', 'mix', 105, 1, PERCENT_TYPE),
    ('chorus', 'rate', 106, 1, POSITIVE_TYPE),
    ('chorus', 'depth', 107, 1, PERCENT_TYPE),
    ('chorus', 'delay', 108, 1, POSITIVE_TYPE),
    ('chorus', 'feedback', 109, 1, PLUS_MINUS_PERCENT_TYPE),
    ('chorus', 'lfo_shape', 110, 1, SELECT_TYPE),

    # 0 = off, 1 delay, 2 reverb, 3 both.
    ('delay', 'mode', 112, 1, SELECT_TYPE),
    ('delay', 'send', 113, 1, PERCENT_TYPE ),
    # Delay if clock not specified.
    ('delay', 'time',  114, 1, POSITIVE_TYPE ),
    ('delay', 'feedback', 115, 1, PERCENT_TYPE ),
    ('delay', 'rate', 116, 1, POSITIVE_TYPE),
    ('delay', 'depth', 117, 1, PERCENT_TYPE),
    ('reverb', 'room', 117, 1, SELECT_TYPE),
    ('delay', 'lfo_shape', 118, 1, SELECT_TYPE),
    ('delay', 'color', 119, 1, PLUS_MINUS_TYPE),
    ('keyboard', 'local', 122, 1, POSITIVE_TYPE),

    ('arpeggio', 'mode', 0x81, 1, SELECT_TYPE),
    ('arpeggio', 'pattern', 0x82, 1, POSITIVE_TYPE),
    ('arpeggio', 'octave_range', 0x83, 1, POSITIVE_TYPE),
    ('arpeggio', 'hold', 0x84, 1, POSITIVE_TYPE),
    ('arpeggio', 'note_length', 0x85, 1, PLUS_MINUS_TYPE),
    ('arpeggio', 'swing', 0x86, 1, POSITIVE_TYPE),

    ('lfo3', 'rate', 0x87, 1, POSITIVE_TYPE),
    ('lfo3', 'shape', 0x88, 1, SELECT_TYPE),
    ('lfo3', 'mode', 0x89, 1, POSITIVE_TYPE),
    ('lfo3', 'keyfollow', 0x8a, 1, PLUS_MINUS_TYPE),
    ('lfo3', 'destination', 0x8b, 1, SELECT_TYPE),
    ('lfo3', 'osc_amount', 0x8c, 1, POSITIVE_TYPE),
    ('lfo3', 'fade_in_time', 0x8d, 1, POSITIVE_TYPE),

    ('patch', 'tempo', 0x90, 1, POSITIVE_TYPE),
    # 0-17 1/64 - 1/1
    ('arpeggio', 'clock', 0x91, 1, SELECT_TYPE),
    # 0-19 1/64 - 4/1
    ('lfo1', 'clock', 0x92, 1, SELECT_TYPE),
    # 0-19 1/64 - 4/1
    ('lfo2', 'clock', 0x93, 1, SELECT_TYPE),
    # 0-16 1/64 -3/1
    ('delay', 'clock', 0x94, 1, SELECT_TYPE),
    # 0-19 1/64 - 4/1
    ('lfo3', 'clock', 0x95, 1, SELECT_TYPE),

    ('control', 'smooth_mode', 0x99, 1, SELECT_TYPE),
    ('control', 'bender_range_up', 0x9a, 1, PLUS_MINUS_TYPE),
    ('control', 'bender_range_down', 0x9b, 1, PLUS_MINUS_TYPE),
    ('control', 'bender_scale', 0x9c, 1, SELECT_TYPE),

    # 0=negative, 1=positive
    ('filter1', 'env_polarity', 0x9e, 1, POSITIVE_TYPE),
    ('filter2', 'env_polarity', 0x9f, 1, POSITIVE_TYPE),
    # 0 off 1 on
    ('filter', 'cutoff_link', 0xa0, 1, POSITIVE_TYPE),
    # c-1 - G9.
    ('filter', 'keytrack_base', 0xa1, 1, POSITIVE_TYPE),

    # Type of FM.  Varies between Classic and Wavetable mode.
    # 0: pos-tri, 1:tri, 2:wave, 3: noise, 4:in l, 5 in L+R
    ('osc', 'fm_mode', 0xa2, 1, SELECT_TYPE),
    # 0 off, 1..127
    ('osc', 'init_phase', 0xa3, 1, POSITIVE_TYPE),
    ('punch', 'intensity', 0xa4, 1, POSITIVE_TYPE),


    ('input', 'follower_mode', 0xa6, 1, SELECT_TYPE),
    ('vocoder', 'mode', 0xa7, 1, SELECT_TYPE),

    # Oscillator 3 is a separate oscillator, and differs from the
    # suboscillator in the other oscillators.
    # 0: off, 1: Osc2 slave, 2: saw, 3, pulse, 4: sine, 5: triangle
    ('osc3', 'mode', 0xa9, 1, SELECT_TYPE),
    ('osc3', 'volume', 0xaa, 1, POSITIVE_TYPE),
    ('osc3', 'semitone', 0xab, 1, PLUS_MINUS_TYPE),
    ('osc3', 'detune', 0xac, 1, POSITIVE_TYPE),
    ('equalizer', 'low_freq', 0xad, 1, POSITIVE_TYPE),
    # Cutoff frequency for high frequencies. 1830 Hz to 24KHz.
    ('equalizer', 'high_freq', 0xae, 1, POSITIVE_TYPE),
    ('osc1', 'shape_velocity', 0xaf, 1, PLUS_MINUS_TYPE),
    ('osc2', 'shape_velocity', 0xb0, 1, PLUS_MINUS_TYPE),
    ('osc', 'pulsewidth_velocity', 0xb1, 1, PLUS_MINUS_TYPE),
    ('fm', 'amount_velocity', 0xb2, 1, PLUS_MINUS_TYPE),
    ('soft_knob', 'name_1', 0xb3, 1, SELECT_TYPE),
    ('soft_knob', 'name_2', 0xb4, 1, SELECT_TYPE),
    # Not sure
    ('soft_knob', 'name_3', 0xb5, 1, SELECT_TYPE),

    ('filter1', 'envamt_velocity', 0xb6, 1,PLUS_MINUS_TYPE),
    ('filter2', 'envamt_velocity', 0xb7, 1, PLUS_MINUS_TYPE),
    ('filter1', 'resonance_velocity', 0xb8, 1, PLUS_MINUS_TYPE),
    ('filter2', 'resonance_velocity', 0xb9, 1, PLUS_MINUS_TYPE),
    ('output', '2_balance', 0xba, 1, POSITIVE_TYPE),
    ('amplifier', 'velocity', 0xbc, 1, PLUS_MINUS_TYPE),
    ('panorama', 'velocity', 0xbd, 1, PLUS_MINUS_TYPE),

    ('soft_knob', 'function_1', 0xbe, 1, SELECT_TYPE),
    ('soft_knob', 'function_2', 0xbf, 1, SELECT_TYPE),

    ('mod_matrix_1', 'source', 0xc0, 1, SELECT_TYPE),
    ('mod_matrix_1', 'dest_1', 0xc1, 1, SELECT_TYPE),
    ('mod_matrix_1', 'amount_1', 0xc2, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_2', 'source', 0xc3, 1, SELECT_TYPE),
    ('mod_matrix_2', 'dest_1', 0xc4, 1, SELECT_TYPE),
    ('mod_matrix_2', 'amount_1', 0xc5, 1, PLUS_MINUS_TYPE),
    ('mod_matrix_2', 'dest_2', 0xc6, 1, SELECT_TYPE),
    ('mod_matrix_2', 'amount_2', 0xc7, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_3', 'source', 0xc8, 1, SELECT_TYPE),
    ('mod_matrix_3', 'dest_1', 0xc9, 1, SELECT_TYPE),
    ('mod_matrix_3', 'amount_1', 0xca, 1, PLUS_MINUS_TYPE),
    ('mod_matrix_3', 'dest_2', 0xcb, 1, SELECT_TYPE),
    ('mod_matrix_3', 'amount_2', 0xcc, 1, PLUS_MINUS_TYPE),
    ('mod_matrix_3', 'dest_3', 0xcd, 1, SELECT_TYPE),
    ('mod_matrix_3', 'amount_3', 0xce, 1, PLUS_MINUS_TYPE),

    ('lfo1', 'assign_dest', 0xcf, 1, SELECT_TYPE),
    ('lfo1', 'assign_amount', 0xd0, 1, PLUS_MINUS_TYPE),
    ('lfo2', 'assign_dest', 0xd1, 1, SELECT_TYPE),
    ('lfo2', 'assign_amount', 0xd2, 1, PLUS_MINUS_TYPE),

    ('phaser', 'mode', 0xd4, 1, SELECT_TYPE),
    ('phaser', 'mix', 0xd5, 1, POSITIVE_TYPE),
    ('phaser', 'rate', 0xd6, 1, POSITIVE_TYPE),
    ('phaser', 'depth', 0xd7, 1, POSITIVE_TYPE),
    ('phaser', 'frequency', 0xd8, 1, POSITIVE_TYPE),
    ('phaser', 'feedback', 0xd9, 1, PLUS_MINUS_TYPE),
    ('phaser', 'spread', 0xda, 1, POSITIVE_TYPE),
    ('equalizer', 'mid_gain', 0xdc, 1, PLUS_MINUS_TYPE),
    ('equalizer', 'mid_frequency', 0xdd, 1, POSITIVE_TYPE),
    ('equalizer', 'mid_q', 0xde, 1, POSITIVE_TYPE),
    ('equalizer', 'low_gain', 0xdf, 1, POSITIVE_TYPE),
    # How much to boost or lower high frequencies.  -16db to 16db.
    ('equalizer', 'high_gain', 0xe0, 1, POSITIVE_TYPE),
    ('equalizer', 'bass_intensite', 0xe1, 1, POSITIVE_TYPE),
    ('equalizer', 'bass_tune', 0xe2, 1, POSITIVE_TYPE),
    ('ring_modulator', 'input', 0xe3, 1, POSITIVE_TYPE),
    ('distortion', 'curve', 0xe4, 1, SELECT_TYPE),
    ('distortion', 'intensity', 0xe5, 1, PERCENT_TYPE),


    ('mod_matrix_4', 'source', 0xe7, 1, SELECT_TYPE),
    ('mod_matrix_4', 'dest_1', 0xe8, 1, SELECT_TYPE),
    ('mod_matrix_4', 'amount_1', 0xe9, 1, PLUS_MINUS_TYPE),

    # Not sure
    ('mod_matrix_4', 'dest_2', 0x161, 1, SELECT_TYPE),
    ('mod_matrix_4', 'amount_2', 0x162, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_4', 'dest_3', 0x163, 1, SELECT_TYPE),
    ('mod_matrix_4', 'amount_3', 0x164, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_5', 'source', 0xea, 1, SELECT_TYPE),
    ('mod_matrix_5', 'dest_1', 0xeb, 1, SELECT_TYPE),
    ('mod_matrix_5', 'amount_1', 0xec, 1, PLUS_MINUS_TYPE),

    # Not sure
    ('mod_matrix_6', 'source', 0xed, 1, SELECT_TYPE),
    ('mod_matrix_6', 'dest_1', 0xee, 1, SELECT_TYPE),
    ('mod_matrix_6', 'amount_1', 0xef, 1, PLUS_MINUS_TYPE),

    ('patch', 'name', 0xf0, 10, STRING_TYPE),

    ('filter', 'select', 0xfa, 1, SELECT_TYPE),
    ('patch', 'category_1', 0xfb, 1, SELECT_TYPE),
    ('patch', 'category_2', 0xfc, 1, SELECT_TYPE),

    ('reverb', 'time', 0x105, 1, POSITIVE_TYPE),
    ('reverb', 'coloration', 0x107, 1, PLUS_MINUS_TYPE),
    ('soft_knob', 'function_3', 0x11d, 1, SELECT_TYPE),

    # Basic type of oscillator.  Classic, Hypersaw, Wavetable, etc.
    ('osc1', 'mode', 0x11f, 1, SELECT_TYPE),
    ('osc2', 'mode', 0x124, 1, SELECT_TYPE),

    ('osc1', 'interpolation', 0x12d, 1, POSITIVE_TYPE),
    ('osc2', 'interpolation', 0x141, 1, POSITIVE_TYPE),

    ('mod_matrix_1', 'dest_2', 0x15b, 1, SELECT_TYPE),
    ('mod_matrix_1', 'amount_2', 0x15c, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_1', 'dest_3', 0x15d, 1, SELECT_TYPE),
    ('mod_matrix_1', 'amount_3', 0x15e, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_2', 'dest_3', 0x15f, 1, SELECT_TYPE),
    ('mod_matrix_2', 'amount_3', 0x160, 1, PLUS_MINUS_TYPE),

    ('env3', 'attack', 0x151, 1, POSITIVE_TYPE),
    ('env3', 'decay', 0x152, 1, POSITIVE_TYPE),
    ('env3', 'sustain', 0x153, 1, POSITIVE_TYPE),
    ('env3', 'sustain_slope', 0x154, 1, PLUS_MINUS_TYPE),
    ('env3', 'release', 0x155, 1, POSITIVE_TYPE),

    ('env4', 'attack', 0x156, 1, POSITIVE_TYPE),
    ('env4', 'decay', 0x157, 1, POSITIVE_TYPE),
    ('env4', 'sustain', 0x158, 1, POSITIVE_TYPE),
    ('env4', 'sustain_slope', 0x159, 1, PLUS_MINUS_TYPE),
    ('env4', 'release', 0x160, 1, POSITIVE_TYPE),

    ('mod_matrix_5', 'dest_2', 0x165, 1, SELECT_TYPE),
    ('mod_matrix_5', 'amount_2', 0x166, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_5', 'dest_3', 0x167, 1, SELECT_TYPE),
    ('mod_matrix_5', 'amount_3', 0x168, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_6', 'dest_2', 0x169, 1, SELECT_TYPE),
    ('mod_matrix_6', 'amount_2', 0x16a, 1, PLUS_MINUS_TYPE),

    ('mod_matrix_6', 'dest_3', 0x16b, 1, SELECT_TYPE),
    ('mod_matrix_6', 'amount_3', 0x16c, 1, PLUS_MINUS_TYPE),

    # Interpolation?
    ]

def euclidean_distance(a, b):
   """
   Returns the euclidean distance for n>=2 dimensions
   :param a: tuple with integers
   :param b: tuple with integers
   :return: the euclidean distance as an integer
   """
   dimension = len(a) # notice, this will definitely throw a IndexError if len(a) != len(b)

   return math.sqrt(reduce(lambda i,j: i + ((a[j] - b[j]) ** 2), range(dimension), 0))

class AccessPatch(patch.Patch):
    def __init__(self, filepath):
        # cc_offset counts 3 bytes for manufacturer, 4 for device, bank,
        # and patch, and two for who knows.
        super(AccessPatch, self).__init__(filepath, cc_offset=9)
        # First three bytes after F0 are manufacturer.
        # Next two are product (0x01 is virus) and device ID (0-f -channel,
        # 10: omini)
        self.manufacturer_string = '[0, 0x20, 0x33]'
        self.device = 'virus'
        self.settings['device'] = self.device
        self.settings['filename'] = os.path.basename(filepath)
        self.settings['source'] = os.path.basename(filepath)
        self.definitions = access_definitions
        self.select_styles = access_select_styles

    def compare(self, other):
        # Tuples of (label, self value, other value)
        scores = []
        for (block, label, _, _, type) in self.definitions:
            key = '%s_%s' % (block, label)
            if key in self.settings and key in other.settings:
                if type == STRING_TYPE:
                    continue
                if type == SELECT_TYPE:
                    if self.settings[key] == other.settings[key]:
                        scores.append((key, 0, 0))
                    else:
                        scores.append((key, 0, 64))
                else:
                    scores.append((key, self.settings[key],
                                   other.settings[key]))
        us = [x[1] for x in scores]
        other = [x[2] for x in scores]
        return euclidean_distance(us, other)

    def compare_categories(self, other):
        """Returns categorization of blocks that are similar and different
        between patch.

        Result is a dictionary of block names, and score for each showing
        euclidean distance.
        """
        # Tuples of (label, self value, other value)
        scores = []
        for (block, label, _, _, type) in self.definitions:
            key = '%s_%s' % (block, label)
            if key in self.settings and key in other.settings:
                if type == STRING_TYPE:
                    continue
                if type == SELECT_TYPE:
                    if self.settings[key] == other.settings[key]:
                        scores.append((key, 0, 0))
                    else:
                        scores.append((key, 0, 64))
                else:
                    scores.append((key, self.settings[key],
                                   other.settings[key]))

        categories = {}
        for (label, us, other) in scores:
            category = label.split('_')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append((us, other))

        result = {}
        for category in categories:
            us = [x[0] for x in categories[category]]
            other = [x[1] for x in categories[category]]
            result[category] = euclidean_distance(us, other)
        return result

    def old_compare(self, patch):
        """Returns a score comparing two patches."""

        us_scores = []
        other_scores = []
        for key in ['amplifier_attack', 'amplifier_decay',
                     'amplifier_sustain', 'amplifier_sustain_time',
                     'amplifier_decay']:
            us_scores.append(self.settings.get(key))
            other_scores.append(patch.settings.get(key))

        for key in ['phaser_mix', 'chorus_mix', 'subosc_volume']:
            us_scores.append(self.settings.get(key) / 2)
            other_scores.append(patch.settings.get(key) / 2)

        # For categories, give lower scores for matches.
        for key in ['osc1_shape', 'osc2_shape', 'keymode',
                    'patch_transpose']:
            if self.settings.get(key) == patch.settings.get(key):
                us_scores.append(0)
                other_scores.append(0)
            else:
                us_scores.append(0)
                other_scores.append(64)

        # Chorded vs non-chorded.
        us_semitones = (self.settings.get('osc1_semitones') +
                        self.settings.get('osc2_semitones'))
        them_semitones = (patch.settings.get('osc1_semitones') +
                          patch.settings.get('osc2_semitones'))
        if (us_semitones % 12 != them_semitones % 12):
            us_scores.append(0)
            other_scores.append(64)
        else:
            us_scores.append(0)
            other_scores.append(0)


        for key in ['arpeggio_mode']:
            if self.settings.get(key) == patch.settings.get(key):
                us_scores.append(0)
                other_scores.append(0)
            else:
                us_scores.append(0)
                other_scores.append(128)

        return euclidean_distance(us_scores, other_scores)

    def asDict(self):
        result = super(AccessPatch, self).asDict()
        result['amplifier_graph'] = self.adsr_graph(
            result['amplifier_attack'],
            result['amplifier_decay'],
            result['amplifier_sustain'],
            result['amplifier_sustain_time'],
            result['amplifier_decay'])
        result['filter_graph'] = self.adsr_graph(
            result['filter_attack'],
            result['filter_decay'],
            result['filter_sustain'],
            result['filter_sustain_time'],
            result['filter_decay'])
        result['env3_graph'] = self.adsr_graph(
            result['env3_attack'],
            result['env3_decay'],
            result['env3_sustain'],
            result['env3_sustain_slope'],
            result['env3_decay'])
        result['env4_graph'] = self.adsr_graph(
            result['env4_attack'],
            result['env4_decay'],
            result['env4_sustain'],
            result['env4_sustain_slope'],
            result['env4_decay'])


        return result

def read_patches(filepath):
    """Read multiple Virus TI patches from file."""
    patches = []

    if filepath.endswith('syx'):
        # Single patch.
        messages = mido.read_syx_file(filepath)
        for message in messages:
            bytes = message.bin()
            if len(bytes) != 524:
                # Not patch.
                continue
            patch_name = str(bytes[0xf9:0x103])
            patch_name = patch_name.strip()
            p = AccessPatch(filepath)
            p.name = patch_name
            p.collection = os.path.basename(filepath)
            p.parse(message.bin())
            patches.append(p)
    elif filepath.endswith('mid'):
        patch_file = mido.MidiFile(filepath)
        for i, track in enumerate(patch_file.tracks):
            for msg in track:
                bytes = msg.bin()
                if len(bytes) == 524:
                    track_number = msg.bin()[8]

                    patch_name = str(bytes[0xf9:0x103])
                    patch_name = patch_name.strip()
                    p = AccessPatch(filepath)
                    p.name = patch_name
                    p.collection = os.path.basename(filepath)
                    p.parse(msg.bin())
                    patches.append(p)

    return patches

def main():
        patches = read_patches('/Users/bowdidge/Documents/Access Music/Virus TI/Patches/Classic Live Patches For Virus TI.mid')

if __name__ == '__main__':
    main()
