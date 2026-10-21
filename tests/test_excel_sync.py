from openpyxl import load_workbook  # Đọc hoặc tạo workbook Excel.

from excel_sync import SYNCED_WORKBOOK, export_synced_workbook  # Đọc hoặc ghi workbook đồng bộ từ MySQL.


def test_synced_workbook_contains_current_database_data():
    path = export_synced_workbook()
    book = load_workbook(path, read_only=True, data_only=True)

    assert path == SYNCED_WORKBOOK
    assert {'Khach_hang', 'San_pham', 'Ton_kho', 'Ghi_chu'} <= set(book.sheetnames)
    assert book['Khach_hang'].max_row > 1
    assert book['San_pham'].max_row > 1
    assert book['Ton_kho'].max_row > 1

    adv_rows = [
        row for row in book['Ton_kho'].iter_rows(min_row=2, values_only=True)
        if row[1] == 'ADV 160'
    ]
    assert adv_rows
    assert any(row[5] == 10 for row in adv_rows)
