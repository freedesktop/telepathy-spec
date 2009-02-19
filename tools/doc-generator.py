#!/usr/bin/env python
#
# doc-generator.py
#
# Generates HTML documentation from the parsed spec using Cheetah templates.
#
# Copyright (C) 2009 Collabora Ltd.
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or (at
# your option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Authors: Davyd Madeley <davyd.madeley@collabora.co.uk>
#

import sys
import os.path

try:
    from Cheetah.Template import Template
except ImportError, e:
    print >> sys.stderr, e
    print >> sys.stderr, "Install `python-cheetah'?"
    sys.exit (-1)

import specparser

template_path = os.path.join (os.path.dirname (sys.argv[0]),
                              '../doc/templates')
output_path = os.path.join (os.path.dirname (sys.argv[0]),
                              '../doc/spec')

def load_template (filename):
    try:
        file = open (os.path.join (template_path, filename))
        template_def = file.read ()
        file.close ()
    except IOError, e:
        print >> sys.stderr, "Could not load template file `%s'" % filename
        print >> sys.stderr, e
        sys.exit (-1)

    return template_def

# write out HTML files for each of the interfaces
spec = specparser.parse (sys.argv[1])
namespace = {}
template_def = load_template ('interface.html')
t = Template (template_def, namespaces = [namespace])
for interface in spec.interfaces:
    namespace['interface'] = interface
    
    # open the output file
    out = open (os.path.join (output_path, '%s.html' % interface.name), 'w')
    print >> out, t
    out.close ()

# write out a TOC
template_def = load_template ('index.html')
t = Template (template_def, namespaces = [spec])
out = open (os.path.join (output_path, 'index.html'), 'w')
print >> out, t
out.close ()

# write out the generic types
namespace = { 'spec': spec }
template_def = load_template ('generic-types.html')
t = Template (template_def, namespaces = namespace)
out = open (os.path.join (output_path, 'generic-types.html'), 'w')
print >> out, t
out.close ()

# write out the errors
namespace = { 'spec': spec }
template_def = load_template ('errors.html')
t = Template (template_def, namespaces = namespace)
out = open (os.path.join (output_path, 'errors.html'), 'w')
print >> out, t
out.close ()

# write out the fullindex
namespace = { 'spec': spec }
template_def = load_template ('fullindex.html')
t = Template (template_def, namespaces = namespace)
out = open (os.path.join (output_path, 'fullindex.html'), 'w')
print >> out, t
out.close ()
