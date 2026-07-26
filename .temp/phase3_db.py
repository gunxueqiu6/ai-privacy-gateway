path = r"G:\projects\ai数据隐私隔离\database.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the line with "CREATE INDEX IF NOT EXISTS idx_login_ip"
for i, line in enumerate(lines):
    if "CREATE INDEX IF NOT EXISTS idx_login_ip ON login_attempts" in line:
        # Insert new tables before the closing """)"""
        # Find the closing triple-quote after this line
        closing_idx = None
        for j in range(i + 1, min(i + 20, len(lines))):
            if '""")' in lines[j]:
                closing_idx = j
                break
        
        if closing_idx is None:
            print(f"Could not find closing triple-quote after line {i+1}")
            break

        new_tables = '''
                -- Phase 3: Multi-user and team tables
                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    license_id TEXT,
                    created_at TEXT NOT NULL,
                    settings TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'member',
                    api_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    UNIQUE(team_id, username)
                );

                CREATE INDEX IF NOT EXISTS idx_users_team ON users(team_id);
                CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
'''
        lines.insert(closing_idx, new_tables)
        print(f"Inserted team tables before line {closing_idx+1}")
        break

# Now add team_id column migrations
# Find the audit_log prev_hash migration block
for i, line in enumerate(lines):
    if 'logger.info("已为 audit_log 表添加 prev_hash 列")' in line or 'logger.info("Added prev_hash column to audit_log")' in line:
        migration_code = '''
            # Phase 3: Add team_id columns to existing tables
            cursor.execute("PRAGMA table_info(vault_mappings)")
            vm_cols = {row[1] for row in cursor.fetchall()}
            if "team_id" not in vm_cols:
                cursor.execute("ALTER TABLE vault_mappings ADD COLUMN team_id TEXT DEFAULT 'default'")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_team_session ON vault_mappings(team_id, session_id)")
                logger.info("Added team_id column to vault_mappings")

            cursor.execute("PRAGMA table_info(custom_keywords)")
            ck_cols = {row[1] for row in cursor.fetchall()}
            if "team_id" not in ck_cols:
                cursor.execute("ALTER TABLE custom_keywords ADD COLUMN team_id TEXT DEFAULT 'default'")
                logger.info("Added team_id column to custom_keywords")

            cursor.execute("PRAGMA table_info(stats)")
            st_cols = {row[1] for row in cursor.fetchall()}
            if "team_id" not in st_cols:
                cursor.execute("ALTER TABLE stats ADD COLUMN team_id TEXT DEFAULT 'default'")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_team_date ON stats(team_id, date)")
                logger.info("Added team_id column to stats")
'''
        lines.insert(i + 1, migration_code)
        print(f"Inserted team_id migrations after line {i+1}")
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("database.py updated with Phase 3 schema")
