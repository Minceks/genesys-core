from agent.user_allowance import account_context
import logging
import hmac
import os
import time
import uuid

from dotenv import load_dotenv
from flask import (
    Flask,
    g,
    jsonify,
    request,
    send_from_directory,
)
from flask_cors import CORS
from agent.logging_config import configure_logging, request_id_context
from agent.config import load_settings
from agent.orchestrator import run_agent, classify_request_type
from agent.jobs import JobManager, saved_build_retry
from agent import user_auth
from agent.preview_proxy import publish_preview
from agent.verified_preview import verified_preview, restore_verified
from agent.usage_limits import UsageLimiter, UsageLimited
from agent.tools import list_files, read_file, write_file
from agent.daytona_workspace import get_workspace
from agent.promotion import (
    sign_verified_checkpoint,
    verify_checkpoint_promotion_token,
)


# ============================================================
# ENVIRONMENT
# ============================================================

PROJECT_ROOT = os.path.dirname(
    os.path.abspath(__file__)
)

load_dotenv(
    os.path.join(
        PROJECT_ROOT,
        ".env",
    )
)

configure_logging()

settings = load_settings()

logger = logging.getLogger(__name__)

if os.getenv('SENTRY_DSN'):
    import sentry_sdk
    # Prompts and generated source stay out of reports.
    sentry_sdk.init(dsn=os.environ['SENTRY_DSN'], send_default_pii=False, include_local_variables=False)

# The account should not lose a build allowance to these. Tokens the build spent
# still count against the daily token allowance.
PLATFORM_FAILURES = {'agent_timeout', 'ai_request', 'workspace_unavailable', 'version_backup', 'planning'}
usage_limiter = UsageLimiter()


def reserve_build(prompt):
    from agent.builder_modes import parse_mode
    mode, plain_prompt = parse_mode(str(prompt))
    if mode in {'plan', 'discuss'} or (mode != 'build' and classify_request_type(plain_prompt) == 'chat'):
        return None
    return usage_limiter.reserve(getattr(g, 'user', {}).get('id', 'legacy-api'))


def limit_response(error):
    logger.warning('build_request_limited reason=%s retry_after=%s', error, error.retry_after)
    return jsonify(status='error', message=str(error), retryAfter=error.retry_after), 429, {'Retry-After': str(error.retry_after)}


# ============================================================
# FLASK APP
# ============================================================

app = Flask(
    __name__
)

CORS(
    app,
    resources={
        r"/*": {
            "origins": [
                origin.strip()
                for origin in settings.cors_origins.split(",")
                if origin.strip()
            ],
            "expose_headers": ["X-Request-ID"],
            "allow_headers": [
                "Content-Type",
                "X-API-Key",
                "Authorization",
            ],
        }
    },
)


@app.before_request
def begin_request_logging():
    g.request_started_at = time.perf_counter()
    g.request_id_token = request_id_context.set(uuid.uuid4().hex)


@app.before_request
def require_api_key():
    if request.path == '/internal/deployment-smoke':
        expected = os.getenv('GENESYS_DEPLOY_SMOKE_KEY', '')
        supplied = request.headers.get('X-GeneSys-Smoke-Key', '')
        if len(expected) < 32 or not hmac.compare_digest(expected.encode(), supplied.encode()):
            return '', 401
        return None
    if request.path.startswith('/internal/preview-builds/'):
        expected = os.getenv('GENESYS_PREVIEW_PROXY_KEY', '')
        supplied = request.headers.get('X-GeneSys-Proxy-Key', '')
        if len(expected) < 32 or not hmac.compare_digest(expected.encode(), supplied.encode()):
            return '', 401
        return None
    if request.method in {'GET', 'HEAD'} and request.path.startswith('/apps/'):
        return None
    if request.method == "OPTIONS" or request.path.rstrip("/") in {
        "/health",
        "/api/v1/health",
    }:
        return None

    if user_auth.configured() or request.path.startswith('/api/projects'):
        try:
            g.user = user_auth.current_user(request.headers.get('Authorization', ''))
            project_paths = {'/publish', '/publish/review', '/list-files', '/read-file', '/write-file', '/agent/run', '/preview', '/restore', '/promote', '/beta/feedback'}
            if request.path in project_paths or request.path.startswith('/agent/jobs') or request.path.startswith('/builder/'):
                user_auth.owned_project(get_project_id(), g.user)
            if request.path == '/promote':
                admins = {value.strip() for value in os.getenv('GENESYS_PROMOTION_ADMIN_IDS', '').split(',') if value.strip()}
                if g.user['id'] not in admins:
                    raise user_auth.AccessError('Production promotion requires administrator access.', 403)
        except user_auth.AccessError as error:
            if request.path == '/preview':
                logger.warning('preview_access_denied status=%s project_id=%s reason=%s',
                               error.status, get_project_id(), str(error))
            return jsonify(status='error', message=str(error), requestId=request_id_context.get()), error.status
        return None

    expected_key = str(getattr(settings, "api_key", "") or "").strip()
    if not expected_key:
        logger.error("api_auth_not_configured")
        return jsonify(
            {
                "status": "error",
                "code": "API_AUTH_NOT_CONFIGURED",
                "message": "API authentication is not configured.",
                "requestId": request_id_context.get(),
            }
        ), 503

    supplied_key = request.headers.get("X-API-Key", "")
    keys_match = hmac.compare_digest(
        supplied_key.encode("utf-8"),
        expected_key.encode("utf-8"),
    )
    if not supplied_key or not keys_match:
        logger.warning(
            "api_request_rejected method=%s path=%s",
            request.method,
            request.path,
        )
        return jsonify(
            {
                "status": "error",
                "code": "UNAUTHORIZED",
                "message": "Invalid or missing API key.",
                "requestId": request_id_context.get(),
            }
        ), 401

    return None


