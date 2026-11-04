from pathlib import Path
from decimal import Decimal
import math
import os
import re
import sqlite3
from contextlib import closing

# Пути привязаны к расположению скрипта, а не к папке, из которой его запустили.
RESULTS_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = RESULTS_DIR / "output"
# Источник данных — SQLite-база.
DATABASE_PATH = RESULTS_DIR / "data" / "online_store.sqlite"
QUERIES_PATH = RESULTS_DIR / "sql" / "queries.sql"
# Локальный кэш шрифтов; графики работают без GUI и системной настройки кэша.
os.environ.setdefault("MPLCONFIGDIR", str(RESULTS_DIR / ".matplotlib"))

import matplotlib
# Agg позволяет сохранять изображения без открытия окна графического интерфейса.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

INK = "#182C40"
MUTED = "#536779"
BLUE = "#2763A6"
TEAL = "#168579"
GRID = "#DDE5EC"
MILLION = Decimal("1000000")
MONTH_NAMES = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
               "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

# Единое оформление обоих графиков; DejaVu Sans поддерживает кириллицу.
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "text.color": INK,
    "axes.labelcolor": MUTED,
    "xtick.color": INK,
    "ytick.color": MUTED,
    "svg.fonttype": "none",
    "svg.hashsalt": "online-store-revenue",
})


def read_revenue(query_number):
    """Загружает выручку из SQLite через запрос из sql/queries.sql.

    Args:
        query_number (int): Номер запроса, возвращающего столбец revenue_rub.
            Для категорий используется Q2, для месяцев — Q5.

    Returns:
        list[dict]: Строки результата с именами столбцов в качестве ключей.
            Значение revenue_rub преобразовано в Decimal и выражено в рублях.

    Raises:
        OSError: Не удалось прочитать файл SQL-запросов.
        sqlite3.Error: Не удалось открыть базу или выполнить запрос.
        ValueError: Запрос не найден, результат пуст либо выручка
            отрицательная или не является конечным числом.
        KeyError: В результате отсутствует столбец revenue_rub.
        decimal.InvalidOperation: Значение выручки нельзя преобразовать в Decimal.
    """
    # Заголовки вида «-- Q2 |» отделяют SQL-запросы друг от друга.
    # Опережающая проверка в регулярном выражении сохраняет заголовок в блоке.
    blocks = re.split(r"(?=-- Q\d+ \|)", QUERIES_PATH.read_text(encoding="utf-8-sig"))
    query = next((block for block in blocks if block.startswith(f"-- Q{query_number} |")), None)
    if query is None:
        raise ValueError(f"Запрос Q{query_number} не найден в {QUERIES_PATH}")
    # mode=ro запрещает изменения и создание пустой БД при ошибке в пути.
    with closing(sqlite3.connect(DATABASE_PATH.as_uri() + "?mode=ro", uri=True)) as connection:
        # Имена столбцов SQL становятся ключами словаря: month, revenue_rub и др.
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(query)]
    if not rows:
        raise ValueError(f"Запрос Q{query_number} не вернул данных")
    for row in rows:
        # Decimal нужен для последующего суммирования денежных значений.
        # Преобразование через строку не переносит двоичный хвост float;
        # точность, уже потерянную при делении в SQL, оно не восстанавливает.
        row["revenue_rub"] = Decimal(str(row["revenue_rub"]))
        if not row["revenue_rub"].is_finite() or row["revenue_rub"] < 0:
            raise ValueError(f"Некорректная выручка в Q{query_number}")
    return rows


def ru_number(value, digits=2):
    """Форматирует число с десятичной запятой.

    Args:
        value (int | float | Decimal): Число для отображения.
        digits (int): Неотрицательное число знаков после запятой. По умолчанию 2.

    Returns:
        str: Число, округлённое до указанной точности, например «1234,50».

    Raises:
        ValueError: Указана недопустимая точность форматирования.
    """
    return f"{value:.{digits}f}".replace(".", ",")


