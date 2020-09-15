import socket
import requests
import re
import random
from configparser import ConfigParser
from authentication import Authenticator
import json
import datetime
import time

class ChatBot: 

	def __init__(self, username, client_id, oauth_token, channel, irc_port, irc_server, authenticator):
	
		self.username = username.lower()
		self.client_id = client_id
		self.oauth_token = oauth_token
		self.channel = '#' + channel.lower()
		self.irc_server = irc_server
		self.irc_port = irc_port
		self.authenticator = authenticator
		self.RAFFLE_STATUS = False #raffle active or inactive
		self.KEYWORD = '' #keyword for raffle
		self.participants = [] #current participants in raffle

	#sends message to twitch server
	def send_command(self, command):
		self.irc.send((command + '\r\n').encode())
	
	def api_request(self, query):
		url = BASE_URL + query
		request_header = {}
		response = requests.get(url, headers=request_header)

	#sends message in twitch chat
	def send_privatemsg(self, channel, text):
		self.send_command(f'PRIVMSG {self.channel} :{text}')

	#connects to twitch chat and receives twitch messages, see twitch_response
	def connect(self):
		self.irc = socket.socket()
		self.irc.connect((self.irc_server, self.irc_port))

		self.send_command(f'PASS {self.oauth_token}')
		self.send_command(f'NICK {self.username}')
		self.send_command(f'Join {self.channel}')
		self.send_command(f'CAP REQ :twitch.tv/tags')
		print(f'Joining ' + self.channel)
		self.twitch_response(self.channel)
		
	#loops while bot is connected to stream messages, sends PONG in response to PING to prevent timeout
	def twitch_response(self, channel):
		while True:
			received_msgs = self.irc.recv(2048).decode()
			for msg in received_msgs.split('\r\n'):
				if msg == 'PING :tmi.twitch.tv':
					self.send_command(f'PONG')
				else:
					self.handle_message(msg, self.channel)

	#handles received twitch messages
	def handle_message(self, msg, channel):
		if msg.strip():
			message = self.parse_message(msg)
			print(f'> {message}')

	#splits twitch messages into user and text, see find_user and find_text
	def parse_message(self, msg):
		user = self.find_user(msg)

		if user:
			message = self.find_text(msg, user)
			return (f'{user} : {message}')
		else:
			return msg

	#returns the user that sent the message, currently does not handle capitalization correctly due to IRC request info
	def find_user(self, msg):
		try: 
			user = re.search(r"\b!(\w+)@", msg)
			return (user.group(1))
		except:
			return('')

	#returns the message that the user send, checks to see if it contains command and executes if true
	def find_text(self, msg, user):
		text = msg.partition(f'{self.channel} :')[2]
		cmd = self.is_command(text)

		ignore_commands = ConfigParser()
		ignore_commands.read('Commands.ini')
		excluded_commands = ignore_commands.get('Commands', 'Excluded').split(', ')
		for command in excluded_commands:
			command = command.lower()

		#excludes commands that are handled by other bots to prevent conflicts
		if cmd and cmd not in excluded_commands:                            
			permission_needed = self.check_command(cmd)

			#checks if command exists
			if permission_needed.strip():
				#checks to see if user has permission to execute command, see check_user_permission
				if self.check_user_permission(msg, permission_needed.strip().lower()) or user == self.username:
					self.do_command(cmd, user, text)
				else:
					self.send_privatemsg(self.channel, f'You do not have permission to use that command! {permission_needed} role is needed. Kappa')
			else:
				self.send_privatemsg(self.channel, "Invalid command.")

		return text

	#checks to see if text contains command
	def is_command(self, msg):
		command = msg.split(' ', 1)[0].partition('!')[2].lower()
		return command

	#checks to see if command is valid, returns permission needed to access command, see 'Commands.ini' for commands
	def check_command(self, cmd):
		command_list = retrieve_commands()
		if cmd in command_list[0]:
			return 'Global'
		elif cmd in command_list[1]:
			return 'VIP'
		elif cmd in command_list[2]:
			return 'Subscriber'
		elif cmd in command_list[3]:
			return 'Moderator'
		elif cmd in command_list[4]:
			return 'Broadcaster'
		else:
			return ''

	#checks to see if user has the required permission to perform command
	def check_user_permission(self, msg, permission):
		badges = msg.split('badges=', 1)[1].split(';', 1)[0].lower()

		if permission == 'global':
			return True

		elif permission == 'vip': 
			if re.search(r"(vip|subscriber|moderator|broadcaster)", badges):
				return True
			else:
				return False

		elif permission == 'subscriber':
			if re.search(r"(subscriber|moderator|broadcaster)", badges):
				return True
			else:
				return False

		elif permission == 'moderator':
			if re.search(r"(moderator|broadcaster)", badges):
				return True
			else:
				return False

		elif permission == 'broadcaster':
			if re.search(r"(broadcaster)", badges):
				return True
			else:
				return False
	
	#executes commands
	def do_command(self, cmd, user, text):
		
		if cmd == 'commands':
			command_list = retrieve_commands()
			all_commands = "Available Commands: "
			for permission_level in command_list:
				for command in permission_level:
					all_commands += f'!{command.lower()}, '
			self.send_privatemsg(self.channel, all_commands[:-2])
		
		#displays discord server link
		elif cmd == 'discord':
			self.send_privatemsg(self.channel, "Come join our Discord! ") #change link here

		#help for beat saber song requests
		elif cmd == 'bsrhelp':
			self.send_privatemsg(self.channel, "Find the song on https://bsaber.com and click the twitch icon by the map you want to request. Paste the result into Twitch chat to add to queue.")

		#notifies streamer that viewer is lurking
		elif cmd == 'lurk':
			self.send_privatemsg(self.channel, f'{user} thanks for the lurk! <3')
		
		#allows viewer to hug a target
		elif cmd == 'hug':
			target = find_target(text)
			if target:
				self.send_privatemsg(self.channel, f'{user} hugs {target} with all the love in the world. <3')
			else:
				self.send_privatemsg(self.channel, f'{user}' " couldn\'t find anyone to " f'{cmd}.')

		#randomly generates a wholesomeness percent, can be also used on another target
		elif cmd == 'wholesome':
			percent = random.randint(1,100)
			target = find_target(text)
			if target:
				self.send_privatemsg(self.channel, f'{target} is {percent}% wholesome.')
			else:
				self.send_privatemsg(self.channel, f'{user} is {percent}% wholesome.')

		#allows user to slap a target with a random weapon, weapon options can be updated in the list below
		elif cmd == 'slap':
			weapon_list = ["with a taser? monkaHmm I dont think that's how it works.", 
							"with some nunchucks. Why do I have them? No clue, ask your face.", 
							"with a baseball bat... Wow (user) yeeted (target)!",
							"with a katana... Brutal, I think (target) is missing some limbs...",
							"with Mjolnir but was unsuccessful as (user) could not pick it up. Kappa",
							"with an energy blade... (target) was disintegrated. FeelsBadMan",
							"with a bagel. Yum!",
							"with a cheesecake. I hope (target) likes cake."]
			weapon_index = random.randint(0, len(weapon_list) - 1)
			target = find_target(text)
			if target:
					action = weapon_list[weapon_index]
					action = action.replace('(user)', f'{user}')
					action = action.replace('(target)', f'{target}')
					self.send_privatemsg(self.channel, f'{user} slapped {target} {action}')
			else:
				self.send_privatemsg(self.channel, f'{user}' " couldn\'t find anyone to " f'{cmd}.')

		#provides a shoutout in chat for the target, calls twitch api to find the target's last game streamed
		elif cmd == 'so':
			target = find_target(text)
			target_url = 'twitch.tv/' + target.lower()
			if target:
				token = self.get_token('oauth token')
				try:
					game_id = self.get_channel(token, {'query': target})['data'][0]['game_id']
					channel_last_played = self.get_game(token, {'id': game_id})['data'][0]['name']
	
					self.send_privatemsg(self.channel, f'Please follow {target} at {target_url}! They were last seen playing {channel_last_played}.')
				except:
					print("No previous games found.")

		#calculates the amount of time that a user has been following the channel, uses UTC time, resets once a user unfollows (twitch api)
		elif cmd == 'followage':
			token = self.get_token('oauth token')
			broadcaster_id = self.get_user_id(token, {'login': self.channel.split('#', 1)[1]})['data'][0]['id']
			user_id = self.get_user_id(token, {'login': user})['data'][0]['id']		
			try:
				followed_at = self.get_follow_info(token, {'from_id': user_id, 'to_id': broadcaster_id})['data'][0]['followed_at']
				followed_at = time.strptime(followed_at, '%Y-%m-%dT%H:%M:%SZ')

				current_utc_time = datetime.datetime.now(tz = datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
				current_utc_time = time.strptime(current_utc_time, '%Y-%m-%dT%H:%M:%SZ')

				followed_time = time.mktime(current_utc_time) - time.mktime(followed_at)
				followage = [int(followed_time/86400), int((followed_time%86400)/3600), int(((followed_time%86400)%3600)/60), int((((followed_time%86400)%3600)%60))]

				self.send_privatemsg(self.channel, f'{user} has been following for {followage[0]} days, {followage[1]} hours, {followage[2]} minutes, and {followage[3]} seconds!')
			except:
				self.send_privatemsg(self.channel, f'{user} is currently not following. :(')
			
		#calculates the amount of time that the channel has been live in the current session, also based on UTC
		elif cmd == 'uptime':
			token = self.get_token('oauth token')
			channel = self.channel.split('#', 1)[1]
			try:
				started_at = self.get_stream(token, {'user_login': channel})['data'][0]['started_at']
				started_at = time.strptime(started_at, '%Y-%m-%dT%H:%M:%SZ')

				current_utc_time = datetime.datetime.now(tz = datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
				current_utc_time = time.strptime(current_utc_time, '%Y-%m-%dT%H:%M:%SZ')

				uptime = time.mktime(current_utc_time) - time.mktime(started_at)
				total_uptime = [int(uptime/3600), int((uptime%3600)/60), int((uptime%3600)%60)]

				self.send_privatemsg(self.channel, f'{channel} has been streaming for {total_uptime[0]} hours, {total_uptime[1]} minutes, and {total_uptime[2]} seconds!')
			except:
				self.send_privatemsg(self.channel, f'{channel} is currently not online.')
			
		#provides link to the computer setup
		elif cmd == 'setup':
			url = '' #update link here
			self.send_privatemsg(self.channel, f'PCPartPicker: {url}')

		#starts raffle, only one can be active at a time
		elif cmd == 'raffle':
			if self.RAFFLE_STATUS == False:
				self.RAFFLE_STATUS = True
				self.send_privatemsg(self.channel, "Raffle is starting now! Goodluck everyone!")
			else:
				self.send_privatemsg(self.channel, "There is already a raffle in progress!")
		
		#sets up the keyword that users must use to join the raffle, only one can be active at a time
		elif cmd == 'keyword':
			if self.RAFFLE_STATUS == True:
				if self.KEYWORD:
					self.send_privatemsg(self.channel, "There is already a keyword!")
				else:
					self.KEYWORD = text.split(' ', 1)[1].lower()
					self.send_privatemsg(self.channel, f'{self.KEYWORD} set as the keyword. Type !join and the keyword to join the raffle!')
			else:
				self.send_privatemsg(self.channel, "No raffles found!")

		#allows an user to join an existing raffle if they enter the correct keyword
		elif cmd == 'join':
			if self.RAFFLE_STATUS == False:
				self.send_privatemsg(self.channel, "No raffles in progress.")
			else:
				try:
					if text.split(' ', 1)[1].lower() == self.KEYWORD:
						self.participants.append(user)
						print(self.participants)
						self.send_privatemsg(self.channel, f'{user} has joined the raffle!')
					else:
						self.send_privatemsg(self.channel, "No keyword found. Try again.")
				except:
					self.send_privatemsg(self.channel, "No keyword found. Try again.")

		#ends raffle without drawing a winner, resets raffle status
		elif cmd == 'endraffle':
			if self.RAFFLE_STATUS == False:
				self.send_privatemsg(self.channel, "No raffles in progress.")
			else:
				self.send_privatemsg(self.channel, "Raffle ended.")
				self.participants = []
				self.RAFFLE_STATUS = False
				self.KEYWORD = ''

		#randomly draws a winner from the participants and resets raffle status, might add additional ability to draw multiple winners (can only win once)
		elif cmd == 'winner':
			if self.RAFFLE_STATUS == True:
				number_of_participants = len(self.participants) - 1
				if number_of_participants:
					self.send_privatemsg(self.channel, "There are currently no participants in the raffle. Try again later.")
				else:
					index = random.randint(0, len(self.participants) - 1)
					winner = self.participants[index]
					self.send_privatemsg(self.channel, f'Congratulations! {winner} has won the raffle!')
					self.participants = []
					self.RAFFLE_STATUS = False
					self.KEYWORD = ''
			else:
				self.send_privatemsg(self.channel, "No raffles in progress.")

		#changes the current game being played on twitch (channel info)		
		elif cmd == 'game':
			token = self.get_token('oauth token')
			broadcaster_id = self.get_user_id(token, {'login': self.channel.split('#', 1)[1]})['data'][0]['id']
			try:
				new_game = str.title(text.split(' ', 1)[1])
				new_game_id = self.get_game(token, {'name': new_game})['data'][0]['id']
				self.change_channel_info(token, {'broadcaster_id': broadcaster_id, 'game_id': new_game_id})
				self.send_privatemsg(self.channel, f'Current game set to {new_game}.')
			except:
				self.send_privatemsg(self.channel, "Invalid game")

		#changes the current title of stream (channel info)
		elif cmd == 'title':
			token = self.get_token('oauth token')
			broadcaster_id = self.get_user_id(token, {'login': self.channel.split('#', 1)[1]})['data'][0]['id']
			try:
				new_title = str.title(text.split(" ", 1)[1])
				print(new_title)
				self.change_channel_info(token, {'broadcaster_id': broadcaster_id, 'title': new_title})
				self.send_privatemsg(self.channel, f'Current title set to "{new_title}".')
			except:
				self.send_privatemsg(self.channel, "No title detected.")
	
	#----------------------LIST OF TWITCH API REQUESTS AND CALLS----------------------

	#retrieves channel information regarding a single or multiple users, retrieve only
	def get_channel(self, token, params):
		url = 'https://api.twitch.tv/helix/search/channels'
		headers = {'client-id': self.client_id, 'Authorization': f'Bearer {token}'}
		
		request = self.get_request(url, headers, params)
		
		return request

	#retrieves a game id or game name based on id, retrieve only
	def get_game(self, token, params):
		url = 'https://api.twitch.tv/helix/games'
		headers = {'client-id': self.client_id, 'Authorization': f'Bearer {token}'}
		request = self.get_request(url, headers, params)

		return request

	#retrieves information about any twitch account including id, date created, global roles, and etc, retrieve only
	def get_user_id(self, token, params):
		url = 'https://api.twitch.tv/helix/users'
		headers = {'client-id': self.client_id, 'Authorization': f'Bearer {token}'}
		
		request = self.get_request(url, headers, params)

		return request

	#retrieves a list of people that follow an user or a list of people that an user follows, can also determine if two individuals are following each other including the initial date, retrieve only
	def get_follow_info(self, token, params):
		url = 'https://api.twitch.tv/helix/users/follows'
		headers = {'client-id': self.client_id, 'Authorization': f'Bearer {token}'}

		request = self.get_request(url, headers, params)
		
		return request

	#retrieves information about one or more streams, must be live or returns empty values, retrieve only
	def get_stream(self, token, params):
		url = 'https://api.twitch.tv/helix/streams'
		headers = {'client-id': self.client_id, 'Authorization': f'Bearer {token}'}

		request = self.get_request(url, headers, params)

		return request

	#retrieves channel game and title, can also be used to change these values, retrieve and edit
	def change_channel_info(self, token, params):
		url = 'https://api.twitch.tv/helix/channels'
		headers = {'client-id': self.client_id, 'Authorization': f'Bearer {token}'}

		request = self.patch_request(url, headers, params)

		return request

	#used to get an oauth or access token from authenticator class based on parameters
	def get_token(self, token_type):

		if token_type == 'oauth token':
			return self.authenticator.get_oauth_token()
		if token_type == 'access token':
			return self.authenticator.get_access_token()

	#formats get request for twitch api calls
	def get_request(self, url, headers, params):
		
		if params:
			request = requests.get(url, headers=headers, params=params).json()
			
		else:
			request = requests.get(url, headers=headers).json()

		return request

	#formats patch requests for twitch api calls
	def patch_request(self, url, headers, params):
		
		request = requests.patch(url, headers=headers, params=params)
		
		return request

#reads command.ini and returns list of commands sorted by permission required
def retrieve_commands():
	commands = ConfigParser()
	commands.read('Commands.ini')

	command_list = [[], [], [], [], []]

	command_list[0] = (commands.get('Commands', 'Global').split(', '))
	command_list[1] = (commands.get('Commands', 'VIP').split(', '))
	command_list[2] = (commands.get('Commands', 'Subscriber').split(', '))
	command_list[3] = (commands.get('Commands', 'Moderator').split(', '))
	command_list[4] = (commands.get('Commands', 'Broadcaster').split(', '))	

	return command_list

#finds mention of end target user for command actions
def find_target(text):
	try:
		target = re.search(r"@(\w+)\b", text).group(1)
		return target
	except:
		return ''

def main():
	
	#reads login info from file
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
	
	#creates authenticator based on login info to generate and refresh tokens if needed
	Twitch_Authenticator = Authenticator(username, channel, client_id, client_secret, oauth_token, access_token, refresh_token, redirect_uri, authorization_code, bot_token, bot_refresh_token)
	
	#checks oauth token to see if it's valid
	new_user_token = Twitch_Authenticator.token_check()
	if new_user_token:
		oauth_token = new_user_token

	#checks bot's oauth token to see if it's valid
	new_bot_token = Twitch_Authenticator.validate_bot_token()
	if new_bot_token:
		bot_token = new_bot_token

	irc_server = 'irc.chat.twitch.tv'
	irc_port = 6667

	#bot intiates using the bot's oauth token or else the script will use the streamer's account to send messages in chat
	twitch_bot = ChatBot(username, client_id, f'oauth:{bot_token}', channel, irc_port, irc_server, Twitch_Authenticator)
	twitch_bot.connect()
	
if __name__ == "__main__":
	main()