import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from matplotlib.colors import LinearSegmentedColormap

df_raw = None
df_work = None
fig = plt.Figure(figsize=(11, 6), dpi=100)
canvas = None
current_chart = "bar"

STORED_SELECTED_HS = []
STORED_SELECTED_FW = []

plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False
sns.set_style("whitegrid")


df_raw = pd.read_csv('data.csv')
df_raw['datetime'] = pd.to_datetime(df_raw['ts'], unit='s')

def preprocess_data():
    global df_raw
    df_work = df_raw.copy()
    for col in df_work.columns:
        if pd.api.types.is_numeric_dtype(df_work[col]):
            df_work[col] = df_work[col].fillna(0).replace([np.inf, -np.inf], 0)
    df_work['fps'] = df_work['fps'].clip(30, 144)
    df_work['comf'] = df_work['comf'] / 10
    df_work['comf'] = df_work['comf'].clip(0, 10)
    df_work['lat'] = df_work['lat'].clip(lower=0)
    df_work['pos_err'] = df_work['pos_err'].clip(lower=0)
    return df_work

root = tk.Tk() #Создаем главное окно
root.title(f"Дашборд: VR/Трекеры")
root.geometry("1400x700")
root.configure(bg="#f0f2f5")

plot_frame = tk.Frame(root, bg="white", relief=tk.SUNKEN, bd=1)
plot_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

canvas = FigureCanvasTkAgg(fig, master=plot_frame)
canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

toolbar = NavigationToolbar2Tk(canvas, plot_frame)
toolbar.update()
toolbar.pack(side=tk.TOP, fill=tk.X)

#фильтры
filter_frame = tk.Frame(root, bg="#f0f2f5", relief=tk.RAISED, bd=1)
filter_frame.pack(fill=tk.X, padx=10, pady=3)

agg_method = tk.StringVar(value="mean")
smoothing_enabled = tk.BooleanVar(value=False)
resample_period = tk.StringVar(value="Дни")
date_start = tk.StringVar(value=df_raw['datetime'].min().strftime('%Y-%m-%d'))
date_end = tk.StringVar(value=df_raw['datetime'].max().strftime('%Y-%m-%d'))
period_map = {"Часы": "h", "Дни": "D", "Недели": "W", "Месяцы": "ME"}

row1 = tk.Frame(filter_frame, bg="#f0f2f5")
row1.pack(fill=tk.X, pady=2)
tk.Label(row1, text="Гарнитуры (Ctrl+Click):", bg="#f0f2f5", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=5)
hs_listbox = tk.Listbox(row1, selectmode=tk.MULTIPLE, height=4, width=15, exportselection=False)
hs_listbox.pack(side=tk.LEFT, padx=2)
hs_scroll = tk.Scrollbar(row1, orient=tk.VERTICAL, command=hs_listbox.yview)
hs_scroll.pack(side=tk.LEFT, fill=tk.Y)
hs_listbox.config(yscrollcommand=hs_scroll.set)

tk.Label(row1, text="Версии FW (Ctrl+Click):", bg="#f0f2f5", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=20)
fw_listbox = tk.Listbox(row1, selectmode=tk.MULTIPLE, height=4, width=12, exportselection=False)
fw_listbox.pack(side=tk.LEFT, padx=2)
fw_scroll = tk.Scrollbar(row1, orient=tk.VERTICAL, command=fw_listbox.yview)
fw_scroll.pack(side=tk.LEFT, fill=tk.Y)
fw_listbox.config(yscrollcommand=fw_scroll.set)

# Кнопки
btn_frame = tk.Frame(row1, bg="#f0f2f5")
btn_frame.pack(side=tk.LEFT, padx=20)
apply_btn = tk.Button(btn_frame, text="Применить", command=lambda: on_apply_filters(), bg="#4CAF50", fg="white", width=14)
apply_btn.pack(side=tk.TOP, pady=2)
reset_btn = tk.Button(btn_frame, text="Сбросить всё", command=lambda: reset_selection(), bg="#f44336", fg="white", width=14)
reset_btn.pack(side=tk.TOP, pady=2)

