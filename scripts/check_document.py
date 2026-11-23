#!/usr/bin/env python3
"""Проверяет ключевые числа README и ссылки на локальные артефакты."""
from pathlib import Path
import re
import struct
from capacity import calculate

ROOT = Path(__file__).resolve().parents[1]
readme = (ROOT / 'README.md').read_text()
model = calculate()


def number(value):
    return float(value.replace('**', '').replace(' ', '').replace(',', '.'))


row = next(line for line in readme.splitlines() if line.startswith('| **Всего API**'))
values = [number(cell.strip()) for cell in row.split('|')[2:5]]
for actual, expected in zip(values, (model['totals']['requests_day'],
                                    model['totals']['rps'],
                                    model['totals']['peak_rps'])):
    assert abs(actual - expected) < .011, (actual, expected)

row = next(line for line in readme.splitlines() if line.startswith('| Полезные данные API |'))
values = [number(cell.strip().split(' GB')[0].split(' Mbit/s')[0])
          for cell in row.split('|')[2:6]]
for actual, key in zip(values, ('in_gb_day', 'out_gb_day', 'in_peak_mbps', 'out_peak_mbps')):
    assert abs(actual - model['totals'][key]) < .011, (actual, key)

for target in re.findall(r'\]\(([^)]+)\)', readme):
    if '://' in target or target.startswith('#'):
        continue
    path = target.split('#')[0]
    assert (ROOT / path).is_file(), f'Missing local link: {target}'

png = (ROOT / 'docs/diagrams/architecture.png').read_bytes()
assert png[:8] == b'\x89PNG\r\n\x1a\n'
width, height = struct.unpack('>II', png[16:24])
assert width >= 600 and height >= 400, (width, height)
puml = (ROOT / 'docs/diagrams/architecture.puml').read_text()
assert puml.startswith('@startuml') and puml.rstrip().endswith('@enduml')
assert readme.count('```') % 2 == 0, 'Unclosed code fence'
print(f'OK: capacity totals, local links, PlantUML source, PNG {width}x{height}')
