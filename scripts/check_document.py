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

row = next(line for line in readme.splitlines() if line.startswith('| API: 300 B'))
values = [number(cell.strip().split(' GB')[0].split(' Mbit/s')[0])
          for cell in row.split('|')[2:6]]
for actual, key in zip(values, ('wire_in_gb_day', 'wire_out_gb_day',
                               'wire_in_peak_mbps', 'wire_out_peak_mbps')):
    assert abs(actual - model[key]) < .011, (actual, key)

storage_rows = {
    'postgres': '| PostgreSQL | 718,25',
    'redis_ram': '| Redis | 1 млн',
    'kafka': '| Kafka | 151,2',
    'clickhouse': '| ClickHouse | 1 280,4',
    's3': '| S3: медиа,',
    's3_dr': '| S3: независимая DR-копия',
    'prometheus': '| Prometheus (2 копии)',
    'logs_traces': '| Loki/Tempo в S3',
}
for key, prefix in storage_rows.items():
    row = next(line for line in readme.splitlines() if line.startswith(prefix))
    for column, field in ((4, 'copies_now_tb'), (5, 'growth_and_free_tb')):
        # Cells may have units or a WAL reserve following the main decimal.
        value = re.match(r'\s*([\d ,]+)', row.split('|')[column]).group(1)
        value = number(value.rstrip(' ,'))
        assert abs(value - model['storage'][field][key]) < .000001, (key, field, value)

apps = readme.split('### 5.3.')[1].split('Расчёт CPU')[0]
cpu = ram = 0
for line in apps.splitlines():
    cells = [cell.strip() for cell in line.split('|')]
    if len(cells) != 6:
        continue
    if cells[1].startswith('**Сумма'):
        expected_cpu, expected_ram = map(int, re.findall(r'\d+', cells[3]))
        assert (cpu, ram) == (expected_cpu, expected_ram), (cpu, ram)
        break
    if not cells[2][:1].isdigit():
        continue
    replicas = int(re.match(r'\d+', cells[2]).group())
    cores, memory = map(int, cells[3].split('/'))
    cpu += replicas * cores
    ram += replicas * memory
else:
    raise AssertionError('Application resource total missing')

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
print(f'OK: API/network/storage tables, app resources {cpu} vCPU/{ram} GiB, '
      f'local links, PlantUML source, PNG {width}x{height}')