row2 = tk.Frame(filter_frame, bg="#f0f2f5")
row2.pack(fill=tk.X, pady=2)
tk.Label(row2, text="Агрегация:", bg="#f0f2f5", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=5)
ttk.Radiobutton(row2, text="Среднее", variable=agg_method, value="mean").pack(side=tk.LEFT)
ttk.Radiobutton(row2, text="Медиана", variable=agg_method, value="median").pack(side=tk.LEFT)
ttk.Radiobutton(row2, text="Макс", variable=agg_method, value="max").pack(side=tk.LEFT)
smooth_cb = ttk.Checkbutton(row2, text="Сглаживание", variable=smoothing_enabled)
smooth_cb.pack(side=tk.LEFT, padx=10)
tk.Label(row2, text="Шаг времени:", bg="#f0f2f5", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=5)
period_combo = ttk.Combobox(row2, textvariable=resample_period, width=8, values=['Часы', 'Дни', 'Недели', 'Месяцы'])
period_combo.pack(side=tk.LEFT, padx=2)
tk.Label(row2, text="Даты:", bg="#f0f2f5", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=10)
tk.Label(row2, text="с:", bg="#f0f2f5").pack(side=tk.LEFT, padx=1)
date_start_entry = tk.Entry(row2, textvariable=date_start, width=10)
date_start_entry.pack(side=tk.LEFT, padx=1)
tk.Label(row2, text="по:", bg="#f0f2f5").pack(side=tk.LEFT, padx=1)
date_end_entry = tk.Entry(row2, textvariable=date_end, width=10)
date_end_entry.pack(side=tk.LEFT, padx=1)
apply_date_btn = tk.Button(row2, text="Применить", command=lambda: on_apply_filters(), bg="#2196F3", fg="white")
apply_date_btn.pack(side=tk.LEFT, padx=10)

#фильтры
def on_hs_select(event=None):
    global STORED_SELECTED_HS
    STORED_SELECTED_HS = [int(hs_listbox.get(i)) for i in hs_listbox.curselection()]

def on_fw_select(event=None):
    global STORED_SELECTED_FW
    STORED_SELECTED_FW = [fw_listbox.get(i) for i in fw_listbox.curselection()]

def populate_initial_lists():
    for hs in sorted(df_work['hs_id'].unique()):
        hs_listbox.insert(tk.END, hs)
    for fw in sorted(df_work['fw_ver'].unique()):
        fw_listbox.insert(tk.END, fw)

def reset_selection():
    global STORED_SELECTED_HS, STORED_SELECTED_FW
    hs_listbox.selection_clear(0, tk.END)
    fw_listbox.selection_clear(0, tk.END)
    STORED_SELECTED_HS = []
    STORED_SELECTED_FW = []
    on_apply_filters()

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except: return False

def apply_filters():
    df_filtered = df_work.copy()
    start_str = date_start.get().strip()
    end_str = date_end.get().strip()
    if validate_date(start_str) and validate_date(end_str):
        try:
            start = pd.to_datetime(start_str)
            end = pd.to_datetime(end_str) + timedelta(days=1)
            df_filtered = df_filtered[(df_filtered['datetime'] >= start) & (df_filtered['datetime'] <= end)]
        except: pass
    else:
        if not validate_date(start_str): messagebox.showwarning("Ошибка", f"Некорректная дата: {start_str}")
        if not validate_date(end_str):messagebox.showwarning("Ошибка", f"Некорректная дата: {end_str}")
        return df_work
    
    if STORED_SELECTED_HS:
        df_filtered = df_filtered[df_filtered['hs_id'].isin(STORED_SELECTED_HS)]
    if STORED_SELECTED_FW:
        df_filtered = df_filtered[df_filtered['fw_ver'].isin(STORED_SELECTED_FW)]
    return df_filtered

hs_listbox.bind('<<ListboxSelect>>', on_hs_select)
fw_listbox.bind('<<ListboxSelect>>', on_fw_select)

