# Native libraries
import requests
from urllib.parse import quote, unquote
# Project libraries
from qlty.utilities.utils import setup_logger
import settings

# Initialize the logger
logger = setup_logger(__name__, settings.DEBUG_LEVEL)


class LeadLmsIntegration:
    """
    Provides LEAD LMS API access for test data cleanup.
    Enables lookup and deletion of test users created during automated tests.
    """

    def __init__(self):
        """
        Initialize the LEAD LMS API client.
        Authenticates using admin credentials from settings to obtain a Bearer token.
        """
        self.base_url = settings.ENVIRONMENTS['STAGING']['BASE_URL'].rstrip('/')
        username = settings.LEAD_API['USERNAME']
        password = settings.LEAD_API['PASSWORD']

        logger.info("Authenticating with LEAD LMS API")
        response = requests.post(
            f"{self.base_url}/api/login",
            data={'email': username, 'password': password},
            headers={'Accept': 'application/json'}
        )
        response.raise_for_status()
        token = response.json()['access_token']

        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        logger.info("LEAD LMS API authentication successful")

    def lookup_user(self, email):
        """
        Look up a user by email address.

        :param email: The email address to search for
        :type email: str
        :return: User dict if found, None if not found
        :rtype: dict or None
        """
        encoded_email = quote(email)
        url = f"{self.base_url}/api/users/email/lookup?email={encoded_email}"
        logger.debug(f"Looking up user by email: {email}")

        response = requests.get(url, headers=self.headers)
        if response.status_code == 404:
            logger.debug(f"User not found: {email}")
            return None
        response.raise_for_status()

        user = response.json().get('user')
        logger.debug(f"Found user: id={user['id']}, email={user['email']}")
        return user

    def delete_user(self, user_id):
        """
        Soft-delete a user by ID.

        :param user_id: The ID of the user to delete
        :type user_id: int
        """
        url = f"{self.base_url}/api/users/{user_id}"
        logger.info(f"Deleting user id={user_id}")

        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        logger.info(f"User id={user_id} deleted successfully")

    def delete_user_by_email(self, email):
        """
        Look up a user by email and delete them.

        :param email: The email address of the user to delete
        :type email: str
        :return: True if user was found and deleted, False if user was not found
        :rtype: bool
        """
        user = self.lookup_user(email)
        if user is None:
            logger.warning(f"Cannot delete user, not found: {email}")
            return False
        self.delete_user(user['id'])
        return True

    def delete_group(self, group_id):
        """
        Soft-delete a group by ID.

        :param group_id: The ID of the group to delete
        :type group_id: int
        """
        url = f"{self.base_url}/api/groups/{group_id}"
        logger.info(f"Deleting group id={group_id}")

        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        logger.info(f"Group id={group_id} deleted successfully")

    def _get_nova_session(self):
        """
        Authenticate via web session for Nova admin API operations.
        Returns a requests.Session with valid CSRF token.

        :return: Authenticated session
        :rtype: requests.Session
        """
        if hasattr(self, '_nova_session'):
            return self._nova_session

        username = settings.LEAD_API['USERNAME']
        password = settings.LEAD_API['PASSWORD']

        session = requests.Session()
        session.get(f"{self.base_url}/login")
        xsrf = unquote(session.cookies.get('XSRF-TOKEN'))
        session.post(
            f"{self.base_url}/login",
            data={'email': username, 'password': password},
            headers={'X-XSRF-TOKEN': xsrf, 'Accept': 'application/json'}
        )
        self._nova_session = session
        return session

    def create_group(self, name, premium=False, registration_fee=None):
        """
        Create a group via the Nova admin API.

        :param name: Group name
        :type name: str
        :param premium: Whether to create a premium group
        :type premium: bool
        :param registration_fee: Registration fee for premium groups (e.g. "25.00")
        :type registration_fee: str or None
        :return: Group ID
        :rtype: int
        """
        session = self._get_nova_session()
        xsrf = unquote(session.cookies.get('XSRF-TOKEN'))

        form_data = {
            'name': (None, name),
            'is_place': (None, '0'),
            'auto_joins_parent_group': (None, '0'),
            'premium_bool': (None, '1' if premium else '0'),
            'asks_child_group_on_registration': (None, '0'),
            'allows_other_users_on_registration': (None, '0'),
            'has_authorization_status': (None, '0'),
            'uses_virtus': (None, '0'),
            'user_can_view': (None, '0'),
            'is_featured': (None, '0'),
            'shows_on_browse': (None, '0'),
            'hide_group_from_invites': (None, '0'),
        }

        if premium:
            form_data['premium_type'] = (None, 'one_time')
            form_data['premium_pricing_model'] = (None, 'flat_rate')
            form_data['registration_fee'] = (None, registration_fee or '0.00')
            form_data['allows_split_payments'] = (None, '0')

        response = session.post(
            f"{self.base_url}/nova-api/groups",
            files=form_data,
            headers={
                'X-XSRF-TOKEN': xsrf,
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
            }
        )
        response.raise_for_status()

        group_id = response.json()['id']
        logger.info(f"Created group '{name}' id={group_id} premium={premium}")
        return group_id