@app.after_request
def finish_request_logging(response):
    request_id = request_id_context.get()
    started_at = g.get("request_started_at", time.perf_counter())
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.path,
        response.status_code,
        duration_ms,
    )
    token = g.pop("request_id_token", None)
    if token is not None:
        request_id_context.reset(token)
    return response


# ============================================================
# HELPERS
# ============================================================

@app.route('/api/projects', methods=['POST'])
def create_user_project():
    try:
        return jsonify(user_auth.create_project(get_json_body().get('name'), g.user)), 201
    except user_auth.AccessError as error:
        return jsonify(status='error', message=str(error)), error.status


@app.route('/api/projects/<project_id>', methods=['GET'])
def get_user_project(project_id):
    try:
        return jsonify(user_auth.owned_project(project_id, g.user))
    except user_auth.AccessError as error:
        return jsonify(status='error', message=str(error)), error.status

def get_project_id() -> str:
    """
    Accept projectId from:
    - JSON body
    - query string

    Defaults to the first GeneSys project.
    """

    data = get_json_body()

    project_id = (
        data.get("projectId")
        or request.args.get(
            "projectId"
        )
        or "genesys-project"
    )

    return (
        str(project_id).strip()
        or "genesys-project"
    )


def get_json_body() -> dict:
    data = request.get_json(
        silent=True
    )

    if not isinstance(
        data,
        dict,
    ):
        return {}

    return data


# ============================================================
# HEALTH
# ============================================================

@app.route(
    "/health",
    methods=["GET"],
)
def health():
    from agent.reference_inspection import rea_command
    from agent.deployment_smoke import checks
    reference_ready = bool(rea_command())
    return jsonify(
        {
            "status": (
                "Genesys Cloud Bridge is Online"
            ),
            "agent": True,
            "deploymentId": os.getenv('RAILWAY_DEPLOYMENT_ID', ''),
            "deploymentSmoke": checks.summary(),
            "visualReview": {"enabled": os.getenv('GENESYS_VISUAL_REVIEW','1')!='0',
                             "providerConfigured": bool(os.getenv('OPENAI_API_KEY'))},
            "referenceInspection": {"enabled": os.getenv('GENESYS_REFERENCE_INSPECTION','1')!='0',
                                    "reaInstalled": reference_ready,
                                    "reaVersion": '6.7.0' if reference_ready else None},
            "daytona": bool(
                os.getenv(
                    "DAYTONA_API_KEY"
                )
            ),
            "groq": bool(
                os.getenv(
                    "GROQ_API_KEY"
                )
            ),
        }
    )


# ============================================================
# LIST FILES
# ============================================================

@app.route(
    "/list-files",
    methods=["GET"],
)
def files():
    try:
        project_id = get_project_id()

        result = list_files(
            project_id=project_id
        )

        return jsonify(
            result
        )

    except Exception as error:
        logger.exception("api_handler_failed")
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# READ FILE
# ============================================================

@app.route(
    "/read-file",
    methods=["GET", "POST"],
)
def read():
    try:
        data = get_json_body()

        filename = (
            data.get("filename")
            or request.args.get(
                "filename"
            )
        )

        if not filename:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "filename is required."
                    ),
                }
            ), 400

        project_id = get_project_id()

        result = read_file(
            filename=str(
                filename
            ),
            project_id=str(
                project_id
            ),
        )

        return jsonify(
            result
        )

    except FileNotFoundError as error:
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 404

    except Exception as error:
        logger.exception("api_handler_failed")
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# WRITE FILE
# ============================================================

