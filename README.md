# Digital Evidence Integrity System Evidence Vault
### AI-Powered Digital Forensic Evidence Management System

Digital Evidence Integrity System Evidence Vault is a production-grade digital forensic evidence custody management platform designed to securely ingest, encrypt, verify, track, and report on electronic evidence. It guarantees evidence integrity using strict cryptographic SHA-256 hashing and AES-256 file encryption, backed by a robust Chain of Custody ledger.

---

## 🛡️ Technical Overview

* **Backend:** Python Flask with Blueprint Modular Architecture
* **Database Management:** Flask-SQLAlchemy (ORM) supporting MySQL
* **Cryptography Core:** AES-256 CBC Mode File Encryption via `pycryptodome` & Streaming SHA-256 Verification Hashing
* **Access Control:** Role-Based Access Control (RBAC) with `@role_required` decorator supporting Admin, Investigator, and Auditor roles
* **Reporting:** Dynamically generated PDF analysis reports via `ReportLab` incorporating live metadata scans & custom QR verification codes
* **Interface:** Cyber Security dark theme layout leveraging Bootstrap 5, FontAwesome, Custom main.js AJAX interactions, and Chart.js analytics

---

## 🚀 Installation & Setup Guide

### 1. Requirements & Dependencies
Make sure you have **Python 3.10+** installed. Install the system requirements using `pip`:

```bash
# Set up virtual environment
python -m venv venv
venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Environment Configurations
Rename `.env.example` to `.env` and configure appropriate keys:

```ini
FLASK_APP=run.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=enter-any-secure-random-phrase-here

# Choose Database Target
# For MySQL: mysql+pymysql://username:password@localhost:3306/chainproof_db
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/chainproof_db

# AES-256 Encryption key (must be secure string)
ENCRYPTION_KEY=my-super-secure-32-byte-aes-key
```

### 3. Database Inception
On launch, the system automatically builds the tables if they don't exist and seeds default role entities as well as demo accounts.

To manually perform migrations (optional):
```bash
flask db init
flask db migrate -m "Initial forensic schema"
flask db upgrade
```

### 4. Running the Development Node
To run the server locally:
```bash
python run.py
```
Visit `http://127.0.0.1:5000` in your web browser.

---

## 👥 Seeded Default Accounts

The system automatically seeds the following staff accounts for immediate testing:

| Username | Password | Role Designation | Permissions |
|---|---|---|---|
| `admin` | `admin123` | **System Administrator** | Full access to users, audit logs, tampering alerts, cases, evidence, custody transfer |
| `investigator` | `investigator123` | **Forensic Investigator** | Case CRUD, Evidence uploads & downloads, Custody transfer, Report generation |
| `auditor` | `auditor123` | **Forensic Auditor** | Read-only access to cases, evidence detail, custody timeline, audit logs |

---

## 🏛️ Database Architecture & Schema (14 Tables)

