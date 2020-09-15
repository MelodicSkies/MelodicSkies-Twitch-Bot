from configparser import ConfigParser
import requests
import webbrowser
from http.server import  HTTPServer, BaseHTTPRequestHandler
import re
import json


class Authenticator:

    def __init__(self, username, channel, client_id, client_secret, user_oauth_token, app_access_token, refresh_token, redirect_uri, authorization_code, bot_token, bot_refresh_token):

        self.username = username.lower()
        self.channel = '#' + channel.lower()
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_oauth_token = user_oauth_token
        self.app_access_token = app_access_token
        self.refresh_token = refresh_token
        self.redirect_uri = redirect_uri
        self.authorization_code = authorization_code
        self.bot_token = bot_token
        self.bot_refresh_token = bot_refresh_token
        self.scopes = ['analytics:read:extensions', 'analytics:read:games', 'bits:read', 'channel:edit:commercial', 'channel:read:hype_train', 'channel:read:subscriptions', 'clips:edit', 
                        'user:edit', 'user:edit:broadcast', 'user:edit:follows', 'user:read:broadcast', 'user:read:email', 'channel:moderate', 'chat:edit', 'chat:read', 'whispers:read', 
                        'whispers:edit'] #edit scopes here
    
    #checks to see if oauth and access tokens exist, creates new ones if they don't or refresh them if they are expired, checks upon startup each time
    def token_check(self):
        if self.user_oauth_token:
            new_token = self.validate_oauth_token()
        else:
            new_token = self.authorize_app()

        if self.app_access_token:
            self.validate_access_token()
        else:
            self.retrieve_access_token()

        return new_token

    #asks user to authorize this bot to access and edit their twitch info based on the scopes listed above, only initiates on first use
    def authorize_app(self):
        total_scopes = ''
        for item in self.scopes:
            total_scopes += f'{item} '
        
        url = 'https://id.twitch.tv/oauth2/authorize'
        headers = {'client_id': self.client_id, 'redirect_uri': self.redirect_uri, 'response_type': 'code', 'scope' : total_scopes.strip()}
        authorization_url = requests.get(url, headers).url
        webbrowser.open(f'{authorization_url}', new=2) #opens request window in browser

        #authorization redirects user to an uri with the token generation code in the redirect url, creates local http server to capture code
        PORT = 8000
        server = Stoppable_Server(('', PORT), Server_Handler)
        server.serve_forever()

        self.authorization_code = edit_config('retrieve', 'authorizationcode', '')[0]
        return(self.retrieve_oauth_token())

    #retrieves oauth token from twitch and updates login file
    def retrieve_oauth_token(self): 
        url = 'https://id.twitch.tv/oauth2/token'
        headers = {'client_id': self.client_id, 'client_secret': self.client_secret, 'code': self.authorization_code, 'grant_type': 'authorization_code', 'redirect_uri': self.redirect_uri}
        
        request = requests.post(url, headers).json()
        oauth_token = request['access_token']
        refresh_token = request['refresh_token']

        self.user_oauth_token = oauth_token
        self.refresh_token = refresh_token
        edit_config('edit', 'oauthtoken', oauth_token)
        edit_config('edit', 'refreshtoken', refresh_token)

        return oauth_token

    #retrieves access token from twitch and updates login file
    def retrieve_access_token(self):
        total_scopes = ''
        for item in self.scopes:
            total_scopes += f'{item} '
        
        url = 'https://id.twitch.tv/oauth2/token'
        headers = {'client_id': self.client_id, 'client_secret': self.client_secret, 'grant_type': 'client_credentials', 'scope': total_scopes.strip()}

        request = requests.post(url, headers).json()
        access_token = request['access_token']

        self.app_access_token = access_token

        edit_config('edit', 'accesstoken', access_token)

    #sends request to check if oauth token is expired, if expiration is within 2 hours, refreshes token
    def validate_oauth_token(self):
        url = 'https://id.twitch.tv/oauth2/validate'
        headers = {'Authorization': f'OAuth {self.user_oauth_token}'}
        
        request = requests.get(url, headers=headers).json()

        try:
            expires_in = request['expires_in']
            if expires_in <= 120:
                return(self.refresh_oauth_token())

        except:
            return(self.refresh_oauth_token())

    #sends request to check if access token is expired, if expiration is within 2 hours, generates new toke, access tokens can't be refreshed
    def validate_access_token(self):
        url = 'https://id.twitch.tv/oauth2/validate'
        headers = {'Authorization': f'OAuth {self.app_access_token}'}
        
        request = requests.get(url, headers=headers).json()

        try:
            expires_in = request['expires_in']
            if expires_in <= 120:
                self.retrieve_access_token()

        except:
            self.retrieve_access_token()

    #refreshes oauth token and updates login file
    def refresh_oauth_token(self):
        url = 'https://id.twitch.tv/oauth2/token'
        headers = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token, 'client_id': self.client_id, 'client_secret': self.client_secret}

        request = requests.post(url, headers).json()
        oauth_token = request['access_token']
        refresh_token = request['refresh_token']

        self.user_oauth_token = oauth_token
        self.refresh_token = refresh_token
        edit_config('edit', 'oauthtoken', oauth_token)
        edit_config('edit', 'refreshtoken', refresh_token)

        return oauth_token

    #validates and returns oauth token each time a command is called by the bot
    def get_oauth_token(self):
        self.validate_oauth_token()

        return self.user_oauth_token

    #validates and returns access token each time a command is called by the bot
    def get_access_token(self):
        self.validate_access_token()

        return self.app_access_token

    #validates bot's own oauth token, currently hard coded into program
    def validate_bot_token(self):
        url = 'https://id.twitch.tv/oauth2/validate'
        headers = {'Authorization': f'OAuth {self.bot_token}'}
        
        request = requests.get(url, headers=headers).json()

        try:
            expires_in = request['expires_in']
            if expires_in <= 120:
                return(self.refresh_bot_token())

        except:
            return(self.refresh_bot_token())

    #refreshes bot's oauth token if nearing expiry and updates login file
    def refresh_bot_token(self):
        url = 'https://id.twitch.tv/oauth2/token'
        headers = {'grant_type': 'refresh_token', 'refresh_token': self.bot_refresh_token, 'client_id': self.client_id, 'client_secret': self.client_secret}

        request = requests.post(url, headers).json()
        bot_token = request['access_token']
        bot_refresh_token = request['refresh_token']

        self.bot_token = bot_token
        self.bot_refresh_token = bot_refresh_token
        edit_config('edit', 'botoauthtoken', bot_token)
        edit_config('edit', 'botrefreshtoken', bot_refresh_token)

        return(bot_token)
 
 #local http server that shuts down after receiving one request (can be changed)
