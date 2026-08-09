# tests/test_google_sheets.py
"""Тесты google_sheets.py. Сеть не используется: gspread и Credentials подменяются.

Запуск: python -m unittest discover -s tests -t .
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# config.py падает без этих переменных, а тестам нужен только импорт модуля
os.environ.setdefault("VK_TOKEN", "test-token")
os.environ.setdefault("VK_GROUP_ID", "1")

import google_sheets as gs


class FakeWorksheet:
    """Лист Google Sheets. row_values/col_values обрезают пустые ячейки справа –
    как это делает настоящий Sheets API."""

    def __init__(self, rows=None):
        self.rows = [list(r) for r in (rows or [])]
        self.updated_cells = []
        self.batches = []
        self.calls = 0

    def _trim(self, values):
        values = list(values)
        while values and values[-1] in ('', None):
            values.pop()
        return values

    def col_values(self, n):
        self.calls += 1
        return self._trim([r[n - 1] if len(r) >= n else '' for r in self.rows])

    def row_values(self, n):
        self.calls += 1
        return self._trim(self.rows[n - 1])

    def update_cell(self, row, col, value):
        self.calls += 1
        while len(self.rows[row - 1]) < col:
            self.rows[row - 1].append('')
        self.rows[row - 1][col - 1] = value
        self.updated_cells.append((row, col, value))

    def append_row(self, values, **kwargs):
        self.calls += 1
        self.rows.append(list(values))
        end = len(self.rows)
        return {'updates': {'updatedRange': f"'Гости'!A{end}:N{end}"}}

    def batch_update(self, data, **kwargs):
        self.calls += 1
        self.batches.append(data)


class GoogleSheetsTestCase(unittest.TestCase):
    """Общая обвязка: подменяем лист и сбрасываем кэши между тестами."""

    def setUp(self):
        gs._client = None
        gs._spreadsheet = None
        gs._sheet = None
        gs._vk_cache.clear()
        self.sheet = FakeWorksheet()
        patcher = mock.patch.object(gs, 'get_sheet', return_value=self.sheet)
        self.addCleanup(patcher.stop)
        patcher.start()


class TestCredentials(unittest.TestCase):
    def setUp(self):
        gs._client = None
        gs._spreadsheet = None
        gs._sheet = None

    def test_import_does_not_connect(self):
        """Импорт модуля не должен ходить в сеть – иначе бот не стартует
        при сбое Google или отсутствии кредов."""
        self.assertIsNone(gs._client)
        self.assertIsNone(gs._sheet)

    def test_json_string_in_env(self):
        payload = '{"type": "service_account", "project_id": "x"}'
        with mock.patch.dict(os.environ, {"GOOGLE_CREDS_JSON": payload}), \
             mock.patch.object(gs, 'Credentials') as creds:
            gs._load_credentials()
        creds.from_service_account_info.assert_called_once_with(
            {"type": "service_account", "project_id": "x"}, scopes=gs.SCOPES)
        creds.from_service_account_file.assert_not_called()

    def test_file_path_in_env(self):
        with mock.patch.dict(os.environ, {"GOOGLE_CREDS_JSON": r"C:\creds\sa.json"}), \
             mock.patch.object(gs, 'Credentials') as creds:
            gs._load_credentials()
        creds.from_service_account_file.assert_called_once_with(
            r"C:\creds\sa.json", scopes=gs.SCOPES)

    def test_falls_back_to_cred_file(self):
        env = {k: v for k, v in os.environ.items() if k != "GOOGLE_CREDS_JSON"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(gs.os.path, 'isfile', return_value=True), \
             mock.patch.object(gs, 'Credentials') as creds:
            gs._load_credentials()
        creds.from_service_account_file.assert_called_once_with(
            gs.CRED_FILE, scopes=gs.SCOPES)

    def test_no_credentials_raises_explicit_error(self):
        """Раньше creds оставались None и падало внутри gspread с невнятным
        'NoneType' object has no attribute '__module__'."""
        env = {k: v for k, v in os.environ.items() if k != "GOOGLE_CREDS_JSON"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(gs.os.path, 'isfile', return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                gs._load_credentials()
        self.assertIn("GOOGLE_CREDS_JSON", str(ctx.exception))

    def test_client_is_built_once(self):
        with mock.patch.object(gs, '_load_credentials', return_value='creds'), \
             mock.patch.object(gs.gspread, 'authorize', return_value='client') as auth:
            self.assertEqual(gs.get_client(), 'client')
            self.assertEqual(gs.get_client(), 'client')
        auth.assert_called_once_with('creds')

    def test_today_master_reuses_shared_client(self):
        """Раньше на каждый вызов создавался новый клиент и заново открывалась книга."""
        master = mock.Mock()
        master.get_all_records.return_value = []
        book = mock.Mock()
        book.worksheet.return_value = master
        with mock.patch.object(gs, 'get_client') as client:
            client.return_value.open_by_url.return_value = book
            gs.get_today_master()
            gs.get_today_master()
            client.return_value.open_by_url.assert_called_once_with(gs.SHEET_URL)


class TestEnsureGuestInSheet(GoogleSheetsTestCase):
    def test_restores_phone_and_birth_on_trimmed_row(self):
        """Регрессия: row_values обрезает пустой хвост, и обращение к
        current_row[2] роняло функцию с IndexError – ровно в том сценарии,
        ради которого она написана."""
        self.sheet.rows = [['12345', 'Иван', '', '']]
        guest = (12345, 'Иван', '79161234567', '15.05.1990', 'now',
                 0, 1, 'active', 'now', 3, '', '', 0, 0)

        gs.ensure_guest_in_sheet(12345, guest)

        self.assertEqual(self.sheet.updated_cells,
                         [(1, 3, '79161234567'), (1, 4, '15.05.1990')])

    def test_keeps_existing_values(self):
        self.sheet.rows = [['12345', 'Иван', '79990000000', '01.01.2000']]
        guest = (12345, 'Иван', '79161234567', '15.05.1990', 'now',
                 0, 1, 'active', 'now', 3, '', '', 0, 0)

        gs.ensure_guest_in_sheet(12345, guest)

        self.assertEqual(self.sheet.updated_cells, [])

    def test_restores_only_missing_birth(self):
        self.sheet.rows = [['12345', 'Иван', '79990000000', '']]
        guest = (12345, 'Иван', '79161234567', '15.05.1990', 'now',
                 0, 1, 'active', 'now', 3, '', '', 0, 0)

        gs.ensure_guest_in_sheet(12345, guest)

        self.assertEqual(self.sheet.updated_cells, [(1, 4, '15.05.1990')])

    def test_appends_row_when_guest_missing(self):
        guest = (777, 'Пётр', '79161234567', '', 'создан', 5, 3, 'active',
                 'обновлён', 3, '', '', 2, 0)

        gs.ensure_guest_in_sheet(777, guest)

        self.assertEqual(len(self.sheet.rows), 1)
        self.assertEqual(self.sheet.rows[0][:4], ['777', 'Пётр', '79161234567', ''])


if __name__ == '__main__':
    unittest.main()
