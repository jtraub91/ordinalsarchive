# ordinalsarchive

## Quick Installation

```bash
git clone https://github.com/jtraub91/ordinalsarchive
cd ordinalsarchive
python3 -m venv venv
. venv/bin/activate
python -m pip install -U pip poetry
poetry install
pre-commit install
```

## DB Setup

1. Install Postgres 17

2. Create database and user

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE <dbname>;
CREATE USER <dbuser> WITH ENCRYPTED PASSWORD <dbpassword>;
ALTER DATABASE <dbname> OWNER TO <dbuser>;
```