def make_chart(title, xlabel, query, maximum, step):
    """Создаёт основу графика с заголовком, сеткой и подписью источника.

    Args:
        title (str): Заголовок графика.
        xlabel (str): Подпись горизонтальной оси.
        query (str): Обозначение SQL-запроса в подписи источника, например «Q2».
        maximum (float): Максимальная выручка в миллионах рублей;
            конечное неотрицательное число.
        step (float): Положительный конечный шаг вертикальной шкалы
            в миллионах рублей.

    Returns:
        tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]: Фигура и область
            построения для добавления столбцов или линии. Сохранение и закрытие
            фигуры выполняются отдельно.
    """
    fig, ax = plt.subplots(figsize=(12.8, 5.9), facecolor="white")
    # Оставляем место для заголовка, подписей осей и строки с источником данных.
    fig.subplots_adjust(left=0.075, right=0.975, top=0.79, bottom=0.23)
    fig.text(0.075, 0.925, title, fontsize=20)
    fig.text(0.075, 0.855, "Выручка, млн руб.", fontsize=11, color=MUTED)
    fig.text(0.075, 0.045,
             f"Источник: online_store.sqlite, {query}; синтетические данные; только completed.",
             fontsize=9.5, color=MUTED)
    ax.set_xlabel(xlabel, labelpad=19)
    # Нулевая база и запас над максимальным значением для подписей.
    # Верхняя граница кратна шагу и остаётся положительной при нулевой выручке.
    ax.set_ylim(0, max(step, math.ceil(maximum * 1.08 / step) * step))
    ax.yaxis.set_major_locator(MultipleLocator(step))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: ru_number(v, 1)))
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(axis="both", length=0, pad=10)
    return fig, ax