@app.route(
    "/write-file",
    methods=["POST"],
)
def write():
    try:
        data = get_json_body()

        filename = data.get(
            "filename"
        )

        content = data.get(
            "content"
        )

        if not filename:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "filename is required."
                    ),
                }
            ), 400

        if content is None:
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "content is required."
                    ),
                }
            ), 400

        project_id = get_project_id()

        if jobs.is_running(project_id):
            return jsonify(status='error',message='Wait for the current build to finish before editing files.'),409
        from agent.version_history import operate
        operate(get_workspace(project_id),'capture',label='Before manual source edit')
        result = write_file(
            filename=str(
                filename
            ),
            content=str(
                content
            ),
            project_id=str(
                project_id
            ),
        )

        return jsonify(
            result
        )

    except Exception as error:
        logger.exception("api_handler_failed")
        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500


# ============================================================
# AGENT RUN
# ============================================================

def execute_agent_request(prompt, project_id, conversation_history, reservation=None, recovery_context=None):
    from agent.build_metrics import current, BuildMetrics
    metrics = BuildMetrics()
    metrics_token = current.set(metrics)
    token = account_context.set(reservation[0] if reservation else None)
    refund = False
    try:
        result = _execute_agent_request(prompt, project_id, conversation_history, recovery_context)
        if isinstance(result, dict):
            refund = result.get('errorType') in PLATFORM_FAILURES
            result['metrics'] = metrics.summary(result)
            if result.get('requestType') != 'chat' and result.get('modifiedFiles'):
                try:
                    from agent.version_history import operate
                    result['sourceVersion'] = operate(get_workspace(project_id),'capture',
                        label='After build: '+str(result.get('status','unknown')))
                except Exception:
                    logger.exception('source_version_capture_failed')
        return result
    finally:
        current.reset(metrics_token)
        usage_limiter.release(reservation, refund=refund)
        account_context.reset(token)


def _execute_agent_request(prompt, project_id, conversation_history, recovery_context=None):
    result = run_agent(
        prompt=str(
            prompt
        ),
        project_id=project_id,
        conversation_history=conversation_history,
        recovery_context=recovery_context,
    )

    if isinstance(result, dict):
        if result.get('buildPassed'):
            try:
                result['buildFingerprint'] = get_workspace(project_id).build_fingerprint()
            except Exception:
                logger.exception('build_fingerprint_failed')
        checkpoint = result.get('checkpoint') or {}
        if result.get('requestType') != 'chat':
            try:
                if result.get('status') == 'success' and result.get('browserVerified') and checkpoint.get('status') == 'success':
                    workspace = get_workspace(project_id)
                    result['previewUrl'] = verified_preview(workspace, checkpoint)
                    from agent.preview_hosting import save, configured
                    if configured():
                        result['previewUrl'] = save(workspace, project_id)
                        result['previewPersistent'] = True
                elif result.get('status') != 'success' and not result.get('previewUrl'):
                    # A failed new build must not strand the last verified build
                    # on a temporary sandbox URL that disappears with the sandbox.
                    from agent.preview_hosting import available_url, save, configured
                    durable = available_url(project_id)
                    if durable:
                        result['previewUrl'] = durable
                        result['previewPersistent'] = True
                    else:
                        workspace = get_workspace(project_id)
                        result['previewUrl'] = verified_preview(workspace)
                        if result['previewUrl'] and configured():
                            result['previewUrl'] = save(workspace, project_id)
                            result['previewPersistent'] = True
                    result['previousPreviewPreserved'] = bool(result['previewUrl'])
            except Exception:
                logger.exception('verified_preview_failed')
                result['previewUrl'] = None
                result['previewHostingError'] = 'The new build could not be saved to persistent hosting. Please report this problem; your previous saved preview is preserved.'
                result['text'] = str(result.get('text') or result.get('message') or '') + '\n\n' + result['previewHostingError']
        from agent.preview_hosting import available_url
        durable = available_url(project_id) if result.get('requestType') != 'chat' else None
        if durable:
            result['previewUrl'] = durable
            result['previewPersistent'] = True
            if result.get('previewHostingError'):
                result['previousPreviewPreserved'] = True
        if result.get('previewUrl') and not result.get('previewPersistent'):
            try:
                result['previewUrl'] = publish_preview(result['previewUrl'], project_id)
            except Exception:
                logger.exception('preview_proxy_registration_failed')
                result['previewUrl'] = None
                result['previewStarted'] = False
                result['message'] = str(result.get('message') or '') + ' Preview could not reconnect. Please retry from the builder.'
        from agent.verification_report import finalize_report
        finalize_report(result)
        try:
            from agent.release_review import save_evidence
            save_evidence(project_id, result)
        except Exception:
            logger.exception('release_evidence_save_failed')
        result.setdefault("requestType", "build")
        checkpoint = result.get("checkpoint")
        if (
            result.get("buildPassed") is True
            and result.get("browserVerified") is True
            and isinstance(checkpoint, dict)
            and checkpoint.get("status") == "success"
            and checkpoint.get("checkpointId")
            and checkpoint.get("commit")
            and settings.promotion_signing_key
        ):
            result["promotionToken"] = sign_verified_checkpoint(
                signing_key=settings.promotion_signing_key,
                project_id=project_id,
                checkpoint_id=str(checkpoint["checkpointId"]),
                checkpoint_commit=str(checkpoint["commit"]),
            )

    return result


