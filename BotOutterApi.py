# -*- coding: utf-8 -*-
import datetime
import json
import os

import pytz

import BotInnerApi
import VkApi


def get_request_type(event):
	if event.obj['form_id'] == 1:
		return 'add'
	elif event.obj['form_id'] == 2:
		return 'remove'
	else:
		return 'unknown'


def add_request_notify(event, session, user_session):
	from_id = event.obj['user_id']
	link = event.obj['answers'][0]['answer']
	ginfo = VkApi.get_groups_info([link.split('/')[-1]], user_session, optional=True)[0]
	if not group_moderate(ginfo, user_session):
		msg = 'Похоже группа из вашей заявки не прошла автомодерацию CBRG. ' +\
			'Проверьте соответствует ли группа правилам CBR'
		VkApi.send_message(msg, session, from_id)
		return

	text = 'Заявка на добавление в рейтинг' +\
		'\nОт: vk.com/id' + str(from_id) +\
		'\nГруппа: [' + ginfo['screen_name'] + '|' + ginfo['name'] + ']'
	photo = VkApi.get_photo_to_send(ginfo['photo_200'], session, int(os.environ.get('USER_NOTIFY')))

	buttons = [
		{
			'text': 'Принять',
			'payload_key': ginfo['screen_name'],
			'payload_value': [1, from_id]
		},
		{
			'text': 'Отклонить',
			'payload_key': ginfo['screen_name'],
			'payload_value': [0, from_id]
		}
	]

	VkApi.send_message_attach(text, session, int(os.environ.get('USER_NOTIFY')), photo=photo, buttons=buttons)


def remove_request_notify(event, session, user_session):
	from_id = event.obj['user_id']
	link = event.obj['answers'][0]['answer']
	ginfo = VkApi.get_groups_info([link.split('/')[-1]], user_session, optional=True)[0]

	text = 'Заявка на удаление из рейтинга' +\
		'\nОт: vk.com/id' + str(from_id) +\
		'\nГруппа: [' + ginfo['screen_name'] + '|' + ginfo['name'] + ']'
	photo = VkApi.get_photo_to_send(ginfo['photo_200'], session, int(os.environ.get('USER_NOTIFY')))

	buttons = [
		{
			'text': 'Принять',
			'payload_key': ginfo['screen_name'],
			'payload_value': [-1, from_id]
		},
		{
			'text': 'Отклонить',
			'payload_key': ginfo['screen_name'],
			'payload_value': [0, from_id]
		}
	]

	VkApi.send_message_attach(text, session, int(os.environ.get('USER_NOTIFY')), photo=photo, buttons=buttons)


def process_request(groups_list, groups_data, event, session):
	if 'payload' not in event.obj['message'].keys():
		if event.obj['message']['from_id'] == int(os.environ.get('USER_NOTIFY')):
			if event.obj['message']['text'] == 'сброс':
				BotInnerApi.save_groups_data({'last': {}, 'deltas': {}, 'all': {}, 'likes': {}})
			if event.obj['message']['text'] == 'бэкап':
				BotInnerApi.set_list()
			if event.obj['message']['text'] == 'амнистия':
				BotInnerApi.save_banlist([])
			if event.obj['message']['text'] == 'list':
				print(groups_list)
			if event.obj['message']['text'] == 'data':
				print(groups_data)
		return

	payload = json.loads(event.obj['message']['payload'])
	if list(payload.values())[0][0] == 1 and not (list(payload.keys())[0] in groups_list):
		groups_list[list(payload.keys())[0]] = list(payload.values())[0][1]
		BotInnerApi.save_list(groups_list)
		VkApi.send_message('Группа из вашей заявки добавлена в список CBR', session, list(payload.values())[0][1])
	elif list(payload.values())[0][0] == -1 and list(payload.keys())[0] in groups_list:
		del groups_list[list(payload.keys())[0]]
		BotInnerApi.save_list(groups_list)
		VkApi.send_message('Группа из вашей заявки удалена из списка CBR', session, list(payload.values())[0][1])
	else:
		VkApi.send_message('Ваша заявка в CBR отклонена модератором', session, list(payload.values())[0][1])
	VkApi.send_message('Обработано', session, event.obj['message']['from_id'])


def group_moderate(group_info, user_session):
	try:
		is_open = (group_info['is_closed'] == 0)
		is_able = not ('deactivated' in list(group_info.keys()))
		is_members_open = ('members_count' in list(group_info.keys()))
		post_time = VkApi.get_last_post(user_session, group_info['screen_name'])['date']
		three_month_ago = (datetime.datetime.now(pytz.timezone('Europe/Moscow')) - datetime.timedelta(days=90)).timestamp()
		is_active = post_time - three_month_ago
		return is_open and is_members_open and is_able and (is_active > 0)
	except Exception as e:
		print(repr(e))
		return True
