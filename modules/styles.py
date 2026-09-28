# modules/styles.py
import tkinter as tk
from tkinter import ttk
from datetime import datetime


COLORS = {
    'light': '#f8fafc',
    'white': '#ffffff',
    'text_dark': '#1e293b',
    'text_light': '#64748b',
    'primary': '#2563eb',
    'primary_light': '#dbeafe',
    'primary_dark': '#1e40af',
    'secondary': '#475569',
    'success': '#059669',
    'success_light': '#d1fae5',
    'danger': '#dc2626',
    'danger_light': '#fee2e2',
    'warning': '#d97706',
    'warning_light': '#fef3c7',
    'info': '#0891b2',
    'info_light': '#cffafe',
    'background': '#f8fafc',
    'surface': '#ffffff',
    'text_primary': '#1e293b',
    'text_secondary': '#64748b',
    'border': '#e2e8f0',
    'divider': '#f1f5f9',
    'hover': '#f1f5f9',
    'focus': '#e0e7ff',
    'text': '#1e293b',
    'tree_bg': '#f8fafc',
    'tree_selected': '#dbeafe'
}

FONT = {
    'family': 'Segoe UI',
    'header': ('Segoe UI', 24, 'bold'),
    'title': ('Segoe UI', 18, 'bold'),
    'subtitle': ('Segoe UI', 15, 'bold'),
    'body_large': ('Segoe UI', 12, ''),
    'body': ('Segoe UI', 11, ''),
    'body_small': ('Segoe UI', 10, ''),
    'caption': ('Segoe UI', 9, ''),
    'button': ('Segoe UI', 11, 'bold'),
    'input': ('Segoe UI', 11, ''),
    'label': ('Segoe UI', 11, 'bold')
}

LAYOUT = {
    'page_padx': 18,
    'page_pady': 14,
    'card_padx': 12,
    'card_pady': 10,
    'gap': 12,
    'small_gap': 5,
    'header_height': 48,
    'field_width': 18,
}

BUTTON_STYLES = {
    'primary': {
        'bg': COLORS['primary'],
        'fg': COLORS['surface'],
        'activebackground': COLORS['primary_dark'],
        'activeforeground': COLORS['surface'],
        'font': FONT['button'],
        'relief': 'solid',
        'padx': 14,
        'pady': 7,
        'borderwidth': 1,
        'cursor': 'hand2',
    },
    'success': {
        'bg': COLORS['success'],
        'fg': COLORS['surface'],
        'activebackground': '#047857',
        'activeforeground': COLORS['surface'],
        'font': FONT['button'],
        'relief': 'solid',
        'padx': 14,
        'pady': 7,
        'borderwidth': 1,
        'cursor': 'hand2',
    },
    'danger': {
        'bg': COLORS['danger'],
        'fg': COLORS['surface'],
        'activebackground': '#b91c1c',
        'activeforeground': COLORS['surface'],
        'font': FONT['button'],
        'relief': 'solid',
        'padx': 14,
        'pady': 7,
        'borderwidth': 1,
        'cursor': 'hand2',
    },
    'warning': {
        'bg': COLORS['warning'],
        'fg': COLORS['surface'],
        'activebackground': '#b45309',
        'activeforeground': COLORS['surface'],
        'font': FONT['button'],
        'relief': 'solid',
        'padx': 14,
        'pady': 7,
        'borderwidth': 1,
        'cursor': 'hand2',
    },
    'secondary': {
        'bg': COLORS['secondary'],
        'fg': COLORS['surface'],
        'activebackground': '#334155',
        'activeforeground': COLORS['surface'],
        'font': FONT['button'],
        'relief': 'solid',
        'padx': 14,
        'pady': 7,
        'borderwidth': 1,
        'cursor': 'hand2',
    }
}

FRAME_STYLES = {
    'card': {
        'bg': COLORS['surface'],
        'relief': 'solid',
        'borderwidth': 1,
        'padx': LAYOUT['card_padx'],
        'pady': LAYOUT['card_pady']
    },
    'compact_card': {
        'bg': COLORS['surface'],
        'relief': 'solid',
        'borderwidth': 1,
        'padx': 10,
        'pady': 8
    }
}

TREEVIEW_STYLES = {
    'sales': {
        'background': COLORS['surface'],
        'foreground': COLORS['text_primary'],
        'selected_bg': COLORS['primary_light'],
        'selected_fg': COLORS['primary_dark'],
        'alternate_bg': COLORS['background'],
        'rowheight': 30,
        'font': FONT['body'],
        'padding': 6
    },
    'management': {
        'background': COLORS['surface'],
        'foreground': COLORS['text_primary'],
        'selected_bg': COLORS['primary_light'],
        'selected_fg': COLORS['text_primary'],
        'alternate_bg': COLORS['background'],
        'rowheight': 34,
        'font': FONT['body']
    },
    'report': {
        'background': COLORS['surface'],
        'foreground': COLORS['text_primary'],
        'selected_bg': COLORS['primary_light'],
        'selected_fg': COLORS['text_primary'],
        'alternate_bg': COLORS['background'],
        'rowheight': 34,
        'font': FONT['body']
    }
}