def plot_bar():
    global current_chart
    current_chart = "bar"
    fig.clear()
    df_filtered = apply_filters()
    if len(df_filtered) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', fontsize=14)
        canvas.draw_idle()
        return
    if agg_method.get() == 'mean':
        df_grouped = df_filtered.groupby('hs_id')['fps'].mean().reset_index()
        agg_name = "Среднее"
    elif agg_method.get() == 'median':
        df_grouped = df_filtered.groupby('hs_id')['fps'].median().reset_index()
        agg_name = "Медиана"
    else:
        df_grouped = df_filtered.groupby('hs_id')['fps'].max().reset_index()
        agg_name = "Максимум"
    
    ax = fig.add_subplot(111)
    bars = ax.bar(df_grouped['hs_id'].astype(str), df_grouped['fps'], color='steelblue', edgecolor='black', alpha=0.8)
    ax.set_title(f'Частота кадров (FPS) по ID гарнитуры\nАгрегация: {agg_name}', fontsize=12)
    ax.set_xlabel('ID гарнитуры', fontsize=11)
    ax.set_ylabel('FPS', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    for bar, val in zip(bars, df_grouped['fps']):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{val:.1f}', ha='center', va='bottom', fontsize=9)
    fig.tight_layout()
    canvas.draw_idle()

def plot_line():
    global current_chart
    current_chart = "line"
    fig.clear()
    df_filtered = apply_filters()
    if len(df_filtered) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', fontsize=14)
        canvas.draw_idle()
        return
    df_plot = df_filtered.copy()
    df_plot = df_plot.set_index('datetime').sort_index()
    period = period_map[resample_period.get()]
    if agg_method.get() == 'mean':df_agg = df_plot['fps'].resample(period).mean()
    elif agg_method.get() == 'median':df_agg = df_plot['fps'].resample(period).median()
    else:df_agg = df_plot['fps'].resample(period).max()
    if smoothing_enabled.get():df_agg = df_agg.rolling(window=3, min_periods=1).mean()
    ax = fig.add_subplot(111)
    ax.plot(df_agg.index, df_agg.values, 'b-', linewidth=2, label='FPS')
    ax.set_title(f'Частота кадров по времени (шаг: {resample_period.get()})', fontsize=12)
    ax.set_xlabel('Время', fontsize=11)
    ax.set_ylabel('FPS', fontsize=11)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    canvas.draw_idle()

def plot_scatter():
    global current_chart
    current_chart = "scatter"
    fig.clear()
    df_filtered = apply_filters()
    if len(df_filtered) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', fontsize=14)
        canvas.draw_idle()
        return
    if agg_method.get() == 'mean':
        df_grouped = df_filtered.groupby('hs_id')['fps'].mean().reset_index()
        agg_name = "Среднее"
    elif agg_method.get() == 'median':
        df_grouped = df_filtered.groupby('hs_id')['fps'].median().reset_index()
        agg_name = "Медиана"
    else:
        df_grouped = df_filtered.groupby('hs_id')['fps'].max().reset_index()
        agg_name = "Максимум"
    ax = fig.add_subplot(111)
    ax.scatter(df_grouped['hs_id'], df_grouped['fps'], 
               s=100, c='red', edgecolors='black', zorder=5)
    ax.plot(df_grouped['hs_id'], df_grouped['fps'], 'r--', alpha=0.5, linewidth=1)
    ax.set_title(f'FPS по ID гарнитуры\nАгрегация: {agg_name}', fontsize=12)
    ax.set_xlabel('ID гарнитуры', fontsize=11)
    ax.set_ylabel('FPS', fontsize=11)
    ax.set_xticks(df_grouped['hs_id'])
    ax.grid(True, alpha=0.3, axis='y')
    for i, row in df_grouped.iterrows():
        ax.annotate(f'{row["fps"]:.1f}', (row["hs_id"], row["fps"]),
                    textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
    fig.tight_layout()
    canvas.draw_idle()

def plot_heat_map():
    global current_chart
    current_chart = "heatmap"
    fig.clear()
    df_filtered = apply_filters()
    if len(df_filtered) == 0:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', fontsize=14)
        canvas.draw_idle()
        return
    method = agg_method.get()
    if method == 'mean':
        df_grouped = df_filtered.groupby(['fw_ver', 'hs_id'])['comf'].mean().reset_index()
        agg_name = "средний"
    elif method == 'median':
        df_grouped = df_filtered.groupby(['fw_ver', 'hs_id'])['comf'].median().reset_index()
        agg_name = "медианный"
    else:  # max
        df_grouped = df_filtered.groupby(['fw_ver', 'hs_id'])['comf'].max().reset_index()
        agg_name = "максимальный"
    pivot_table = df_grouped.pivot_table( values='comf',index='fw_ver',columns='hs_id', fill_value=np.nan)
    if pivot_table.empty or pivot_table.isnull().all().all():
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', fontsize=14)
        canvas.draw_idle()
        return
    ax = fig.add_subplot(111)
    colors = ['red', 'yellow', 'green']
    custom_cmap = LinearSegmentedColormap.from_list('custom', colors, N=256)
    sns.heatmap( pivot_table, annot=True, fmt='.2f', cmap=custom_cmap, center=5, vmin=0, vmax=10,  
        square=True, linewidths=0.5, linecolor='white',  annot_kws={'size': 9, 'weight': 'bold'},
        cbar_kws={'label': f'{agg_name} комфорт (0-10)', 'shrink': 0.8}, ax=ax) 
    ax.set_title(f'Тепловая карта комфорта\n{agg_name} значение\nВерсия FW vs ID гарнитуры', fontsize=12)
    ax.set_xlabel('ID гарнитуры', fontsize=11)
    ax.set_ylabel('Версия прошивки', fontsize=11)
    fig.tight_layout()
    canvas.draw_idle()


def on_apply_filters():
    if current_chart == "line": plot_line()
    elif current_chart == "bar": plot_bar()
    elif current_chart == "scatter": plot_scatter()
    elif current_chart == "heatmap": plot_heat_map()
    
def refresh_data():
    global df_work, current_chart, STORED_SELECTED_HS, STORED_SELECTED_FW
    df_work = preprocess_data()
    date_start.set(df_work['datetime'].min().strftime('%Y-%m-%d'))
    date_end.set(df_work['datetime'].max().strftime('%Y-%m-%d'))
    old_hs = STORED_SELECTED_HS.copy()
    old_fw = STORED_SELECTED_FW.copy()
    hs_listbox.delete(0, tk.END)
    for hs in sorted(df_work['hs_id'].unique()):
        hs_listbox.insert(tk.END, hs)
    fw_listbox.delete(0, tk.END)
    for fw in sorted(df_work['fw_ver'].unique()):
        fw_listbox.insert(tk.END, fw)
    STORED_SELECTED_HS = []
    for hs in old_hs:
        if hs in df_work['hs_id'].unique():
            STORED_SELECTED_HS.append(hs)
            idx = list(df_work['hs_id'].unique()).index(hs)
            hs_listbox.selection_set(idx)
    STORED_SELECTED_FW = []
    for fw in old_fw:
        if fw in df_work['fw_ver'].unique():
            STORED_SELECTED_FW.append(fw)
            idx = list(df_work['fw_ver'].unique()).index(fw)
            fw_listbox.selection_set(idx)
    if current_chart == "line":  plot_line()
    elif current_chart == "bar":  plot_bar()
    elif current_chart == "scatter":  plot_scatter()
    elif current_chart == "heatmap":  plot_heat_map()
    messagebox.showinfo("Обновление", "Данные обновлены!")

def export_plot():
    filepath = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")])
    if filepath:
        fig.savefig(filepath, dpi=300, bbox_inches='tight')
        messagebox.showinfo("Экспорт", "График сохранён!")

def on_agg_change(*args):
    if current_chart == "line":
        plot_line()
    elif current_chart == "bar":
        plot_bar()
    elif current_chart == "scatter":
        plot_scatter()
    elif current_chart == "heatmap":
        plot_heat_map()

agg_method.trace_add('write', on_agg_change)
smoothing_enabled.trace_add('write', on_agg_change)
resample_period.trace_add('write', on_agg_change)

ctrl_frame = tk.Frame(root, bg="#f0f2f5")
ctrl_frame.pack(fill=tk.X, padx=10, pady=10)
btn_style = {"font": ("Arial", 10, "bold"), "width": 15, "height": 1}
tk.Button(ctrl_frame, text="Столбчатая", command=plot_bar, bg="#4CAF50", fg="white", **btn_style).pack(side=tk.LEFT, padx=4)
tk.Button(ctrl_frame, text="Линейная", command=plot_line, bg="#2196F3", fg="white", **btn_style).pack(side=tk.LEFT, padx=4)
tk.Button(ctrl_frame, text="Точечная", command=plot_scatter, bg="#FF9800", fg="white", **btn_style).pack(side=tk.LEFT, padx=4)
tk.Button(ctrl_frame, text="Тепловая карта", command=plot_heat_map, bg="#9C27B0", fg="white", **btn_style).pack(side=tk.LEFT, padx=4)
tk.Button(ctrl_frame, text="Обновить", command=refresh_data,bg="#607D8B", fg="white", **btn_style).pack(side=tk.RIGHT, padx=4)
tk.Button(ctrl_frame, text="Экспорт", command=export_plot, bg="#795548", fg="white", **btn_style).pack(side=tk.RIGHT, padx=4)

df_work = preprocess_data()
populate_initial_lists()
plot_bar()
root.mainloop()