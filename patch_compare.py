#!/usr/local/bin/python2.7
#
# Patch Compare: web server for displaying, comparing, and grouping
# patches from different synthesizers.
#
# Usage: patch_compare.py [directory] [directory]
#
# Runs as web server at localhost:8080.
#
# Robert Bowdidge, December 2019.

import BaseHTTPServer
import glob
import jinja2 as jinja
import mido
import os
import sys
import urllib
import urlparse

import access_patch
import refacedx_patch

# Map from short name to full name.
all_patches = {}

def try_filter(patch_list, query_key, query_value):
    """Returns a filtered version of patch list.

    query_key indicates a CC parameter name to compare.

    query_value contains the value to filter on.  value can be a single
    number (15) or can indicate relation (ge15, le15).
    """
    if 'ge' not in query_value and 'le' not in query_value:
        # Straight equality.
        query_key_numeric = '%s_numeric' % query_key
        result = []
        for x in patch_list:
            a = str(x.get(query_key))
            b = str(x.get(query_key_numeric))
            
            if a == query_value or b == query_value:
                print query_value, x.get(query_key), x.get(query_key_numeric)
                result.append(x)
        return result
    greater_equal = 'ge' in query_value
    try:
        base_value = int(query_value.replace('ge', '').replace('le', ''))
    except Exception as e:
        print 'Bad query %s' % query_value
        return patch_list
    new_list = []
    for x in patch_list:
        if query_key not in x:
            new_list.append(x)
        else:
            value = x.get(query_key)
            if ((greater_equal and value >= base_value) or
                (not greater_equal and value <= base_value)):
                new_list.append(x)
    return new_list
    

class PatchCompareHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """Base HTTP handler for PatchCompare."""

    def render_template(self, filename, variables):
        """Renders a Jinja template.

        filename is name of file containing template.
        variables is dictionary of variables available to template.
        """
        file_loader = jinja.FileSystemLoader('templates')
        env = jinja.Environment(loader=file_loader)
        template = env.get_template(filename)

        return template.render(variables)

    def do_GET(self):
        path = urlparse.urlparse(self.path).path
        print path
        if path.startswith('/patch'):
            return self.get_patch()
        elif path == '/':
            return self.get_root()
        else:
            return self.get_404()

    def get_404(self):
        """Return a "not found" error."""
        self.send_response(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('<html><head><title>Unknown page</title>')

    def get_root(self):
        """Renders and returns the main root page listing patches."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('<html><head><title>Title</title>')

        query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        collections = query.get('collection', [])
        devices = query.get('device', [])
        
        patch_list = [x.asDict() for x in all_patches.values()]

        if collections:
            patch_list = [x for x in patch_list
                          if x.get('collection') in collections]
        if devices:
            patch_list = [x for x in patch_list
                          if x.get('device') in devices]

        for key in query:
            values = query[key]
            if key not in ['collection', 'device']:
                for value in values:
                    patch_list = try_filter(patch_list, key, value)

        patch_list = sorted(patch_list, key=lambda x: x.get('patch_name'))
        variables = {'patches': patch_list,
                     'collections': collections}
        content = self.render_template('root.html', variables)
        self.wfile.write(content)

        
    def get_patch(self):
        """Renders page describing patch."""
        patch_name = self.path.replace('/patch/', '')
        patch_name = urllib.unquote(patch_name)
        print patch_name
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write('<html><head><title>Patch</title>')

        patch = all_patches.get(patch_name)

        similar_patches = []
        similar_count = 10
        for other_name in all_patches:
            if other_name == patch_name:
                continue
            other = all_patches.get(other_name)
            if other.device != patch.device:
                continue
            if len(similar_patches) < similar_count:
                similar_patches.append((other, patch.compare(other)))
            smaller = False
            compare_score = patch.compare(other)
            for (s, s_score) in similar_patches:
                if compare_score < s_score:
                    smaller = True
            if smaller:
                similar_patches.append((other, compare_score))
                similar_patches_and_scores = sorted(similar_patches,
                                         key=lambda x: x[1])[0:similar_count]

        similar_patches = [x for x,y in similar_patches_and_scores]
        for similar_patch in similar_patches:
            print patch.compare_categories(similar_patch)

        patch_dict = patch.asDict()
        variables = {'patch_name': patch_dict.get('patch_name'),
                     'patch': patch_dict,
                     'similar_patches': similar_patches_and_scores}
        template = 'patch.html'
        if patch.settings['device'] == 'virus':
            template = 'access_virus.html'
        else:
            template = 'reface_dx.html'
        content = self.render_template(template, variables)
        self.wfile.write(content)

UNKNOWN = 0
REFACE_DX = 1
VIRUS_TI = 2        

def decode_patch(filepath, manufacturer):
    if manufacturer == REFACE_DX:
        return refacedx_patch.read_patches(filepath)
    elif manufacturer == VIRUS_TI:
        return access_patch.read_patches(filepath)

def decode_patches(filepath):
    """Returns patches found."""
    if filepath.endswith('syx'):
        messages = mido.read_syx_file(filepath)
        if (messages) == 0:
            return []

        manufacturer = read_manufacturer_from_bytes(messages[0].bin())
        return decode_patch(filepath, manufacturer)

    elif filepath.endswith('mid'):
        patch_file = mido.MidiFile(filepath)
        for i, track in enumerate(patch_file.tracks):
            for msg in track:
                bytes = msg.bin()
                bytes = msg.bin()
                if len(bytes) == 524:
                    manufacturer = read_manufacturer_from_bytes(bytes)
                    return decode_patch(filepath, manufacturer)
    return []

def read_manufacturer_from_bytes(bytes):
    if (bytes[0] == 0xf0 and
        bytes[1] == 0x43 and
        bytes[2] == 0 and
        bytes[3] == 0x7f and
        bytes[4] == 0x1c):
        return REFACE_DX
    if (bytes[0] == 0xf0 and
        bytes[1] == 0x0 and
        bytes[2] == 0x20 and
        bytes[3] == 0x33):
        return VIRUS_TI
    return UNKNOWN
            

def run(server_class=BaseHTTPServer.HTTPServer,
        handler_class=PatchCompareHandler):
    global all_patches

    if len(sys.argv) == 1:
        patch_dirs = [
            # Mostly Reface.
            '/Users/bowdidge/Desktop/Circuit',
            
            # Access.
            '/Users/bowdidge/Documents/Access Music/Virus TI/Patches'
            '/Library/Application Support/Access Music/Virus TI/Patches/Virus TI Factory Backup/Rom',
            '/Library/Application Support/Access Music/Virus TI/Patches',
            ]
    else:
        patch_dirs = sys.argv[1:]

    files = []

    for match in ['*.syx', '*/*.syx', '*.mid', '*/*.mid']:
        for patch_dir in patch_dirs:
            pattern = '%s/%s' % (patch_dir, match)
            files.extend(glob.glob(pattern))

    if not files:
        print 'No patches found in %s' % patch_dirs
        sys.exit(1)

    for file_path in files:
        print 'Looking at %s' % file_path
        filename = os.path.basename(file_path)
        patches = decode_patches(file_path)

        if not patches:
            print 'No patches in file %s' % file_path
            continue

        for patch in patches:
            if patch.name in favorites:
                patch.is_favorite = True
                print '%s is favorite' % patch.name
            all_patches[patch.name] = patch

    server_address = ('', 8080)
    httpd = server_class(server_address, handler_class)
    print 'Serving at %s' % str(server_address)
    httpd.serve_forever()

favorites = ['ColoColoTU', 'Nylon   BC', 'Banco TU', 'AandreasM@',
             'BeautiflJL', 'PiterFM AV', 'Floooot HS', 'Feather PX',
             'Coldtab SV', 'Dry Bass J', 'Intim8 BC', 'Secrets TU',
             'Veldisa BC', 'PulsHarp', 'LA Lore HS', 'Plucker JS',
             'Harmone TU', 'VibrPad2BC']

def main():
    run()
    
if __name__ == '__main__':
    main()
