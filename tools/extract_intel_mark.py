#!/usr/bin/env python3
"""Extract the classic mark from Intel's official 317804-010 PDF cover.

Build-only: requires pdftocairo and FontTools. Pass the original downloaded PDF;
the checksum guard prevents extracting another edition with different artwork.
"""
from pathlib import Path
import argparse
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import hashlib,json
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('pdf',type=Path)
args=parser.parse_args()
expected='c554f4c7a26dacf291051125c59b0761c978af4cace9fb15863d119fcbf8de22'
checksum=hashlib.sha256(args.pdf.read_bytes()).hexdigest()
if checksum!=expected:parser.error('PDF checksum differs from the verified Intel 317804-010 edition')
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='intel-mark-') as directory:
    svg=Path(directory)/'cover.svg'
    subprocess.run(['pdftocairo','-f','1','-l','1','-svg',str(args.pdf),str(svg)],check=True)
    doc=ET.parse(svg).getroot()
paths=[p.attrib['d'] for p in doc.findall('./{http://www.w3.org/2000/svg}path') if p.attrib.get('fill')!='none'][:8]
assert len(paths)==8
original_fill=doc.findall('./{http://www.w3.org/2000/svg}path')[0].attrib['fill']
names=['oval','l','i','dot','t','e','n','registration']
bounds={}
for name,d in zip(names,paths):
 pen=BoundsPen(None);parse_path(d,pen);bounds[name]=pen.bounds
x0,y0,x1,y1=bounds['oval'];scale=24/(x1-x0);oy=(24-(y1-y0)*scale)/2
matrix=(scale,0,0,scale,-x0*scale,oy-y0*scale)
normal={}
for name,d in zip(names,paths):
 pen=SVGPathPen(None);parse_path(d,TransformPen(pen,matrix));normal[name]=pen.getCommands()
normal['letters']=' '.join(normal[name] for name in ('i','dot','n','t','e','l'))
e=bounds['e'];normal['eBox']=[(e[0]-x0)*scale,oy+(e[1]-y0)*scale,(e[2]-e[0])*scale,(e[3]-e[1])*scale]
normal={k:normal[k] for k in ('oval','letters','e','eBox','registration')}
normal['eGrid']=[16,19]
# Optical hint: remove the terminal cell that becomes a raised tooth after scaling.
normal['eOmit']=[[12,13]]
svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><title>Classic Intel mark extracted from Intel document 317804-010, page 1</title><g fill="'+original_fill+'">'+''.join('<path id="'+name+'" d="'+d+'"/>' for name,d in normal.items() if name in ('oval','letters','registration'))+'</g></svg>\n'
(root/'prototypes/theme-lab/themes/intel/source.svg').write_text(svg)
(root/'agent_theme/themes/assets/intel-source.svg').write_text(svg)
(root/'prototypes/theme-lab/themes/intel/official-paths.js').write_text('// Extracted from Intel document 317804-010 (December 2008), page 1. See SOURCE.md.\nexport const intelMark = '+json.dumps(normal,separators=(',',':'))+';\n')
provenance=dict(document='Intel Thermal and Mechanical Design Guidelines, 317804-010',date='December 2008',url='https://cdrdv2-public.intel.com/841119/317804.pdf',page=1,sha256=checksum,extraction='pdftocairo SVG, unmodified filled cover paths; uniform normalization to a 24-unit-wide oval',source_bounds=bounds,source_fill=original_fill,svg_sha256=hashlib.sha256(svg.encode()).hexdigest(),normalization=list(matrix),e_box=normal['eBox'],terminal_e_grid=normal['eGrid'],terminal_e_omit=normal['eOmit'],terminal_validation_logo_columns=[49,77,107])
(root/'prototypes/theme-lab/themes/intel/provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
(root/'agent_theme/themes/assets/intel-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
print('Extracted Intel cover paths and provenance (317804-010, page 1)')
