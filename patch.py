#!/usr/bin/env python2.7
#
# Base class for patches.
#
# Patches for a specific synthesizer should inherit from this class and
# define their own definitions for the CCs setting patch parameters.
#
# Robert Bowdidge, December 2019.


# Classification of different CC variables.  Used to control presentation.

# Uninteresting part of patch.  Unprocessed.
NONE_TYPE=0

# CC represents a positive value from 0 - 127.
POSITIVE_TYPE=1

# CC represents a value from -64 to 63.
PLUS_MINUS_TYPE=2

# One of a set of choices.  String names for values are in Patch.select_types
# dictionary.
SELECT_TYPE=3

# Value that's either on (non-zero) or off (127).
# TODO(bowdidge): Extend to 0-1 and other alternative values.
ON_OFF_TYPE=4

# Multi byte string.
STRING_TYPE=5

# CC represents a value from -100% to 100%.
PLUS_MINUS_PERCENT_TYPE=6

# CC represents a value from 0% to 100%.
PERCENT_TYPE=6

class Patch(object):
    """Base class for all synthesizer-specific patches.

    Callers should override __init__ at a minimum.
    """

    def __init__(self, filepath, cc_offset=0, collection=''):
        # Full path to location of file containing patch.
        self.filepath = filepath

        # True if favorite of user.
        self.is_favorite = False

        # Dictionary containing map of cc names to 0-127 values.
        self.settings = {}

        # Array of valid cc names and locations in file.
        # Each item is a tuple of:
        # ('block', 'label', offset, bytes, type)
        # where 
        # block is the name of subsystem in the synthesizer
        # label is a name for the particular value.  block_label must be
        # unique for this synthesizer, but label and block individually can
        # appear in multiple ccs.
        # offset is the offset in patch Sysex message, 
        # bytes is the number of cc values (usually 1 except for strings)
        # type describes how the number should be formatted, represented
        # by a constant.
        # 
        # Each unique value is converted to a name of block_label.
        self.definitions = None

        # Dictionary mapping block_label to dictionary for a given select
        # type.  Dictionary maps integer values to string to display.
        self.select_styles = None

        # Name of file (or directory) where patch appeared.
        self.collection = ''

        # Name of patch.
        self.name = 'unknown'

        # Raw MIDI command for patch.
        self.sysex = None

        # Offset between indexes in file and CCs.
        # TODO(bowdidge): Remove.
        self.cc_offset = cc_offset

    def asDict(self, definitions=None, group_key=None):
        """Converts patch details to form that web template can handle.

        Returned dictionary contains map of all block_label names to the
        human-readable values they hold.  block_label_numeric contains the
        raw value for SELECT_TYPE parameters.
        
        Also includes other details on patch.
        """
        out = {}
        if not definitions:
            definitions = self.definitions

        out['is_favorite'] = self.is_favorite
        out['collection'] = self.collection
        out['device'] = self.settings['device']
        out['source'] = self.settings['source']
        out['hex_dump'] = dump_hex(self.sysex)
        out['manufacturer_string'] = self.manufacturer_string
        out['sysex'] = ''.join([ '%%%02x' % c for c in self.sysex])

        the_dict = self.settings
        if group_key:
            the_dict = self.settings[group_key]

        for block, label, _, _, type in definitions:
            key = '%s_%s' % (block, label)
            if key not in the_dict:
                continue
            if type == SELECT_TYPE:
                out[key] = self.select_label(key, the_dict[key])
                out[key + '_numeric'] = the_dict[key]
            elif type == ON_OFF_TYPE:
                if the_dict[key] == 0:
                    out[key] = 'off'
                else:
                    out[key] = 'on'
            else:
                out[key] = the_dict[key]
        return out

    def adsr_graph(self, attack, decay, sustain, sustain_time, release):
        """Draw SVG markup for an ADSR (attack-decay-sustain-release) graph.

        SVG (scalable vector graphics) can be drawn in most web browsers,
        and lets us draw a nice picture for showing change in sound over time.

        Values are expected to be between 0 and 127.

        Sustain time indicates the slope of the sustain.  A value less than
        64 causes sustain to decrease as key is held, a value greater than 64
        causes sustain to increase as key is held.

        Graphic is always assumed to be 300 wide x 200 high.
        """
        # Scale everything in a 300x200 section; assume each
        # point can fill the 200 pixel Y axis, but that we break
        # up the various sections to take nominally 75 (1/4) of X.
        points = [(0, 200)]
        # Attack: ramp up to full at some rate.
        points.append(
            (attack * 75 / 127, 0))
        # Decay: time to drop to sustain level.
        points.append((points[1][0] + decay * 75 / 127,
                       (127 - sustain) * 200 / 127))
        # Slope of sustain.
        points.append((
                points[2][0] + sustain_time * 75 / 127,
                (points[2][1] * 200 / 127)))
        # How fast release gets back to zero.
        points.append((
                points[3][0] + release * 75 / 127,
                (127 * 200 / 127)))
        points.append((300, 200))
        points.append((0, 200))
        points_arr = ["%d, %d" % (x[0], x[1]) for x in points]

        return ('<svg width="300" height="200">'
                '<rect width="300" height="200" '
                '  style="fill:rgb(192,192,192);stroke-width:1;'
                '         stroke:rgb(0,0,0)" />'
                '<polyline fill="#006060" stroke="#0074d9" stroke_width="3" '
                '          points="%s" \/>'
                '</svg>' % '\n'.join(points_arr)
                )

    def eg_graph(self, eg_rate_1, eg_level_1, eg_rate_2, eg_level_2,
                 eg_rate_3, eg_level_3, eg_rate_4, eg_level_4):
        """Draw an envelope generator graph describing sound change over time.

        Based on Reface DX's specification of change in sound.

        Values expected to be between 0 and 127.

        Graphic is always assumed to be 300 wide x 200 high.
        """
        points = [(0, 200)]
        points.append(
            ((127 - eg_rate_1) * 75 / 127, 
             (127 - eg_level_1) * 200 / 127))
        points.append((
                points[1][0] + (127 - eg_rate_2) * 75 / 127,
                (127 - eg_level_2) * 200 / 127
                ))
        points.append((
                points[2][0] + (127 - eg_rate_3) * 75 / 127,
                (127 - eg_level_3) * 200 / 127
                ))
        points.append((
                points[3][0] + (127 - eg_rate_4) * 75 / 127,
                (127 - eg_level_4) * 200 / 127
                ))
        points.append((300, 200))
        points.append((0, 200))
        points_arr = ["%d, %d" % (x[0], x[1]) for x in points]

        return ('<svg width="300" height="200">'
                '<rect width="300" height="200" '
                '      style="fill:rgb(192,192,192);stroke-width:1;'
                '             stroke:rgb(0,0,0)" />'
                '<polyline fill="#006060" stroke="#0074d9" stroke_width="3" '
                '          points="%s" \/>'
                '</svg>' % '\n'.join(points_arr)
                )

    def select_label(self, label, value):
        """Returns human-readable label for a SELECT_TYPE CC parameter.

        Returns string holding integer if label is unknown, or key isn't
        present.
        """
        if label not in self.select_styles:
            print 'no style for %s' % label
            return str(value)

        label_dict = self.select_styles[label]
        if value not in label_dict:
            print '%s: No label in %s for %d' % (self.name, label, value)
            return str(value)

        return '%s (%d)' % (label_dict[value], value)

    def parse(self, sysex, definitions=None, group_key=None):
        """Parse a Sysex message containing an arbitrary patch.

        Uses derived class's definitions to map bytes to names of
        CC parameters.
        """
        if not definitions:
            definitions = self.definitions
        self.sysex = sysex
        start_offset = self.cc_offset
        the_dict = self.settings
        if group_key:
            if group_key not in self.settings:
                self.settings[group_key] = {}
            the_dict = self.settings[group_key]

        for rule in definitions:
            # print rule
            try:
                block, label, offset, bytes, type = rule
            except Exception as e:
                print 'problems parsing %s:%s' % (rule, e)
                continue
            full_label = '%s_%s' % (block, label)
            if type is STRING_TYPE:
                the_dict[full_label] = str(self.sysex[start_offset + offset:start_offset + offset + bytes]).strip()
            elif type is NONE_TYPE:
                pass
            elif type is POSITIVE_TYPE:
                # assume length is 1.
                the_dict[full_label] = self.sysex[start_offset + offset]
            elif type is PLUS_MINUS_TYPE:
                the_dict[full_label] = self.sysex[start_offset + offset] - 64
            elif type is PLUS_MINUS_PERCENT_TYPE:
                the_dict[full_label] = 100 * (self.sysex[start_offset + offset] - 64) / 64
            elif type is PERCENT_TYPE:
                the_dict[full_label] = (100 * self.sysex[start_offset + offset]  / 124)
            else:
                the_dict[full_label] = self.sysex[start_offset + offset]
        return the_dict

    def print_patch(self):
        """Print the patch in a human-readable text format."""
        for rule in self.definitions:
            try:
                block, label, offset, bytes, type = rule
            except Exception as e:
                print 'problems parsing %s:%s' % (rule, e)
                continue
            full_label = '%s_%s' % (block, label)

            value = self.settings[full_label]

            if type is STRING_TYPE:
                print '%s: %s' % (full_label, value)
            elif type is NONE_TYPE:
                pass
            elif type is SELECT_TYPE:
                print '%s: %s' % (full_label, self.select_label(label, value))
            elif type is ON_OFF_TYPE:
                str_value = 'off'
                if value != 0:
                    str_value = 'on'
                print '%s: %s' % (full_label, str_value)
            elif type is PLUS_MINUS_TYPE:
                print '%s: %d' % (full_label, value - 64)
            elif type is PLUS_MINUS_PERCENT_TYPE:
                print '%s: %d' % (full_label, 100 * (value - 64) / 64)
            elif type is PERCENT_TYPE:
                print '%s: %d%' % (full_label, 100 * value / 127)
            else:
                print '%s: %d' % (full_label, value)
        
        print self.settings

def dump_hex(bytes):
    """Returns ASCII version of raw bytes in Sysex message."""
    out = ''
    index = 0
    while index < len(bytes):
        # Show address
        out += '%04x ' % index
        row = bytes[index:index+16]
        while len(row) < 16:
            row.append(0)

        for row_offset in range(0, 16):
            i = row[row_offset]
            out += '%02x'% i
            if row_offset % 2 == 1:
                out += ' '
        out += '  '
        for i in range(0, 15):
            if row[i] < 32 or row[i] > 127:
                row[i] = '.'
        out += row + '\n'
        index += 16
    return out
