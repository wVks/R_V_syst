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
                totals=totals, media_tb_day=media_bytes_day / 1e12,
                media_peak_mbps=media_bytes_day / 86400 * 6 * 8 / 1e6,
                media_origin_tb_day=media_bytes_day * 0.05 / 1e12)


if __name__ == '__main__':
    result = calculate()
    assert DAU <= MAU
    assert sum(x[1] for x in LOAD) == 57_480_000
    assert abs(result['totals']['in_gb_day'] - 24.24) < 1e-9
    assert abs(result['totals']['out_gb_day'] - 173.16) < 1e-9
    print(json.dumps(result, ensure_ascii=False, indent=2))