Refer to [schema.sql](file:///c:/Users/DEEPAK PRAJAPATI/Downloads/chainproof/database/schema.sql) for raw MySQL commands.

```
+---------------+      +-------------------+      +---------------------+
|     roles     |      |       users       |      |     user_roles      |
+---------------+      +-------------------+      +---------------------+
| id (PK)       |      | id (PK)           |      | user_id (FK->users) |
| name (Unique) |      | username (Unique) |      | role_id (FK->roles) |
| description   |      | email (Unique)    |      +---------------------+
+---------------+      | password_hash     |
                       | fullname          |
                       | is_active         |
                       | failed_attempts   |
                       | locked_until      |
                       +-------------------+
```

### Table Descriptions:
* **users & roles:** Manage staff identity and their RBAC status.
* **cases:** Case file parameters containing lead investigator and status (Open, Active, Closed, Archived).
* **case_evidence:** Junction table linking one Case to multiple Evidence items.
* **evidence:** Base evidence records. Stores original filename, category (Image, Video, Audio, Document, Malware, Network, Mobile), upload date, sealed SHA-256 hash, and random UUID stored file name.
* **evidence_hashes:** Verification registry logging every manual or automated integrity verification pass, tracking verifier, status, and calculated hash.
* **evidence_metadata:** Tag-value metadata pairs extracted dynamically from files on upload.
* **custody_records:** Handoff logs documenting transfer of custody. Tracks "From", "To", and Remarks.
* **audit_logs:** System-wide security logs recording logins, file downloads, edits, PDF generation, and IP/browser user agents.
* **reports:** Tracks generated case PDF files.
* **notifications:** Live feed for role-based notifications.
* **tamper_alerts:** Triggered when verification fails.

---

## 🛡️ Security Implementation Details

### Cryptographic Evidence Integrity
When an evidence file is ingested, the system reads its bytes in chunks and calculates a **SHA-256 hash** of the raw file. This hash represents the "Forensic Seal" and is stored permanently in the database.

### AES-256 File System Encryption
Immediately after hashing, the file is encrypted using **AES-256-CBC** via the PyCryptodome library. A 16-byte random Initialization Vector (IV) is generated for each file and prepended to the encrypted ciphertext. The raw file is instantly removed from temporary storage. The encrypted file is saved in the `app/encrypted/` directory.

### Recalculation & Tamper Verification
During verification:
1. The encrypted file is read.
2. The IV is extracted from the first 16 bytes.
3. The content is decrypted in memory.
4. The decrypted content's SHA-256 hash is calculated.
5. The computed hash is compared with the original hash stored in the DB.
6. A mismatch instantly marks the file as **Tampered**, issues a **TamperAlert** in the admin console, log entries in the **AuditLog**, and posts a high-priority alert notification.

---

## 📡 API Endpoints Directory

### Authentication (`/auth`)
* `GET/POST /auth/register`: Create a new staff account
* `GET/POST /auth/login`: Authenticate staff (locks account for 10 minutes on 5 failures)
* `GET /auth/logout`: End session and write audit log
* `GET/POST /auth/forgot-password`: Password reset request simulation

### Dashboard (`/`)
* `GET /dashboard`: Command center metrics and recent events
* `GET /dashboard/chart-data`: Fetch JSON dataset for Chart.js analytics

### Cases (`/cases`)
* `GET /cases/`: View cases list
* `GET/POST /cases/create`: Initialize new case
* `GET /cases/<id>`: Open case folder & view linked evidence
* `GET/POST /cases/<id>/edit`: Edit case meta
* `POST /cases/<id>/delete`: Delete case (Admin only)

### Evidence (`/evidence`)
* `GET /evidence/`: Ingested files listing with search/filter parameters
* `GET/POST /evidence/upload`: Upload file, encrypt it, scan metadata
* `GET /evidence/<id>`: Open evidence analysis board
* `POST /evidence/<id>/verify`: Recalculate hash and verify integrity
* `GET /evidence/<id>/download`: Decrypt on-the-fly and download evidence
* `GET /evidence/verify/<hash_val>`: Public QR verification portal

### Custody (`/custody`)
* `GET /custody/history/<id>`: Read timeline of custody records
* `GET/POST /custody/transfer/<id>`: Transfer forensic custody to another examiner

### Reports (`/reports`)
* `GET /reports/`: Generated PDF list
* `POST /reports/generate/<case_id>`: Compile case records to PDF
* `GET /reports/download/<id>`: Download PDF file

---

## 🏗️ Production Deployment Guidelines

### Windows Deployment (XAMPP + WSGI)
1. Install **XAMPP** on Windows.
2. Install Python and libraries globally or inside a virtual env.
3. Install **Apache `mod_wsgi`** module via pip: `pip install mod_wsgi`.
4. Run `mod_wsgi-express module-config` to get load config strings.
5. Paste load config strings inside XAMPP `apache/conf/httpd.conf`.
6. Add VirtualHost configuration pointing to `run.py` WSGI handler:
   ```apache
   <VirtualHost *:80>
       ServerName deis-vault.local
       WSGIDaemonProcess deis threads=5 python-home=C:/path/to/venv
       WSGIProcessGroup deis
       WSGIScriptAlias / C:/Users/DEEPAK PRAJAPATI/Desktop/deis/run.wsgi
       
       <Directory "C:/Users/DEEPAK PRAJAPATI/Desktop/deis">
           Require all granted
       </Directory>
   </VirtualHost>
   ```

7. Map `deis-vault.local` to `127.0.0.1` in `C:\Windows\System32\drivers\etc\hosts`.
8. Start Apache service from XAMPP Control Panel.
