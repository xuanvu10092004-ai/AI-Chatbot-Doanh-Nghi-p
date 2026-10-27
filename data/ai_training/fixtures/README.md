# Synthetic Phase 3 fixture

`honda_chatbot_test.sql` is generated from the repository's small schema sample and synthetic rows. It does not read or copy `data/source/` or the live database.

The agent did **not** import it automatically. Import only after verifying that the target name is exactly `honda_chatbot_test`:

```powershell
$env:MYSQL_PWD = $env:ADMIN_DB_PASSWORD
Get-Content .\data\ai_training\fixtures\honda_chatbot_test.sql | & 'C:\xampp\mysql\bin\mysql.exe' -h 127.0.0.1 -P 3306 -u $env:ADMIN_DB_USER
Remove-Item Env:MYSQL_PWD
```

Create/configure the read-only account separately; never put its password in this SQL file:

```sql
CREATE USER IF NOT EXISTS 'chatbot_ro'@'localhost' IDENTIFIED BY '<secret-from-secret-manager>';
GRANT SELECT ON honda_chatbot_test.v_ai_products TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot_test.v_ai_inventory TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot_test.v_ai_customers TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot_test.v_ai_orders TO 'chatbot_ro'@'localhost';
GRANT SELECT ON honda_chatbot_test.v_ai_product_costs TO 'chatbot_ro'@'localhost';
GRANT EXECUTE ON FUNCTION honda_chatbot_test.fn_session_branch TO 'chatbot_ro'@'localhost';
```

Reset is limited to this explicitly named synthetic target. Do not point the command at `honda_chatbot`.
