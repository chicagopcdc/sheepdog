from sheepdog.api import app, app_init
from os import environ
import os
import bin.confighelper as confighelper

APP_NAME = "sheepdog"


def load_json(file_name):
    return confighelper.load_json(file_name, APP_NAME)


conf_data = load_json("creds.json")
config = app.config

# ARBORIST deprecated, replaced by ARBORIST_URL
# ARBORIST_URL is initialized in app_init() directly
config["ARBORIST"] = "http://arborist-service/"

config["INDEX_CLIENT"] = {
    "host": os.environ.get("INDEX_CLIENT_HOST") or "http://indexd-service",
    "version": "v0",
    # The user should be "sheepdog", but for legacy reasons, we use "gdcapi" instead
    "auth": (
        (
            environ.get("INDEXD_USER", "gdcapi"),
            environ.get("INDEXD_PASS")
            or conf_data.get("indexd_password", "{{indexd_password}}"),
        )
    ),
}

config["PSQLGRAPH"] = {
    "host": conf_data.get("db_host", os.environ.get("PGHOST", "localhost")),
    "user": conf_data.get("db_username", os.environ.get("PGUSER", "sheepdog")),
    "password": conf_data.get("db_password", os.environ.get("PGPASSWORD", "sheepdog")),
    "database": conf_data.get("db_database", os.environ.get("PGDB", "sheepdog")),
}

config["FLASK_SECRET_KEY"] = conf_data.get("gdcapi_secret_key", "{{gdcapi_secret_key}}")
fence_username = conf_data.get(
    "fence_username", os.environ.get("FENCE_DB_USER", "fence")
)
fence_password = conf_data.get(
    "fence_password", os.environ.get("FENCE_DB_PASS", "fence")
)
fence_host = conf_data.get("fence_host", os.environ.get("FENCE_DB_HOST", "localhost"))
fence_database = conf_data.get(
    "fence_database", os.environ.get("FENCE_DB_DATABASE", "fence")
)
config["PSQL_USER_DB_CONNECTION"] = "postgresql://%s:%s@%s:5432/%s" % (
    fence_username,
    fence_password,
    fence_host,
    fence_database,
)

# Public-facing issuer URL: the `iss` claim Fence embeds in tokens and the URL
# authutils uses for JWT issuer validation.
_public_user_api = "https://%s/user" % conf_data.get(
    "hostname", os.environ.get("CONF_HOSTNAME", "localhost")
)

# USER_API may be overridden to an internal cluster URL (e.g.
# http://fence-service/user) so JWKS key fetches stay within the cluster
# network. When overridden it must differ from _public_user_api; OIDC_ISSUER
# always stays as the public URL so validate_jwt's issuer check still passes.
config["USER_API"] = os.environ.get("USER_API") or _public_user_api
config["OIDC_ISSUER"] = _public_user_api

config["AUTHZ_AUDIENCE"] = "gen3"  # for use by authutils

# Direct key fetching to USER_API rather than the token's iss claim, allowing
# an internal URL override to work even when iss carries the public URL.
config["FORCE_ISSUER"] = True
config["DICTIONARY_URL"] = os.environ.get(
    "DICTIONARY_URL",
    "https://s3.amazonaws.com/dictionary-artifacts/datadictionary/develop/schema.json",
)

app_init(app)
application = app
application.debug = os.environ.get("GEN3_DEBUG") == "True"
