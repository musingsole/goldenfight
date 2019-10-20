import boto3
import warrant


def get_cognito_pool_id():
        pool_id = None
        for pool in boto3.client("cognito-idp").list_user_pools(MaxResults=60)['UserPools']:
            if 'openscale' in pool['Name'].lower():
                pool_id = pool['Id']
                break

        if pool_id is None:
            raise Exception("No Cognito User Pool Identified. Creating...")

        return pool_id


def get_cognito_client_id():
    pool_id = get_cognito_pool_id()
    client_id = None
    for client in boto3.client("cognito-idp").list_user_pool_clients(UserPoolId=pool_id, MaxResults=60)['UserPoolClients']:
        if 'openscale' in client['ClientName'].lower():
            client_id = client['ClientId']

    if client_id is None:
        print("No client id found. Creating...")
        cog_client = boto3.client("cognito-idp").create_user_pool_client(
            UserPoolId=pool_id,
            ClientName="OpenScale",
            GenerateSecret=False,
            RefreshTokenValidity=7
        )
        client_id = cog_client['UserPoolClient']['ClientId']

    return client_id


def cognito_session(**kwargs):
    pool_id = get_cognito_pool_id()
    app_id = get_cognito_client_id()
    return warrant.Cognito(pool_id,
                           app_id,
                           **kwargs)


def create_user(username, password):
    cs = cognito_session()
    cs.add_base_attributes()
    cs.register(username, password)


def verify_user(username, verification_code):
    cs = cognito_session()
    cs.confirm_sign_up(verification_code, username=username)


def initiate_forgotten_password(username):
    cs = cognito_session(username=username)
    cs.initiate_forgot_password()


def confirm_forgotten_password(username, forgotten_password_code, password):
    cs = cognito_session(username=username)
    cs.confirm_forgot_password(forgotten_password_code, password)


def authenticate(username, password):
    pool_id = get_cognito_pool_id()
    app_id = get_cognito_client_id()
    awssrp = warrant.aws_srp.AWSSRP(username=username,
                                    password=password,
                                    pool_id=pool_id,
                                    client_id=app_id)

    tokens = awssrp.authenticate_user()['AuthenticationResult']
    return tokens


def get_user_id(access_token):
    try:
        cognito_client = boto3.client("cognito-idp")
        resp = cognito_client.get_user(AccessToken=access_token)
        username = resp['Username']
    except Exception:
        print("Failed to get username from token")
        raise

    return username


def renew_tokens(tokens):
    print("Renewing tokens...")
    print("Renewing for {}".format(get_user_id(tokens['AccessToken'])))
    cs = cognito_session(refresh_token=tokens['RefreshToken'],
                         access_token=tokens['AccessToken'])
    cs.renew_access_token()
