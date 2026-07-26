path = r"G:\projects\ai数据隐私隔离\database.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the problematic area
# We need to fix: get_today_stats definition has no body, and new methods are inside it
# Find line numbers
get_today_stats_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("def get_today_stats"):
        get_today_stats_idx = i
        break

if get_today_stats_idx is None:
    print("Could not find get_today_stats")
    exit(1)

# Find the orphaned get_today_stats body (starts with "        today = datetime.now()...")
orphaned_body_start = None
orphaned_body_end = None
for i in range(get_today_stats_idx + 1, len(lines)):
    if "today = datetime.now().strftime" in lines[i] and lines[i].startswith("        today"):
        orphaned_body_start = i
        break

# Find where the orphaned body ends (before "db = Database()")
for i in range(len(lines) - 1, 0, -1):
    if lines[i].strip() == "db = Database()":
        orphaned_body_end = i
        break

if orphaned_body_start is None or orphaned_body_end is None:
    print(f"Could not find orphaned body: start={orphaned_body_start}, end={orphaned_body_end}")
    exit(1)

# Extract the orphaned body (the real get_today_stats body)
orphaned_body = lines[orphaned_body_start:orphaned_body_end]

# Now rebuild:
# 1. Lines before get_today_stats (inclusive)
# 2. The orphaned body of get_today_stats
# 3. Blank line
# 4. New methods (save_license through get_license_count) - from after get_today_stats line to before orphaned body
# 5. Orphaned body lines (we already moved these) - SKIP these
# 6. Rest of file from orphaned_body_end

# Lines for new methods: from get_today_stats_idx+1 to orphaned_body_start
new_methods = lines[get_today_stats_idx + 1:orphaned_body_start]

# Build new file
result = lines[:get_today_stats_idx + 1]  # up to and including get_today_stats line
result.extend(orphaned_body)  # add the body
result.append("\n")  # blank line separator
result.extend(new_methods)  # add new license methods
result.extend(lines[orphaned_body_end:])  # rest of file

with open(path, "w", encoding="utf-8") as f:
    f.writelines(result)

print(f"Fixed database.py: get_today_stats at line {get_today_stats_idx+1}, body from {orphaned_body_start+1} to {orphaned_body_end+1}")