@app.route(
    "/agent/run",
    methods=["POST"],
)
def agent_run():
    try:
        data = get_json_body()

        prompt = data.get(
            "prompt"
        )

        if not prompt or not str(
            prompt
        ).strip():
            return jsonify(
                {
                    "status": "error",
                    "message": (
                        "prompt is required."
                    ),
                }
            ), 400

        project_id = get_project_id()

        from agent.builder_modes import encode_mode
        try:
            prompt = encode_mode(str(prompt).strip(), data.get('mode'))
        except ValueError as error:
            return jsonify(status='error', message=str(error)), 400

        project_id = (
            str(project_id).strip()
            or "genesys-project"
        )

        raw_history = data.get("history")
        conversation_history = (
            [
                {
                    "role": str(turn.get("role", "")),
                    "content": str(turn.get("content", "")),
                }
                for turn in raw_history[-10:]
                if isinstance(turn, dict)
            ]
            if isinstance(raw_history, list)
            else []
        )

        logger.info(
            "agent_run_started project_id=%s",
            project_id,
        )

        reservation = reserve_build(prompt)
        result = execute_agent_request(prompt, project_id, conversation_history, reservation)

        return jsonify(
            result
        )

    except UsageLimited as error:
        return limit_response(error)
    except Exception as error:
        logger.exception("agent_run_failed")

        return jsonify(
            {
                "status": "error",
                "message": str(error),
            }
        ), 500



jobs = JobManager(execute=execute_agent_request)
from agent.preview_hosting import start_migration
start_migration()
from agent.deployment_smoke import start_checks
start_checks()


@app.route('/internal/deployment-smoke', methods=['GET', 'POST'])
def deployment_smoke():
    import re
    from agent.deployment_smoke import checks
    if os.getenv('GENESYS_DEPLOY_SMOKE_ENABLED', '1') == '0':
        return jsonify(status='disabled', message='Deployment smoke checks are disabled.'), 503
    if request.method == 'POST':
        data = get_json_body()
        source = data.get('source')
        deployment = str(data.get('deploymentId') or '')
        if source not in {'frontend', 'preview-router', 'manual'} or not re.fullmatch(r'[a-zA-Z0-9:._-]{1,100}', deployment):
            return jsonify(message='Invalid deployment check trigger.'), 400
        scheduled = checks.schedule(source + ':' + deployment)
        return jsonify(scheduled=scheduled, **checks.summary()), 202
    return jsonify(checks.report)


@app.route("/agent/jobs", methods=["POST"])
def start_agent_job():
    data = get_json_body()
    prompt = str(data.get("prompt") or "").strip()
    project_id = get_project_id()
    if not prompt or len(prompt) > 8000 or not project_id or len(project_id) > 128:
        return jsonify(status="error", message="A project and a prompt of at most 8000 characters are required."), 400
    from agent.builder_modes import encode_mode
    try:
        prompt = encode_mode(prompt, data.get('mode'))
    except ValueError as error:
        return jsonify(status='error', message=str(error)), 400
    history = [{"role": turn.get("role"), "content": str(turn.get("content") or "")[:2000]}
               for turn in (data.get("history") or [])[-10:] if isinstance(turn, dict)] if isinstance(data.get("history"), list) else []
    try:
        reservation = reserve_build(prompt)
    except UsageLimited as error:
        return limit_response(error)
    try:
        previous = jobs.latest(project_id)
        verification_retry = saved_build_retry(previous, prompt)
        from agent.jobs import implementation_retry_context
        job_id = jobs.submit(project_id, request_id_context.get(),
            prompt=prompt, history=history, reservation=reservation,
            verification_retry=verification_retry,
            implementation_retry=implementation_retry_context(previous,prompt),
            user_id=g.user["id"] if getattr(g, "user", None) else None)
    except ValueError as error:
        usage_limiter.release(reservation, refund=True)
        logger.warning('build_request_rejected reason=%s', error)
        return jsonify(status="error", message=str(error)), 429
    except Exception:
        usage_limiter.release(reservation, refund=True)
        raise
    return jsonify(jobs.get(job_id, project_id)), 202


@app.get('/builder/reviews')
def builder_reviews():
    from agent.visual_evidence import latest_reviews
    return jsonify(reviews=latest_reviews(get_project_id()))