class Stoppable_Server(HTTPServer):

    def serve_forever(self):
        self.requests_handled = 0

        while self.requests_handled <= 0:
            self.handle_request()
            self.requests_handled += 1

        self.force_stop

    
    def force_stop(self):
        self.serve_close()

#handles request sent from twitch servers after an user authorizes the bot for the first time, writes authorization code to login file
class Server_Handler(BaseHTTPRequestHandler):
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('content-type', 'text/html')
        self.end_headers
        code = re.search(r"=(\w+)&", self.path.split("code", 1)[1]).group(1)
        edit_config('edit', 'authorizationcode', code)
        self.wfile.write("Authorization Sucessful!".encode("utf-8"))

#called to retrieve or edit specific elements in the login file
def edit_config(action, item, change):

    config = ConfigParser()
    config.read('TwitchLogin.ini')

    username = config.get('Settings', 'username')
    channel = config.get('Settings', 'channel')
    client_id = config.get('Settings', 'clientid')
    client_secret = config.get('Settings', 'clientsecret')
    oauth_token = config.get('Settings', 'oauthtoken')
    access_token = config.get('Settings', 'accesstoken')
    refresh_token = config.get('Settings', 'refreshtoken')
    redirect_uri = config.get('Settings', 'redirecturi')
    authorization_code = config.get('Settings', 'authorizationcode')
    bot_token = config.get('Settings', 'botoauthtoken')
    bot_refresh_token = config.get('Settings', 'botrefreshtoken')

    if action == 'retrieveall':
        return [username, channel, client_id, client_secret, oauth_token, access_token, refresh_token, redirect_uri, authorization_code, bot_token, bot_refresh_token]

    elif action == 'edit':
        config.set('Settings', item, change)
        with open('TwitchLogin.ini', 'w') as configfile:
            config.write(configfile)

    elif action == 'retrieve':
        return [config.get('Settings', item)]