ENTRY_STYLES = {
    'normal': {
        'font': FONT['body'],
        'relief': 'solid',
        'borderwidth': 1,
        'bg': COLORS['surface']
    },
    'search': {
        'font': FONT['input'],
        'relief': 'solid',
        'borderwidth': 1,
        'bg': COLORS['background']
    }
}


def button_style(variant='primary', compact=False, **overrides):
    style = BUTTON_STYLES.get(variant, BUTTON_STYLES['primary']).copy()
    style.update(relief='flat', borderwidth=0)
    if compact:
        style.update({'padx': 10, 'pady': 5})
    style.update(overrides)
    return style


def card_style(compact=False, **overrides):
    key = 'compact_card' if compact else 'card'
    style = FRAME_STYLES[key].copy()
    style.update(relief='flat', borderwidth=0, highlightthickness=1,
                 highlightbackground=COLORS['border'])
    style.update(overrides)
    return style


def entry_style(kind='normal', **overrides):
    style = ENTRY_STYLES.get(kind, ENTRY_STYLES['normal']).copy()
    style.update(overrides)
    return style


def configure_treeview_style(style_name, preset='management'):
    tree_style = TREEVIEW_STYLES.get(preset, TREEVIEW_STYLES['management'])
    style = ttk.Style()
    style.configure(
        style_name,
        background=tree_style['background'],
        foreground=tree_style['foreground'],
        rowheight=tree_style['rowheight'],
        fieldbackground=tree_style['background'],
        font=tree_style['font'],
    )
    style.configure(
        f'{style_name}.Heading',
        background=COLORS['divider'],
        foreground=COLORS['text_primary'],
        relief='flat',
        font=FONT['label'],
    )
    style.map(
        style_name,
        background=[('selected', tree_style['selected_bg'])],
        foreground=[('selected', tree_style['selected_fg'])],
    )
    return style


def _coerce_sort_value(value, force_numeric=False, force_date=False):
    text = '' if value is None else str(value).strip()

    if force_date:
        for fmt in ('%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return 0, datetime.strptime(text, fmt).timestamp()
            except ValueError:
                pass

    cleaned = (
        text.replace('₫', '')
        .replace(',', '')
        .replace('%', '')
        .replace('+', '')
        .strip()
    )
    if force_numeric or cleaned.replace('.', '', 1).replace('-', '', 1).isdigit():
        try:
            return 0, float(cleaned)
        except ValueError:
            if force_numeric:
                return 0, 0

    return 1, text.casefold()


def enable_treeview_sorting(tree, numeric_columns=None, date_columns=None):
    """Enable click-to-sort behavior for a Treeview's visible columns."""
    numeric_columns = set(numeric_columns or [])
    date_columns = set(date_columns or [])
    sort_reverse = {}
    original_headings = {
        col: tree.heading(col, 'text') or col
        for col in tree['columns']
    }

    def sort_by_column(col):
        reverse = sort_reverse.get(col, False)
        rows = []
        for item_id in tree.get_children(''):
            value = tree.set(item_id, col)
            rows.append((
                _coerce_sort_value(
                    value,
                    force_numeric=col in numeric_columns,
                    force_date=col in date_columns,
                ),
                item_id,
            ))

        rows.sort(key=lambda item: item[0], reverse=reverse)
        for index, (_, item_id) in enumerate(rows):
            tree.move(item_id, '', index)

        for heading_col, heading_text in original_headings.items():
            suffix = ''
            if heading_col == col:
                suffix = ' ▼' if reverse else ' ▲'
            tree.heading(heading_col, text=f'{heading_text}{suffix}')

        sort_reverse[col] = not reverse

    for col in tree['columns']:
        tree.heading(
            col,
            text=original_headings[col],
            command=lambda selected_col=col: sort_by_column(selected_col),
        )

    return tree


def create_scrollable_frame(parent, bg=None):
    bg = bg or COLORS['background']
    outer = tk.Frame(parent, bg=bg)
    outer.rowconfigure(0, weight=1)
    outer.columnconfigure(0, weight=1)

    canvas = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0)
    scrollbar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
    inner = tk.Frame(canvas, bg=bg)
    inner_window = canvas.create_window((0, 0), window=inner, anchor='nw')

    def update_scroll_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox('all'))

    def fit_inner_width(event):
        canvas.itemconfigure(inner_window, width=event.width)

    inner.bind('<Configure>', update_scroll_region)
    canvas.bind('<Configure>', fit_inner_width)
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.grid(row=0, column=0, sticky='nsew')
    scrollbar.grid(row=0, column=1, sticky='ns')

    return outer, inner
