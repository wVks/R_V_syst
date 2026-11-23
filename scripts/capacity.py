#!/usr/bin/env python3
"""Проверяемая модель нагрузки. Десятичные kB/GB/TB; без внешних пакетов."""
import json

MAU = 1_200_000
DAU = 300_000
ORDERS_DAY = 120_000
# name, requests/day, peak factor, request bytes, response bytes
LOAD = [
    ('Каталог и меню', DAU * 24, 6, 1000, 20000),
    ('Поиск', DAU * 6, 6, 1000, 10000),
    ('Корзина', DAU * 4, 6, 2000, 2000),
    ('Оформление заказа', ORDERS_DAY, 6, 4000, 3000),
    ('Статус заказа', DAU * 8, 6, 500, 1000),
    ('Профиль и история', DAU * 2, 6, 1000, 2000),
    ('Геопозиции курьеров', 20000 * 6 * 3600 // 10, 4, 200, 100),
    ('Команды ресторанов/курьеров', ORDERS_DAY * 6, 6, 2000, 500),
    ('Платёжные callbacks', ORDERS_DAY * 2, 6, 2000, 500),
]

# name, count, bytes/record; retained rows at the current run rate.
POSTGRES = [
    ('profiles', 2400000, 2000), ('addresses', 4800000, 300),
    ('restaurants', 10000, 4000), ('dishes', 1000000, 2000),
    ('orders', ORDERS_DAY * 365, 4000),
    ('items', ORDERS_DAY * 365 * 5, 300),
    ('payments', ORDERS_DAY * 365 * 2, 500),
    ('history', ORDERS_DAY * 365 * 8, 200),
    ('outbox', ORDERS_DAY * 7 * 10, 500),
    ('idempotency', ORDERS_DAY * 7, 400),
]


def storage():
    pg = sum(count * size for _, count, size in POSTGRES) / 1e12
    kafka = (43200000 * 200 + 1200000 * 500 + 6000000 * 200) * 3 / 1e12
    ch = (43200000 * 7 * 100 + 1200000 * 365 * 500 + 6000000 * 90 * 200) / 1e12
    redis = (1000000 * 2000 + 150000 * 2000 + 20000 * 500 + 1000000 * 500) / 1e12
    backup = 2 * pg * 2 + 14 * 0.02
    metrics = 500000 * (86400 // 15) * 14 * 2 / 1e12
    logs_traces = (57480000 * 300 + .01 * 57480000 * 1000) * 14 / 4 / 1e12
    copies_now = dict(postgres=pg * 2 * 3, redis_ram=redis * 3 * 2,
                      kafka=kafka * 1.2 * 3, clickhouse=ch / 4 * 1.3 * 2,
                      s3=(.3 + backup + .01) * 1.5,
                      s3_dr=backup * 1.5, prometheus=metrics * 2,
                      logs_traces=logs_traces * 1.5)
    return dict(postgres_rows=sum(n for _, n, _ in POSTGRES),
                postgres_raw_tb=pg, copies_now_tb=copies_now,
                growth_and_free_tb={k: v * 2 / .7 for k, v in copies_now.items()})


def calculate():
    rows = []
    for name, count, peak, req, resp in LOAD:
        rows.append(dict(name=name, requests_day=count, rps=count / 86400,
                         peak_rps=count / 86400 * peak,
                         in_gb_day=count * req / 1e9,
                         out_gb_day=count * resp / 1e9,
                         in_peak_mbps=count / 86400 * peak * req * 8 / 1e6,
                         out_peak_mbps=count / 86400 * peak * resp * 8 / 1e6))
    totals = {key: sum(row[key] for row in rows) for key in rows[0] if key != 'name'}
    media_bytes_day = DAU * 24 * 10 * 30000
    return dict(mau=MAU, dau=DAU, orders_day=ORDERS_DAY, rows=rows,
                totals=totals, storage=storage(), media_tb_day=media_bytes_day / 1e12,
                media_peak_mbps=media_bytes_day / 86400 * 6 * 8 / 1e6,
                media_origin_tb_day=media_bytes_day * 0.05 / 1e12,
                wire_in_gb_day=(totals['in_gb_day'] + totals['requests_day'] * 300 / 1e9) * 1.3,
                wire_out_gb_day=(totals['out_gb_day'] + totals['requests_day'] * 300 / 1e9) * 1.3,
                wire_in_peak_mbps=(totals['in_peak_mbps'] + totals['peak_rps'] * 300 * 8 / 1e6) * 1.3,
                wire_out_peak_mbps=(totals['out_peak_mbps'] + totals['peak_rps'] * 300 * 8 / 1e6) * 1.3)


if __name__ == '__main__':
    result = calculate()
    assert DAU <= MAU
    assert sum(x[1] for x in LOAD) == 57_480_000
    assert abs(result['totals']['in_gb_day'] - 24.24) < 1e-9
    assert abs(result['totals']['out_gb_day'] - 173.16) < 1e-9
    assert abs(result['storage']['postgres_raw_tb'] - .367596) < 1e-12
    print(json.dumps(result, ensure_ascii=False, indent=2))
