import init_db
from db import cursor


def test_targeted_extension_is_repeatable_and_preserves_business_data(monkeypatch):
    def counts():
        with cursor() as cur:
            cur.execute('SELECT (SELECT COUNT(*) FROM customer_profiles) AS customers,'
                        '(SELECT COUNT(*) FROM orders) AS orders,(SELECT SUM(quantity) FROM inventory) AS stock')
            return cur.fetchone()
    before=counts()
    monkeypatch.setattr('sys.argv',['init_db.py','--extension','16_chat_dialogue.sql'])
    assert init_db.main()==0
    assert init_db.main()==0
    assert counts()==before
