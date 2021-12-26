# -*- coding: utf-8 -*-

import datetime
import os
import asyncio
import traceback
from threading import Thread

import BotInnerApi
import BotOutterApi
import VkApi


class AsyncLoopThread(Thread):
	def __init__(self):
		super().__init__(daemon=True)
		self.loop = asyncio.new_event_loop()

	def run(self):
		asyncio.set_event_loop(self.loop)
		self.loop.run_forever()


async def await_post(user_session, session):
	while True:
		print('Wait time to post')
		t = datetime.datetime.today()
		need_time = datetime.datetime(t.year, t.month, t.day, int(os.environ.get('RATING_TIME')), 0)
		if t.hour >= int(os.environ.get('RATING_TIME')):
			need_time += datetime.timedelta(days=1)
		# await asyncio.sleep((need_time - t).seconds)
		# await asyncio.sleep(1000)
		if daily_post(user_session, session):
			print('posted')
		else:
			print('fail posting')
		await asyncio.sleep(1000)


def daily_post(user_session, session):
	try:
		group_list = BotInnerApi.load_list()
		ban_list = BotInnerApi.load_banlist()
		groups_data = BotInnerApi.load_groups_data()

		info = BotInnerApi.get_info(list(group_list.keys()), groups_data, user_session)
		BotInnerApi.save_groups_data(BotInnerApi.take_groups_data(info))

		cleaned_info = []
		for group_info in info:
			if not group_info['passes']:
				if group_info['id'] in ban_list:
					group_list = {key: val for key, val in group_list.items() if val != group_info['id']}
				else:
					ban_list.append(group_info['id'])
					cleaned_info.append(group_info)
					msg = 'Ваша группа не прошла автомодерацию. Убедитесь, что она удовлетворяет правилам CBR. ' +\
						'Если она не пройдет ее вновь, то будет удалена из рейтинга'
					try:
						VkApi.send_message(msg, session, group_list[group_info['id']])
					except Exception:
						traceback.format_exc()
			else:
				cleaned_info.append(group_info)
		BotInnerApi.save_banlist(ban_list)
		BotInnerApi.save_list(group_list)

		content = BotInnerApi.create_post_content(cleaned_info, 'subs', user_session)
		VkApi.post(
			content['text'],
			user_session,
			photos_ready=[VkApi.upload_photo_to_post(content['photo'], user_session)]
		)

		if datetime.date.isoweekday(datetime.datetime.today()) == int(os.environ.get('LIKE_RATING_DAY')):
			content = BotInnerApi.create_post_content(cleaned_info, 'likes', user_session)
			VkApi.post(content['text'], user_session, photos_ready=[content['photo']])

		return True
	except Exception:
		# print('\nDAILY POST ERROR:', repr(ee))
		print(traceback.format_exc())
		return False


async def process_event(event, session, user_session):
	try:
		if VkApi.is_event_form(event.type):
			request_type = BotOutterApi.get_request_type(event)
			if request_type == 'add':
				BotOutterApi.add_request_notify(event, session, user_session)
			elif request_type == 'remove':
				BotOutterApi.remove_request_notify(event, session, user_session)
		elif VkApi.is_event_message(event.type):
			BotOutterApi.process_request(BotInnerApi.load_list(), event, session)
	except Exception:
		# print('\nLONGPOLL EVENT ERROR:', repr(ee))
		print(traceback.format_exc())


async def main():
	looph = AsyncLoopThread()
	looph.start()

	user_session = VkApi.create_user_session()
	vk_group_api = VkApi.create_session()
	session = vk_group_api['session']
	longpoll = vk_group_api['longpoll']

	asyncio.run_coroutine_threadsafe(await_post(user_session, session), looph.loop)

	for event in longpoll.listen():
		asyncio.run_coroutine_threadsafe(process_event(event, session, user_session), looph.loop)


if __name__ == '__main__':
	while True:
		try:
			asyncio.run(main())
		except Exception:
			# print(e)
			print(traceback.format_exc())
			continue
