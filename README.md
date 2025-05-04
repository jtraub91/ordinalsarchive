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
npm install
```

## DB Setup

1. Install Postgres

2. Create database and user

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE <dbname>;
CREATE USER <dbuser> WITH ENCRYPTED PASSWORD <dbpassword>;
ALTER DATABASE <dbname> OWNER TO <dbuser>;
```

## Environment Variables

The following environment variables can be specified

- `DJANGO_DEBUG` (default: False)
- `DJANGO_SECRET_KEY` (__required__)
- `DJANGO_ALLOWED_HOSTS` (__required__)
- `DJANGO_DB_NAME` (__required__)
- `DJANGO_DB_USER` (__required__)
- `DJANGO_DB_PASSWORD` (__required__)
- `DJANGO_DB_HOST` (default: 127.0.0.1)
- `DJANGO_DB_PORT` (default: 5432)
- `DJANGO_STATIC_URL` (default: /static/)
- `DJANGO_MEDIA_URL` (default: /media/)
- `DJANGO_LOG_LEVEL` (default: INFO)
- `DJANGO_S3_ACCESS_KEY` (default: None)
- `DJANGO_S3_SECRET_KEY` (default: None)
- `DJANGO_S3_BUCKET_NAME` (default: None)
- `DJANGO_S3_ENDPOINT_URL` (default: None)

## Static files

Static files include CSS, Javascript, images, and more.

Tailwind CSS can be built and output to ordinalsarchive/static/dist/tailwind.css with

```bash
npm run tailwind-build
```

Static files in ordinalsarchive/static and pages/static may be collected to the STATIC_ROOT directory with

```bash
python manage.py collectstatic
```

Static files can be deployed to netlify with

```bash
npm run deploy-static   # requires NETLIFY_AUTH_TOKEN env var to be set
```