def save_chart(fig, name):
    """Сохраняет график в PNG и SVG, затем закрывает фигуру.

    Папка OUTPUT_DIR создаётся автоматически. Одноимённые файлы перезаписываются,
    а пути к сохранённым файлам выводятся в консоль.

    Args:
        fig (matplotlib.figure.Figure): Фигура для сохранения.
        name (str): Базовое имя файла без расширения и компонентов пути.

    Returns:
        None: Результат записывается в файлы name.png и name.svg.

    Raises:
        OSError: Не удалось создать папку или записать файл.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "svg"):
        destination = OUTPUT_DIR / f"{name}.{extension}"
        # Убираем дату создания из SVG, чтобы повторный запуск не менял её в файле.
        options = {"metadata": {"Date": None}} if extension == "svg" else {}
        fig.savefig(destination, dpi=220, facecolor="white", **options)
        print(f"Создан: {destination.relative_to(RESULTS_DIR)}")
    plt.close(fig)  # Освобождаем память после сохранения обоих форматов.


def plot_categories(rows):
    """Строит и сохраняет столбчатую диаграмму выручки по категориям.

    Args:
        rows (list[dict]): Непустой результат Q2 из read_revenue.
            Каждая строка содержит category_id (int), category (str)
            и revenue_rub (Decimal, неотрицательная конечная сумма в рублях).

    Returns:
        None: Диаграмма сохраняется в OUTPUT_DIR как category_revenue.png
            и category_revenue.svg.

    Raises:
        ValueError: Список пуст или идентификатор категории нельзя привести к int.
        KeyError: В строке отсутствует обязательное поле.
        OSError: Не удалось сохранить диаграмму.
    """
    # Сначала самые доходные категории; при равенстве — по идентификатору.
    rows = sorted(rows, key=lambda r: (-r["revenue_rub"], int(r["category_id"])))
    # В миллионы и float переводим только значения для отрисовки.
    values = [float(r["revenue_rub"] / MILLION) for r in rows]
    fig, ax = make_chart("Выручка по категориям", "Категория товара", "Q2", max(values), 0.5)
    # Две ведущие категории выделены синим цветом.
    bars = ax.bar(range(len(rows)), values, width=0.58,
                  color=[BLUE if i < 2 else TEAL for i in range(len(rows))])
    ax.set_xticks(range(len(rows)), [r["category"] for r in rows])
    ax.margins(x=0.04)
    ax.bar_label(bars, labels=[ru_number(v) for v in values], padding=8, fontsize=12, color=INK)
    save_chart(fig, "category_revenue")


def complete_months(rows):
    """Заполняет пропуски между первым и последним месяцами результата Q5.

    Args:
        rows (list[dict]): Непустой список строк с уникальным month (str,
            формат YYYY-MM) и revenue_rub (Decimal, сумма в рублях).
            Порядок входных строк может быть произвольным.

    Returns:
        list[dict]: Новый список в хронологическом порядке. Пропущенные месяцы
            получают revenue_rub = Decimal("0"). Исходные строки не изменяются
            и включаются в результат без копирования.

    Raises:
        ValueError: Список пуст, формат месяца неверен или месяц повторяется.
        KeyError: В строке отсутствует поле month.
    """
    if not rows:
        raise ValueError("Нет данных для помесячного графика")
    by_month = {}
    for row in rows:
        month = row["month"]
        # Q5 должен возвращать одну строку на месяц в формате YYYY-MM.
        if not isinstance(month, str) or not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", month):
            raise ValueError(f"Некорректный месяц в Q5: {month!r}")
        if month in by_month:
            raise ValueError(f"Повторяющийся месяц в Q5: {month}")
        by_month[month] = row
    # Для YYYY-MM строковый порядок совпадает с хронологическим.
    year, month = map(int, min(by_month).split("-"))
    end = max(by_month)
    result = []
    # Заполняем только промежутки внутри периода; за его границы не выходим.
    while (key := f"{year:04d}-{month:02d}") <= end:
        result.append(by_month.get(key, {"month": key, "revenue_rub": Decimal("0")}))
        # После декабря переходим к январю следующего года.
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return result


def plot_months(rows):
    """Строит и сохраняет линейный график выручки с непрерывной шкалой месяцев.

    Args:
        rows (list[dict]): Непустой результат Q5 из read_revenue.
            Каждая строка содержит month (str, формат YYYY-MM)
            и revenue_rub (Decimal, неотрицательная конечная сумма в рублях).
            Месяцы без продаж внутри периода добавляются с нулевой выручкой.

    Returns:
        None: График сохраняется в OUTPUT_DIR как monthly_revenue.png
            и monthly_revenue.svg.

    Raises:
        ValueError: Список пуст, формат месяца неверен или месяц повторяется.
        KeyError: В строке отсутствует обязательное поле.
        OSError: Не удалось сохранить график.
    """
    rows = complete_months(rows)
    years = sorted({r["month"][:4] for r in rows})
    period = years[0] if len(years) == 1 else f"{years[0]}–{years[-1]}"
    labels = [MONTH_NAMES[int(r["month"][5:7]) - 1] for r in rows]
    # При нескольких годах добавляем год под названием каждого месяца.
    if len(years) > 1:
        labels = [f"{label}\n{row['month'][:4]}" for label, row in zip(labels, rows)]
    values = [float(r["revenue_rub"] / MILLION) for r in rows]
    fig, ax = make_chart(f"Выручка по месяцам, {period}", "Месяц заказа", "Q5", max(values), 0.4)
    ax.plot(range(len(rows)), values, color=BLUE, linewidth=2.5, marker="o", markersize=6)
    ax.set_xticks(range(len(rows)), labels)
    ax.margins(x=0.04)
    for x, value in enumerate(values):
        # Подпись располагается выше точки; три знака в млн руб. дают шаг 1000 руб.
        ax.annotate(ru_number(value, 3), (x, value), xytext=(0, 12),
                    textcoords="offset points", ha="center", fontsize=12, color=INK)
    save_chart(fig, "monthly_revenue")


def main():
    """Загружает данные, сверяет итоги и сохраняет оба графика выручки.

    Использует пути DATABASE_PATH, QUERIES_PATH и OUTPUT_DIR. После сохранения
    выводит число категорий, число месяцев в результате Q5 и общую выручку.

    Returns:
        None: Результаты записываются в PNG/SVG и выводятся в консоль.

    Raises:
        ValueError: Итоги Q2 и Q5 различаются или данные не проходят проверки.
        OSError: Не удалось прочитать SQL-файл или сохранить графики.
        sqlite3.Error: Ошибка доступа к базе или выполнения SQL-запроса.
        KeyError: В результатах запросов отсутствуют обязательные поля.
        decimal.InvalidOperation: Выручку нельзя преобразовать в Decimal.
    """
    # Q2 объединяет categories, products, order_items и orders; Q5 — orders и order_items.
    # Оба SQL-запроса учитывают только completed и считают выручку как
    # SUM(quantity * unit_price_kopecks) / 100: цена берётся из позиции заказа.
    categories = read_revenue(2)
    months = read_revenue(5)
    # Группировки разные, но сумма продаж должна совпадать до построения графиков.
    category_total = sum(r["revenue_rub"] for r in categories)
    monthly_total = sum(r["revenue_rub"] for r in months)
    if category_total != monthly_total:
        raise ValueError("Итоги Q2 и Q5 не совпадают; проверьте запросы и связи данных в базе")
    plot_categories(categories)
    plot_months(months)
    print(f"Проверено: {len(categories)} категорий, {len(months)} месяцев; "
          f"общая выручка {ru_number(category_total)} руб.")


if __name__ == "__main__":
    # При импорте модуля функции доступны без автоматического запуска main().
    main()
