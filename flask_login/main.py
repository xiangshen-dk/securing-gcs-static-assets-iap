# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import base64
import datetime
import hashlib
import hmac
import time
from google.cloud import secretmanager
from flask import Flask, redirect, request, session, make_response, abort

sm_client = secretmanager.SecretManagerServiceClient()

project_id = os.environ.get("PROJECT_ID")
cdn_sign_key_name = os.environ.get("CDN_SIGN_KEY")
web_url = os.environ.get("WEB_URL")
gcs_path = os.environ.get("GCS_PATH")

app = Flask(__name__)
app.secret_key = os.urandom(12)


@app.route('/')
def home():
    if not session.get('logged_in'):
        url = request.url
        session['logged_in'] = True
        # Expire in a week
        expire_time = int(time.time()) + 3600 * 24 * 7
        cdn_sign_key_val = get_secret(cdn_sign_key_name)
        cookie = sign_cookie(web_url, cdn_sign_key_name, cdn_sign_key_val,
                             datetime.datetime.utcfromtimestamp(expire_time))

        resp = make_response(redirect(url.replace('http:', 'https:')))
        resp.set_cookie('Cloud-CDN-Cookie', cookie,
                        expires=expire_time, path=gcs_path)
        return resp
    else:
        return 'File not found! You have already logged in. <a href="/logout">Logout</a>'


@app.route("/logout")
def logout():
    # Clearing the cookie does not change the fact that the user 
    # is still logged into Google Accounts.
    # This just gives user a chance to switch an account. 
    session.clear()
    resp = make_response(redirect('/?gcp-iap-mode=CLEAR_LOGIN_COOKIE'))
    resp.set_cookie('Cloud-CDN-Cookie', '', expires=0, path=gcs_path)
    return resp


def sign_cookie(url_prefix, key_name, base64_key, expiration_time):
    """Gets the Signed cookie value for the specified URL prefix and configuration.

    Args:
        url_prefix: URL prefix to sign as a string.
        key_name: name of the signing key as a string.
        base64_key: signing key as a base64 encoded string.
        expiration_time: expiration time as a UTC datetime object.

    Returns:
        Returns the Cloud-CDN-Cookie value based on the specified configuration.
    """
    encoded_url_prefix = base64.urlsafe_b64encode(
        url_prefix.strip().encode('utf-8')).decode('utf-8')
    epoch = datetime.datetime.utcfromtimestamp(0)
    expiration_timestamp = int((expiration_time - epoch).total_seconds())
    decoded_key = base64.urlsafe_b64decode(base64_key)

    policy_pattern = u'URLPrefix={encoded_url_prefix}:Expires={expires}:KeyName={key_name}'
    policy = policy_pattern.format(
        encoded_url_prefix=encoded_url_prefix,
        expires=expiration_timestamp,
        key_name=key_name)

    digest = hmac.new(
        decoded_key, policy.encode('utf-8'), hashlib.sha1).digest()
    signature = base64.urlsafe_b64encode(digest).decode('utf-8')

    signed_policy = u'{policy}:Signature={signature}'.format(
        policy=policy, signature=signature)
    # print(signed_policy)
    return signed_policy


def get_secret(secret_id, version_id="latest"):
    """
    Access the payload for the given secret version if one exists. The version
    can be a version number as a string (e.g. "5") or an alias (e.g. "latest").
    """
    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = sm_client.access_secret_version(request={"name": name})

    payload = response.payload.data.decode('UTF-8').rstrip()
    return payload


@app.errorhandler(404)
def not_found(e):
    return home()


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
