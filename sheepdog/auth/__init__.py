"""
This module will depend on the downstream authutils dependency.

eg:
``pip install git+https://git@github.com/NCI-GDC/authutils.git@1.2.3#egg=authutils``
or
``pip install git+https://git@github.com/uc-cdis/authutils.git@1.2.3#egg=authutils``
"""

import functools

from authutils.user import current_user
from authutils.token.validate import current_token
from cachelib import SimpleCache
from cdislogging import get_logger
import flask
import jwt
import time

from sheepdog.errors import AuthNError, AuthZError
from sheepdog.globals import ROLES


logger = get_logger(__name__)
CACHE_SECONDS = 1
AUTHZ_CACHE = SimpleCache(default_timeout=CACHE_SECONDS)
try:
    from authutils.token.validate import validate_request
except ImportError:
    logger.warning(
        "Unable to import authutils validate_request. Sheepdog will error if config AUTH_SUBMISSION_LIST is set to "
        "True (note that it is True by default) "
    )


def get_jwt_from_header():
    jwt_token = None
    auth_header = flask.request.headers.get("Authorization")
    if auth_header:
        items = auth_header.split(" ")
        if len(items) == 2 and items[0].lower() == "bearer":
            jwt_token = items[1]
    if not jwt_token:
        raise AuthNError("Didn't receive JWT correctly")
    return jwt_token


def check_if_jwt_close_to_expiry(jwt_token):
    """Check if a JWT is close to expiry based on `CACHE_SECONDS`."""
    try:
        # decode the JWT to check its expiration, use verify_signature=False to skip signature verification
        decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})

        # The token is considered "close to expiry" if it expires within the next CACHE_SECONDS seconds.
        return decoded_token.get("exp", 0) < time.time() + CACHE_SECONDS
    except jwt.exceptions.DecodeError as e:
        logger.error(f"Unable to decode jwt token: {e}")
        raise AuthNError("Didn't receive JWT correctly")


def authorize_for_project(*required_roles):
    """
    Wrap a function to allow access to the handler iff the user has at least
    one of the roles requested on the given project.
    """

    def wrapper(func):
        @functools.wraps(func)
        def authorize_and_call(program, project, *args, **kwargs):
            resource = "/programs/{}/projects/{}".format(program, project)
            jwt_token = get_jwt_from_header()
            authz = flask.current_app.auth.auth_request(
                jwt=jwt_token,
                service="sheepdog",
                methods=required_roles,
                resources=[resource],
            )
            if not authz:
                raise AuthZError("user is unauthorized")
            return func(program, project, *args, **kwargs)

        return authorize_and_call

    return wrapper


def require_sheepdog_program_admin(func):
    """
    Wrap a function to allow access to the handler if the user has access to
    the resource /services/sheepdog/submission/program (Sheepdog program admin)
    """

    @functools.wraps(func)
    def authorize_and_call(*args, **kwargs):
        jwt_token = get_jwt_from_header()
        authz = flask.current_app.auth.auth_request(
            jwt=jwt_token,
            service="sheepdog",
            methods="*",
            resources=["/services/sheepdog/submission/program"],
        )
        if not authz:
            raise AuthZError("Unauthorized: User must be Sheepdog program admin")
        return func(*args, **kwargs)

    return authorize_and_call


def require_sheepdog_project_admin(func):
    """
    Wrap a function to allow access to the handler if the user has access to
    the resource /services/sheepdog/submission/project (Sheepdog project admin)
    """

    @functools.wraps(func)
    def authorize_and_call(*args, **kwargs):
        jwt_token = get_jwt_from_header()
        authz = flask.current_app.auth.auth_request(
            jwt=jwt_token,
            service="sheepdog",
            methods="*",
            resources=["/services/sheepdog/submission/project"],
        )
        if not authz:
            raise AuthZError("Unauthorized: User must be Sheepdog project admin")
        return func(*args, **kwargs)

    return authorize_and_call


def authorize(program, project, roles, resource_list=None):
    resource = "/programs/{}/projects/{}".format(program, project)

    resources = []
    if resource_list:
        for res in resource_list:
            resources.append(resource + res)
    else:
        resources = [resource]

    jwt_token = get_jwt_from_header()
    jwt_close_to_expiry = check_if_jwt_close_to_expiry(jwt_token)
    cache_key = f"{jwt_token}_{roles}_{resource}"
    authz = None

    if not jwt_close_to_expiry and AUTHZ_CACHE.has(cache_key):
        authz = AUTHZ_CACHE.get(cache_key)
    else:
        authz = flask.current_app.auth.auth_request(
            jwt=jwt_token, service="sheepdog", methods=roles, resources=[resource]
        )
        AUTHZ_CACHE.set(cache_key, authz)

    if not authz:
        raise AuthZError("user is unauthorized")


