import os, sys, requests

os.chdir(r'c:\Users\hariv\Downloads\Plagiarism-Scan-main\Plagiarism-Scan-main\backend')

with open('.env') as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

url = os.environ['FLUXBASE_URL']
api_key = os.environ['FLUXBASE_API_KEY']
project_id = os.environ['FLUXBASE_PROJECT_ID']
headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

def run_sql(sql):
    resp = requests.post(url, json={'projectId': project_id, 'query': sql}, headers=headers, timeout=20)
    data = resp.json()
    if not data.get('success'):
        err = data.get('error', {})
        print(f"  WARN: {err.get('message', str(data))}")
    else:
        print(f"  OK: {data['executionInfo']}")
    return data

tables = {
    "users": """CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(255),
        role VARCHAR(10) DEFAULT 'user',
        is_superuser BOOLEAN DEFAULT FALSE,
        created_at DATETIME DEFAULT NOW(),
        updated_at DATETIME DEFAULT NOW()
    )""",
    "documents": """CREATE TABLE IF NOT EXISTS documents (
        id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        filename VARCHAR(500) NOT NULL,
        file_path VARCHAR(1000) NOT NULL,
        content_type VARCHAR(255),
        status VARCHAR(50) DEFAULT 'pending',
        extracted_text LONGTEXT,
        meta_data JSON,
        created_at DATETIME DEFAULT NOW(),
        updated_at DATETIME DEFAULT NOW()
    )""",
    "scans": """CREATE TABLE IF NOT EXISTS scans (
        id INT AUTO_INCREMENT PRIMARY KEY,
        document_id INT,
        initiated_by INT,
        status VARCHAR(50) DEFAULT 'queued',
        overall_score FLOAT,
        report_data JSON,
        progress INT DEFAULT 0,
        current_step VARCHAR(255),
        created_at DATETIME DEFAULT NOW(),
        completed_at DATETIME,
        updated_at DATETIME DEFAULT NOW()
    )""",
    "scan_matches": """CREATE TABLE IF NOT EXISTS scan_matches (
        id INT AUTO_INCREMENT PRIMARY KEY,
        scan_id INT,
        source_document_id INT,
        chunk_text LONGTEXT,
        matched_text LONGTEXT,
        similarity_score FLOAT,
        created_at DATETIME DEFAULT NOW()
    )""",
    "document_chunks": """CREATE TABLE IF NOT EXISTS document_chunks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        document_id INT,
        chunk_index INT,
        chunk_text LONGTEXT,
        created_at DATETIME DEFAULT NOW()
    )""",
}

for name, sql in tables.items():
    print(f'Creating table: {name}')
    run_sql(sql)

print('\nDone! Verifying tables exist...')
result = run_sql('SHOW TABLES;')
if result.get('success'):
    rows = result['result']['rows']
    print('Tables in Fluxbase:')
    for r in rows:
        print(f"  - {list(r.values())[0]}")
