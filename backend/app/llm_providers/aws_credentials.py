"""AWS credential bootstrap shared by the Bedrock providers.

The experimental Smithy SDK only resolves credentials from environment
variables (``EnvironmentCredentialsResolver``). This helper loads them from
boto3's full standard chain (env vars, ~/.aws/credentials, IAM role) and
exports them into the process environment so the Smithy resolver finds them.
"""

import os

from app.core.exceptions import InvalidRequestError


def bootstrap_aws_env_credentials() -> None:
    """Ensure AWS credentials are present in os.environ (via boto3's chain).

    No-op if AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY are already set.

    Raises:
        InvalidRequestError: If no credentials can be resolved.
    """
    if os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("AWS_SECRET_ACCESS_KEY"):
        return

    try:
        import boto3
    except ImportError as e:
        raise InvalidRequestError("Bedrock support requires: uv add boto3") from e

    creds = boto3.Session().get_credentials()
    if not creds:
        raise InvalidRequestError(
            "No AWS credentials found. Configure ~/.aws/credentials or set "
            "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY."
        )
    frozen = creds.get_frozen_credentials()
    os.environ["AWS_ACCESS_KEY_ID"] = frozen.access_key
    os.environ["AWS_SECRET_ACCESS_KEY"] = frozen.secret_key
    if frozen.token:
        os.environ["AWS_SESSION_TOKEN"] = frozen.token