def create_resource(program, project=None, data=None):
    resource = "/programs/{}".format(program)

    if project:
        resource += "/projects/{}".format(project)

    if isinstance(data, list):
        for d in data:
            get_and_create_resource_values(resource, d)
    else:
        get_and_create_resource_values(resource, data)


def get_and_create_resource_values(resource, data):
    stop_node = flask.current_app.node_authz_entity
    person_node = flask.current_app.subject_entity
    if data and data["type"] == person_node.label:
        resource += "/persons/{}".format(data["submitter_id"])
    elif data and data["type"] == stop_node.label:
        person = None
        if isinstance(data["persons"], list):
            person = data["persons"][0]
        else:
            person = data["persons"]
        resource += "/persons/{}/subjects/{}".format(person["submitter_id"], data["submitter_id"])
    logger.warn(resource)


    logger.info("Creating arborist resource {}".format(resource))

    json_data = {
        "name": resource,
        "description": "Created by sheepdog",  # TODO use authz provider field
    }
    resp = flask.current_app.auth.create_resource(
        parent_path="", resource_json=json_data, create_parents=True
    )
    if resp and resp.get("error"):
        logger.error(
            "Unable to create resource: code {} - {}".format(
                resp.error.code, resp.error.message
            )
        )


def check_resource_access(program, project, nodes):
    subject_submitter_ids = []
    stop_node = flask.current_app.node_authz_entity_name

    for node in nodes:
        if node.label == stop_node:
            subject_submitter_ids.append({"id": node.node_id, "submitter_id": node.props.get("submitter_id", None)})
        else:
            for link in node._pg_links:
                tmp_dads = getattr(node, link, None)
                if tmp_dads:
                    tmp_dad = tmp_dads[0]
                    nodeType = link
                    path_tmp = nodeType
                    tmp = node._pg_links[link]["dst_type"]
                    while tmp.label != stop_node and tmp.label != "program":
                        # assuming ony one parents
                        nodeType = list(tmp._pg_links.keys())[0]
                        path_tmp = path_tmp + "." + nodeType
                        tmp = tmp._pg_links[nodeType]["dst_type"]
                        # TODO double check this with deeper relationship > 2 nodes under project
                        tmp_dad = getattr(tmp_dad, nodeType)[0]

                    if tmp.label == stop_node:
                        subject_submitter_ids.append({"id": tmp_dad.node_id, "submitter_id": tmp_dad.props.get("submitter_id", None)})
                    else:
                        logger.warn("resource not found " + node.label)
                        logger.warn(node)

    try:
        resources = [
                "/{}s/{}".format(stop_node, node["submitter_id"])
                for node in subject_submitter_ids
            ]
        authorize(program, project, [ROLES["READ"]], resources)
    except AuthZError:
        return "You do not have read permission on project {} for one or more of the subjects requested"


# TEST BUT YOU NEED TO ADD ACTUAL ID LIST NOT ONLY THE ONE LISTED IN THE DB
def get_authorized_ids(program, project):
    try:
        mapping = flask.current_app.auth.auth_mapping(current_user.username)
    except AuthZError as e:
        logger.warn(
            "Unable to retrieve auth mapping for user `{}`: {}".format(current_user.username, e)
        )
        mapping = {}

    base_resource_path = "/programs/{}/projects/{}".format(program, project)
    result = [resource_path for resource_path, permissions in mapping.items() if base_resource_path in resource_path]
    ids = []

    for path in result:
        parts = path.strip("/").split("/")
        if path != "/" and parts[0] != "programs":
            continue

        if len(parts) > 6 or (len(parts) > 2 and parts[2] != "projects") or (len(parts) > 4 and (flask.current_app.node_authz_entity_name is None or flask.current_app.node_authz_entity is None or parts[4] != (flask.current_app.node_authz_entity_name + "s"))):
            continue

        if len(parts) <  6:
            return(None)
        else:
            ids.append(parts[5])

    return(ids)

