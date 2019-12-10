Patch Compare

This software gives you ways to view, understand, compare, and group
different patches.  I'd written it when trying to understand how factory
patches for different synthesizers created sounds I like.

Rather that providing a control panel or forcing menu diving, this software
displays all details of patches in a single screen.  Patch parameters are
highlighted and grouped to make understanding easier.  Patches should also
be summarized you can quickly see how a patch might be used "modulation wheel
affects filter, aftertouch affects sustain level."

The software parses all patches in a set of directories provided at launch
time.  Because it knows about multiple patches, Patch Compare also identifies
similar patches, and should allow comparing patches to see the differences.

Currently supports Yamaha Reface DX and Access Virus TI.

Usage:
patch_compare.py [directory with patches] [directory with patches]

User interface appears as web page at localhost:8080.

Robert Bowdidge
rwbowdidge@gmail.com