@app.get('/builder/reviews/<review_id>/<viewport>')
def builder_review_image(review_id, viewport):
    from flask import send_file, abort
    from agent.visual_evidence import image_path
    path = image_path(get_project_id(), review_id, viewport)
    if path is None:
        abort(404)
    response = send_file(path.resolve(), mimetype='image/png')
    response.headers['Cache-Control'] = 'private, no-store'
    return response


@app.route('/builder/controls', methods=['GET', 'PUT'])
def builder_controls():
    from agent.builder_controls import get_controls, save_controls, ControlsConflict
    data = get_json_body() if request.method == 'PUT' else {}
    project_id = str(request.args.get('projectId') or data.get('projectId') or '').strip()
    if not project_id or len(project_id) > 128:
        return jsonify(status='error', message='A project is required.'), 400
    try:
        controls = save_controls(project_id, data) if request.method == 'PUT' else get_controls(project_id)
        return jsonify(controls)
    except ControlsConflict as error:
        return jsonify(status='error', message=str(error)), 409
    except ValueError as error:
        return jsonify(status='error', message=str(error)), 400


@app.route('/agent/jobs', methods=['GET'])
def latest_agent_job():
    project_id = get_project_id()
    if request.args.get('history') == '1':
        return jsonify(jobs=jobs.conversation(project_id))
    return jsonify(job=jobs.latest(project_id))


@app.route("/agent/jobs/<job_id>", methods=["GET"])
def get_agent_job(job_id):
    job = jobs.get(job_id, get_project_id())
    if job is None:
        return jsonify(status="error", message="This request is no longer available. The service may have restarted; please retry."), 404
    return jsonify(job)


@app.route("/preview", methods=["POST"])
def reconnect_preview():
    project_id = get_project_id()
    if not project_id or len(project_id) > 128:
        return jsonify(status="error", message="projectId is required."), 400
    from agent.preview_hosting import available_url, save, configured
    durable = available_url(project_id)
    if durable:
        return jsonify(status='success', url=durable, running=True, persistent=True)
    if jobs.is_running(project_id):
        return jsonify(status="error", message="Wait for the current request to finish before reconnecting the preview."), 409
    try:
        workspace = get_workspace(project_id)
        workspace._ensure_sandbox_running()
        saved = verified_preview(workspace)
        if saved and configured():
            return jsonify(status='success', url=save(workspace, project_id), running=True, persistent=True)
        result = {'status': 'success', 'url': saved, 'running': True} if saved else workspace.start_preview()
        if result.get('url'):
            result['url'] = publish_preview(result['url'], project_id)
        return jsonify(result)
    except Exception:
        logger.exception("preview_reconnect_failed project_id=%s", project_id)
        return jsonify(status="error", message="Preview could not reconnect. Please retry or report this problem."), 503


@app.route('/usage', methods=['GET'])
def account_usage():
    return jsonify(usage_limiter.status(getattr(g, 'user', {}).get('id', 'legacy-api')))


@app.route('/restore', methods=['POST'])
def restore_project():
    project_id = get_project_id()
    if jobs.is_running(project_id) or usage_limiter.status(getattr(g, 'user', {}).get('id', 'legacy-api'))['buildRunning']:
        return jsonify(status='error', message='Wait for the current build to finish before restoring.'), 409
    try:
        workspace = get_workspace(project_id)
        workspace._ensure_sandbox_running()
        result = restore_verified(workspace)
        if result.get('status') != 'success':
            return jsonify(status='error', message='The previous version could not be restored.'), 503
        url = verified_preview(workspace)
        from agent.preview_hosting import save, configured
        url = save(workspace, project_id) if configured() else publish_preview(url, project_id)
        return jsonify(status='success', url=url, persistent=configured(), message='Last verified version restored. Previous edits are saved in the project Git stash.')
    except Exception:
        logger.exception('restore_failed')
        return jsonify(status='error', message='No working version could be restored. Please retry or report this problem.'), 503


@app.route('/builder/history', methods=['GET','POST'])
def project_history():
    import re
    from agent.version_history import operate,local_versions
    project_id=get_project_id()
    if jobs.is_running(project_id):
        return jsonify(status='error',message='Wait for the current build to finish.'),409
    try:
        from agent.daytona_workspace import get_daytona, sandbox_name_for_project
        from types import SimpleNamespace
        if request.method=='GET':
            saved=local_versions(project_id)
            if saved:return jsonify(versions=saved)
            workspace=SimpleNamespace(project_id=project_id,sandbox=get_daytona().get(sandbox_name_for_project(project_id)))
            return jsonify(versions=operate(workspace,'list'))
        from agent.builder_controls import get_controls
        version=str(get_json_body().get('versionId') or '')
        if not re.fullmatch(r'[0-9a-f]{32}',version):
            return jsonify(status='error',message='Choose a valid source version.'),400
        workspace=get_workspace(project_id)
        result=operate(workspace,'restore',id=version,locks=get_controls(project_id)['lockedPaths'])
        return jsonify(status='success',**result)
    except Exception:
        logger.exception('project_history_failed')
        return jsonify(status='error',message='Source history is unavailable or restore was blocked. Check frozen files and workspace availability. Your last published preview has not changed.'),503


