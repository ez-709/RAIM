# RAIM

GPS Single Point Positioning (SPP) с одночастотным C/A-кодом по данным IGS-станций.

## Запуск

```
pip install numpy requests hatanaka matplotlib cartopy
python main.py
```

## Структура

```
RAIM/
├── config.json              параметры (станции, режим скачивания)
├── main.py                  оркестратор: качает, парсит, считает, рисует
├── math_model.py            GPSSatellite — расчёт позиции спутника по эфемериде
├── navigation_solution.py   lse_epoch, spp, ephemeris_solution, save/report PVT
├── plots.py                 карта подспутниковых трасс
├── utils.py                 read_config, write_csv, DATA_DIR
├── parsers/
│   └── rinex_parser.py      parse_rinex_nav, parse_rinex_obs, get_approx_position
└── tests/
    └── test.py              проверка GPSSatellite по IS-GPS-200 Table C-1
```

## Куда что пишется

| Файл | Содержимое |
|---|---|
| `data/tech_data/brdc_*.nav` | broadcast-эфемериды GPS, скачанные с IGS |
| `data/tech_data/eci.csv`    | орбиты ИСЗ в инерциальной СК |
| `data/tech_data/ecef.csv`   | орбиты ИСЗ в земной вращающейся СК |
| `data/tech_data/pvt.csv`    | позиция приёмника по эпохам (основной результат) |
| `rinex_data/*.rnx`          | псевдодальности с IGS-станции |

## Конфиг

- `download.mode: true` — скачивать nav/obs из интернета.
- `download.mode: false` — использовать уже лежащие файлы.
- `download.days_back` — за сколько дней назад брать данные (0 = сегодня, но обычно 1, т.к. свежие появляются с задержкой ~1 час).
- `stations` — список IGS-станций, пробуются по порядку, останавливаемся на первой удачной.
