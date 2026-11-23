import os
import json
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/".env")
SECRET_KEY=os.getenv("SECRET_KEY","dev-only-change-me")
DEBUG=os.getenv("DEBUG","True").lower()=="true"
ALLOWED_HOSTS=os.getenv("ALLOWED_HOSTS","127.0.0.1,localhost").split(",")
if not DEBUG and SECRET_KEY=="dev-only-change-me":
 raise RuntimeError("Set a private SECRET_KEY before running with DEBUG=False")
INSTALLED_APPS=["django.contrib.admin","django.contrib.auth","django.contrib.contenttypes","django.contrib.sessions","django.contrib.messages","django.contrib.staticfiles","rest_framework","apps.core","apps.operations","apps.finance","apps.procurement","apps.insights"]
MIDDLEWARE=["django.middleware.security.SecurityMiddleware","whitenoise.middleware.WhiteNoiseMiddleware","django.contrib.sessions.middleware.SessionMiddleware","django.middleware.common.CommonMiddleware","django.middleware.csrf.CsrfViewMiddleware","django.contrib.auth.middleware.AuthenticationMiddleware","django.contrib.messages.middleware.MessageMiddleware","django.middleware.clickjacking.XFrameOptionsMiddleware"]
ROOT_URLCONF="config.urls"
TEMPLATES=[{"BACKEND":"django.template.backends.django.DjangoTemplates","DIRS":[BASE_DIR/"templates"],"APP_DIRS":True,"OPTIONS":{"context_processors":["django.template.context_processors.request","django.contrib.auth.context_processors.auth","django.contrib.messages.context_processors.messages","apps.core.context_processors.workspace"]}}]
WSGI_APPLICATION="config.wsgi.application"
DATABASES={"default":{"ENGINE":"django.db.backends.sqlite3","NAME":BASE_DIR/"db.sqlite3"}}
if os.getenv("DATABASE_URL"):
 import dj_database_url; DATABASES["default"]=dj_database_url.parse(os.environ["DATABASE_URL"],conn_max_age=600)
AUTH_PASSWORD_VALIDATORS=[{"NAME":"django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},{"NAME":"django.contrib.auth.password_validation.MinimumLengthValidator"},{"NAME":"django.contrib.auth.password_validation.CommonPasswordValidator"},{"NAME":"django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE="en-us"; TIME_ZONE="Asia/Kolkata"; USE_I18N=True; USE_TZ=True
STATIC_URL="static/"; STATICFILES_DIRS=[BASE_DIR/"static"]; STATIC_ROOT=BASE_DIR/"staticfiles"; MEDIA_URL="/private-media/"; MEDIA_ROOT=BASE_DIR/"media"
DEFAULT_AUTO_FIELD="django.db.models.BigAutoField"
LOGIN_URL="login"; LOGIN_REDIRECT_URL="dashboard"; LOGOUT_REDIRECT_URL="login"
STORAGES={"default":{"BACKEND":"django.core.files.storage.FileSystemStorage"},"staticfiles":{"BACKEND":"whitenoise.storage.CompressedManifestStaticFilesStorage"}}
if os.getenv("USE_S3","False").lower()=="true":
 STORAGES["default"]={"BACKEND":"storages.backends.s3boto3.S3Boto3Storage"}
 AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID"); AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY"); AWS_STORAGE_BUCKET_NAME=os.getenv("AWS_STORAGE_BUCKET_NAME"); AWS_S3_ENDPOINT_URL=os.getenv("AWS_S3_ENDPOINT_URL") or None; AWS_S3_REGION_NAME=os.getenv("AWS_S3_REGION_NAME","us-east-1"); AWS_S3_ADDRESSING_STYLE=os.getenv("AWS_S3_ADDRESSING_STYLE","auto"); AWS_DEFAULT_ACL=None; AWS_QUERYSTRING_AUTH=True; AWS_S3_FILE_OVERWRITE=False; AWS_S3_OBJECT_PARAMETERS={"CacheControl":"max-age=3600"}
 if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not AWS_STORAGE_BUCKET_NAME:
  raise RuntimeError("USE_S3=True requires AWS access key, secret and bucket name")
CELERY_BROKER_URL=os.getenv("REDIS_URL","redis://127.0.0.1:6379/0")
AI_PROVIDER=os.getenv("AI_PROVIDER","demo").lower()
CELERY_TASK_ALWAYS_EAGER=os.getenv("CELERY_TASK_ALWAYS_EAGER",str(DEBUG)).lower()=="true"
CELERY_TASK_EAGER_PROPAGATES=True
CELERY_BEAT_SCHEDULE={"scan-pipeline-anomalies":{"task":"apps.operations.tasks.scan_all_organizations","schedule":300.0}}
RECOVERY_ADAPTERS={"demo":"apps.operations.recovery_adapters.demo_retry"}
RECOVERY_ADAPTERS.update(json.loads(os.getenv("RECOVERY_ADAPTERS_JSON") or "{}"))
DATA_UPLOAD_MAX_MEMORY_SIZE=55*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE=10*1024*1024
SESSION_COOKIE_HTTPONLY=True
CSRF_COOKIE_HTTPONLY=False
X_FRAME_OPTIONS="DENY"
SECURE_CONTENT_TYPE_NOSNIFF=True
if not DEBUG:
 SESSION_COOKIE_SECURE=True; CSRF_COOKIE_SECURE=True; SECURE_SSL_REDIRECT=os.getenv("SECURE_SSL_REDIRECT","True").lower()=="true"
 SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO","https")
 SECURE_HSTS_SECONDS=31536000; SECURE_HSTS_INCLUDE_SUBDOMAINS=True; SECURE_HSTS_PRELOAD=True
CSRF_TRUSTED_ORIGINS=[origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS","").split(",") if origin.strip()]
EMAIL_BACKEND=os.getenv("EMAIL_BACKEND","django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend")
FILE_UPLOAD_PERMISSIONS=0o640