@app.post('/builder/app-backend')
def configure_app_backend():
    from agent.app_backend import install,validate
    project_id=get_project_id()
    if jobs.is_running(project_id):
        return jsonify(message='Wait for the current build to finish.'),409
    try:
        data=get_json_body();validate(data)
        return jsonify(install(get_workspace(project_id),data))
    except ValueError as error:
        return jsonify(message=str(error)),400
    except Exception:
        logger.exception('app_backend_configuration_failed')
        return jsonify(message='App backend setup failed. Your previous published site is unchanged; check source history before retrying.'),503


@app.route("/beta/feedback", methods=["POST"])
def beta_feedback():
    data = get_json_body()
    message = str(data.get("message") or "").strip()
    if not message or len(message) > 2000:
        return jsonify(status="error", message="Describe the problem in 1-2000 characters."), 400
    from agent.beta_storage import connection
    with connection() as db:
        db.execute('CREATE TABLE IF NOT EXISTS beta_feedback(id TEXT PRIMARY KEY, user_id TEXT, project_id TEXT, request_id TEXT, stage TEXT, message TEXT, created REAL)')
        db.execute('INSERT INTO beta_feedback VALUES(?,?,?,?,?,?,?)',
            (request_id_context.get(), getattr(g, 'user', {}).get('id'), get_project_id(),
             str(data.get('requestId') or '')[:64], str(data.get('stage') or '')[:100], message, time.time()))
    logger.warning("beta_feedback project_id=%s related_request_id=%s stage=%s message=%s",
        str(data.get("projectId") or "")[:128], str(data.get("requestId") or "")[:64],
        str(data.get("stage") or "")[:100], message.replace("\n", " ").replace("\r", " "))
    return jsonify(status="success", reportId=request_id_context.get())


# ============================================================
# VERIFIED PRODUCTION PROMOTION
# ============================================================

@app.post('/publish/review')
def review_publication():
    from agent.release_review import review
    data = get_json_body()
    checkpoint = str(data.get('checkpointId') or '')
    project_id = get_project_id()
    commit = verify_checkpoint_promotion_token(str(data.get('promotionToken') or ''),
        signing_key=settings.promotion_signing_key or '', project_id=project_id, checkpoint_id=checkpoint)
    if not settings.promotion_signing_key or not commit:
        return jsonify(status='error', message='Publishing approval has expired. Run verification again; your saved preview is unchanged.'), 403
    if jobs.is_running(project_id):
        return jsonify(status='error', message='Wait for the current build to finish.'), 409
    return jsonify(review(project_id, checkpoint, commit))


@app.post('/publish')
def publish_project():
    from agent.publishing import publish
    enabled = os.getenv('GENESYS_PUBLISH_ENABLED', '').lower() == 'true'
    allowed = {value.strip() for value in os.getenv('GENESYS_PUBLISH_TEST_USER_IDS', '').split(',') if value.strip()}
    if not user_auth.configured() or (not enabled and getattr(g, 'user', {}).get('id') not in allowed):
        return jsonify(status='error', message='Publishing is in testing. It is not enabled for this account yet.'), 503
    if not os.getenv('RAILWAY_VOLUME_MOUNT_PATH') and os.getenv('RAILWAY_ENVIRONMENT_ID'):
        return jsonify(status='error', message='Publishing needs persistent storage.'), 503
    data = request.get_json(silent=True) or {}
    checkpoint = str(data.get('checkpointId') or '')
    project_id = get_project_id()
    commit = verify_checkpoint_promotion_token(str(data.get('promotionToken') or ''),
        signing_key=settings.promotion_signing_key or '', project_id=project_id, checkpoint_id=checkpoint)
    if not settings.promotion_signing_key or not commit:
        return jsonify(status='error', message='Publishing approval has expired. Run verification again; your saved preview is unchanged.'), 403
    if jobs.is_running(project_id):
        return jsonify(status='error', message='Wait for the current build to finish.'), 409
    from agent.release_review import review, acknowledged
    release = review(project_id, checkpoint, commit)
    if not acknowledged(release, data.get('reviewHash'), data.get('acknowledgements')):
        return jsonify(status='error', message='Resolve blocking checks and review this exact version before publishing.', review=release), 428
    try:
        publication = publish(get_workspace(project_id), project_id, checkpoint, commit)
        domain = os.getenv('GENESYS_PREVIEW_DOMAIN', '').strip()
        url = 'https://app-' + publication + '.' + domain + '/' if domain else request.url_root.rstrip('/') + '/apps/' + publication + '/'
        return jsonify(status='success', url=url, publicationId=publication)
    except ValueError as error:
        return jsonify(status='error', message=str(error)), 400
    except Exception:
        logger.exception('project_publish_failed project_id=%s', project_id)
        return jsonify(status='error', message='Publishing failed. Your verified project is preserved.'), 503


