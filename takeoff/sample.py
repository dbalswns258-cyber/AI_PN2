"""Synthetic data only; not a school project or an approved takeoff standard."""
import json
from pathlib import Path
import ezdxf


def create_sample(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    doc = ezdxf.new('R2010')
    doc.units = 4
    doc.layers.new('MIXED_DESIGNER_LAYER')
    m = doc.modelspace()
    a = m.add_line((0, 0), (3000, 4000), dxfattribs={'layer': 'MIXED_DESIGNER_LAYER'})
    b = m.add_lwpolyline([(6000, 0), (8000, 0), (8000, 1000)])
    c = m.add_lwpolyline([(10000, 0, 1), (12000, 0, 0)], format='xyb')
    duplicate = m.add_line((3000, 4000), (0, 0), dxfattribs={'layer': 'MIXED_DESIGNER_LAYER'})
    unresolved = m.add_line((0, 7000), (2000, 7000))
    m.add_text('WATER DN20 / SYNTHETIC ONLY', dxfattribs={'height': 180, 'insert': (0, 4500)})
    block = doc.blocks.new('FIXTURE_REFERENCE')
    block.add_line((0, 0), (1000, 0))
    m.add_blockref('FIXTURE_REFERENCE', (4000, 6000))
    m.add_circle((10000, 6000), 300)
    m.add_line((0, 9000, 0), (1000, 9000, 3000))
    doc.saveas(directory / 'sample.dxf')
    decisions = {}
    for e, diameter in [(a, '20'), (b, '25'), (c, '20')]:
        decisions[e.dxf.handle] = {'status': 'confirmed', 'system': 'water', 'diameter_mm': diameter,
                                   'evidence': '합성 테스트 명세의 배관 지정', 'floor': '테스트 1층', 'zone': '합성 구간'}
    decisions[duplicate.dxf.handle] = {'status': 'excluded', 'evidence': f'합성 중복: {a.dxf.handle}만 계산'}
    (directory / 'decisions.json').write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / 'expected.json').write_text(json.dumps({'DN20_m': '8.142', 'DN25_m': '3.000',
        'pending_handle': unresolved.dxf.handle, 'synthetic_only': True}, indent=2))
    return directory / 'sample.dxf'
