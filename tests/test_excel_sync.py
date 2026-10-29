"""Kiểm thử đồng bộ dữ liệu giữa cơ sở dữ liệu và workbook Excel."""

from openpyxl import load_workbook  # Đọc hoặc tạo workbook Excel.

from db import cursor, transaction
from excel_sync import SYNCED_WORKBOOK, export_synced_workbook, sync_after_commit  # Đọc hoặc ghi workbook đồng bộ từ MySQL.


def test_synced_workbook_contains_current_database_data(adv_inventory):
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
    book.close()

def test_committed_inventory_update_syncs_the_managed_workbook():
    # UPDATE không đổi số lượng nghiệp vụ, nhưng vẫn đi qua trigger/outbox.
    with cursor() as cur:
        cur.execute('UPDATE inventory SET quantity=quantity WHERE variant_id=33 AND branch_id=1')
    result = sync_after_commit()
    assert result['status'] == 'completed'
    book = load_workbook(SYNCED_WORKBOOK, read_only=True, data_only=True)
    try:
        row = next(row for row in book['Ton_kho'].iter_rows(min_row=2, values_only=True) if row[0] == 'SP033')
        assert tuple(row[3:7]) == (10, 8, 5, 23)
        assert {'Khach_hang', 'San_pham', 'Ton_kho', 'Ghi_chu'} <= set(book.sheetnames)
    finally:
        book.close()


def test_nested_transaction_defers_excel_sync_until_outer_commit():
    # Hai chi nhanh cung phat sinh outbox; callback chi chay sau commit ngoai cung.
    with transaction():
        with cursor() as cur:
            cur.execute('UPDATE inventory SET quantity=quantity WHERE variant_id=33 AND branch_id IN (1, 2)')
        result = sync_after_commit()
        assert result['status'] == 'pending'

    book = load_workbook(SYNCED_WORKBOOK, read_only=True, data_only=True)
    try:
        row = next(row for row in book['Ton_kho'].iter_rows(min_row=2, values_only=True) if row[0] == 'SP033')
        assert tuple(row[3:7]) == (10, 8, 5, 23)
    finally:
        book.close()