@app.get('/apps/<publication>/')
@app.get('/apps/<publication>/<path:filename>')
def published_app(publication, filename='index.html'):
    import re
    from agent.publishing import root
    from pathlib import Path
    if not re.fullmatch(r'[0-9a-f]{32}', publication) or any(part.startswith('.') for part in Path(filename).parts):
        return '', 404
    directory = root() / publication
    if (directory / '.unpublished').exists():
        return '', 404
    active = directory / '.active'
    if active.is_file():
        revision = active.read_text().strip()
        if not re.fullmatch(r'[0-9a-f]{32}', revision):
            return '', 404
        directory = directory / '.versions' / revision
    if not (directory / 'index.html').is_file():
        return '', 404
    response = send_from_directory(directory, filename)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "sandbox allow-scripts allow-forms allow-popups allow-downloads"
    return response


@app.get('/internal/preview-builds/<ticket>/')
@app.get('/internal/preview-builds/<ticket>/<path:filename>')
def completed_preview_asset(ticket, filename='index.html'):
    from pathlib import Path
    from agent.preview_hosting import directory
    if '\\' in filename or any(part.startswith('.') for part in Path(filename).parts):
        return '', 404
    active = directory(ticket)
    if active is None:
        return '', 404
    if not (active / filename).is_file():
        # Client-side routes fall back to HTML, missing JS/images never do.
        if 'text/html' in request.headers.get('Accept', '') and not Path(filename).suffix:
            filename = 'index.html'
        else:
            return '', 404, {'X-GeneSys-Preview-Hosted': '1'}
    response = send_from_directory(active, filename)
    response.headers['X-GeneSys-Preview-Hosted'] = '1'
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = 'sandbox allow-scripts allow-same-origin allow-forms allow-popups allow-downloads'
    return response


@app.delete('/publish')
def unpublish_project():
    import json
    import re
    from agent.publishing import root
    data = request.get_json(silent=True) or {}
    publication = str(data.get('publicationId') or '')
    if not re.fullmatch(r'[0-9a-f]{32}', publication):
        return jsonify(status='error', message='Invalid publication.'), 400
    directory = root() / publication
    proof = directory / '.publication.json'
    if not proof.is_file() or json.loads(proof.read_text())['projectId'] != get_project_id():
        return jsonify(status='error', message='Publication not found.'), 404
    (directory / '.unpublished').touch()
    return jsonify(status='success')


@app.delete('/api/projects/<project_id>')
def delete_user_project(project_id):
    from agent.daytona_workspace import get_daytona, sandbox_name_for_project
    from agent.publishing import root
    from agent.beta_storage import connection
    try:
        user_auth.owned_project(project_id, g.user)
        if jobs.is_running(project_id):
            return jsonify(status='error', message='Wait for the current build to finish before deleting this project.'), 409
        try:
            sandbox = get_daytona().get(sandbox_name_for_project(project_id))
        except Exception as error:
            if 'not found' not in str(error).lower() and '404' not in str(error):
                raise
        else:
            state = str(sandbox.state).lower()
            if state.endswith('started'):
                sandbox.stop()
            if not state.endswith('archived'):
                sandbox.archive()
        if (request.get_json(silent=True) or {}).get('unpublish') is True:
            # Includes pre-mapping publications; no files or credentials are exposed.
            import json
            for proof in root().glob('*/.publication.json'):
                if json.loads(proof.read_text()).get('projectId') == project_id:
                    (proof.parent / '.unpublished').touch()
        user_auth.call('DELETE', '/rest/v1/projects', g.user['access_token'], params={'id':'eq.'+project_id})
        from agent.preview_hosting import disable
        disable(project_id)
        return jsonify(status='success', message='Project deleted; workspace archived.')
    except user_auth.AccessError as error:
        return jsonify(status='error', message=str(error)), error.status
    except Exception:
        logger.exception('project_cleanup_failed project_id=%s', project_id)
        return jsonify(status='error', message='Project cleanup could not finish. Your project has not been deleted; retry shortly.'), 503


@app.route(
    "/promote",
    methods=["POST"],
)
def promote_verified_checkpoint():
    data = get_json_body()
    checkpoint_id = str(data.get("checkpointId") or "").strip()
    promotion_token = str(data.get("promotionToken") or "").strip()
    project_id = get_project_id()

    if not checkpoint_id:
        return jsonify(
            {
                "status": "error",
                "code": "INVALID_CHECKPOINT",
                "message": "checkpointId is required.",
            }
        ), 400

    if not settings.github_token or not settings.promotion_signing_key:
        return jsonify(
            {
                "status": "error",
                "code": "PROMOTION_NOT_CONFIGURED",
                "message": (
                    "Production promotion requires GENESYS_GITHUB_TOKEN and "
                    "GENESYS_PROMOTION_SIGNING_KEY."
                ),
            }
        ), 503

    verified_commit = verify_checkpoint_promotion_token(
        promotion_token,
        signing_key=settings.promotion_signing_key,
        project_id=project_id,
        checkpoint_id=checkpoint_id,
    )
    if not verified_commit:
        return jsonify(
            {
                "status": "error",
                "code": "INVALID_PROMOTION_PROOF",
                "message": (
                    "This checkpoint has no valid, unexpired verification "
                    "proof. Run and verify the change again."
                ),
            }
        ), 403

    try:
        workspace = get_workspace(project_id)
        result = workspace.promote_checkpoint(
            checkpoint_id,
            github_token=settings.github_token,
            repository=settings.github_repository,
            base_branch=settings.github_base_branch,
            expected_commit=verified_commit,
        )
    except Exception:
        logger.exception(
            "verified_checkpoint_promotion_failed project_id=%s checkpoint_id=%s",
            project_id,
            checkpoint_id,
        )
        return jsonify(
            {
                "status": "error",
                "code": "PROMOTION_FAILED",
                "message": "Could not promote the verified checkpoint.",
                "requestId": request_id_context.get(),
            }
        ), 500

    if result.get("status") == "success":
        logger.info(
            "verified_checkpoint_promoted project_id=%s checkpoint_id=%s pr_number=%s",
            project_id,
            checkpoint_id,
            result.get("number"),
        )
        return jsonify(result)

    code = result.get("code")
    if code in {"INVALID_CHECKPOINT", "CHECKPOINT_NOT_FOUND"}:
        http_status = 400
    elif code in {"STALE_CHECKPOINT", "CHECKPOINT_CHANGED"}:
        http_status = 409
    else:
        http_status = 502
    return jsonify(result), http_status


# ============================================================
# ROOT
# ============================================================

@app.route(
    "/",
    methods=["GET"],
)
def root():
    return jsonify(
        {
            "name": "GeneSys Cloud Agent",
            "status": "online",
            "endpoints": {
                "health": "/health",
                "listFiles": "/list-files",
                "readFile": "/read-file",
                "writeFile": "/write-file",
                "agentRun": "/agent/run",
                "promote": "/promote",
            },
        }
    )


# ============================================================
# BROWSER CONSOLE
# ============================================================

MAX_BROWSER_LOG_LENGTH = 20000


@app.route(
    "/browser-console",
    methods=["POST", "OPTIONS"],
)
def browser_console():
    if request.method == "OPTIONS":
        return ("", 204)

    data = get_json_body()

    level = str(
        data.get("level", "error")
    ).lower()

    message = str(
        data.get("message", "")
    )

    if len(message) > MAX_BROWSER_LOG_LENGTH:
        message = (
            message[:MAX_BROWSER_LOG_LENGTH]
            + "..."
        )

    logger.info(
        "browser_console_event level=%s message_length=%s",
        level.upper(),
        len(message),
    )

    return jsonify(
        {
            "status": "ok",
        }
    )

# ============================================================
# LOCAL DEVELOPMENT
# ============================================================

if __name__ == "__main__":
    host = os.getenv(
        "HOST",
        "127.0.0.1",
    )

    port = int(
        os.getenv(
            "PORT",
            "5000",
        )
    )

    print()
    print(
        "🚀 GeneSys Execution Agent"
    )

    print(
        f"📁 PROJECT ROOT: {PROJECT_ROOT}"
    )

    print(
        "🤖 MODEL: "
        + os.getenv(
            "GENESYS_MODEL",
            "openai/gpt-oss-120b",
        )
    )

    print(
        "🔑 GROQ KEY LOADED: "
        + str(
            bool(
                os.getenv(
                    "GROQ_API_KEY"
                )
            )
        )
    )

    print(
        "🔑 DAYTONA KEY LOADED: "
        + str(
            bool(
                os.getenv(
                    "DAYTONA_API_KEY"
                )
            )
        )
    )

    print(
        f"🌐 Server: http://{host}:{port}"
    )

    print()

    app.run(
        host=host,
        port=port,
        debug=False,
    )
