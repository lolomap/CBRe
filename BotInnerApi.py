# -*- coding: utf-8 -*-
import datetime
import os
import pickle
import random
import time

import matplotlib as mpl

import BotOutterApi

mpl.use('Agg')
import matplotlib.pyplot as pyplot
import io

import VkApi


def save_list(groups_list):
	with open('list', 'wb') as f:
		pickle.dump(groups_list, f)


def load_list():
	try:
		with open('list', 'rb') as f:
			return pickle.load(f)
	except FileNotFoundError:
		return {}


def save_banlist(groups_list):
	with open('banlist', 'wb') as f:
		pickle.dump(groups_list, f)


def load_banlist():
	try:
		with open('banlist', 'rb') as f:
			return pickle.load(f)
	except FileNotFoundError:
		return []


def save_groups_data(subs):
	with open('groupsdata', 'wb') as f:
		pickle.dump(subs, f)


def load_groups_data():
	try:
		with open('groupsdata', 'rb') as f:
			return pickle.load(f)
	except FileNotFoundError:
		return {'last': {}, 'deltas': {}, 'all': {}, 'likes': {}}


def generate_plot(info):
	delta_sort_info = sorted(info, key=lambda x: x['delta'], reverse=True)[:5]

	fig, pl = pyplot.subplots()
	pyplot.title('График роста подписчиков', fontweight='bold')
	pyplot.xlabel('Дни')
	pyplot.ylabel('Подписчики в день')

	for group_info in delta_sort_info:
		try:
			xs = []
			ys = []
			for item in group_info['all']:
				xs.append(datetime.datetime.date(item['date']).day)
				ys.append(item['value'])

			pl.plot(xs, ys, label=group_info['name'])
		except KeyError:
			pass

	pl.legend(title='Самые быстрорастущие\nгруппы за последние сутки', bbox_to_anchor=(1.05, 1), ncol=1)
	pl.minorticks_on()
	pl.grid(which='major')
	pl.grid(which='minor', linestyle=':')

	buffer = io.BytesIO()
	fig.savefig(buffer, format='jpg', bbox_inches='tight')
	buffer.seek(0)
	return buffer


def get_likes(group_id, user_session):
	posts = VkApi.get_posts(user_session, group_id, 100)
	# time.sleep(0.5)
	likes_total = 0
	for post in posts:
		likes_total += post['likes']['count']
	return likes_total


def get_info(groups_list, groups_data, user_session):
	groups = VkApi.get_groups_info(groups_list, user_session, optional=True)
	info = []
	time.sleep(2)
	for group in groups:
		delta = group['members_count'] - groups_data['last'].get(group['screen_name'], group['members_count'])
		likes = get_likes(group['screen_name'], user_session)
		group_info = {
			'id': group['screen_name'],
			'name': group['name'],
			'subs': group['members_count'],
			'delta': delta,
			'likes': likes,
			'delta_likes': likes - groups_data['likes'].get(group['screen_name'], 0)
		}

		if group['screen_name'] in list(groups_data['all'].keys()):
			group_info['all'] = []
			for old_delta in groups_data['all'][group['screen_name']]:
				group_info['all'].append(old_delta)
			group_info['all'].append({'value': delta, 'date': datetime.datetime.today()})
		else:
			group_info['all'] = [{'value': delta, 'date': datetime.datetime.today()}]
		group_info['passes'] = BotOutterApi.group_moderate(group, user_session)
		info.append(group_info)
		time.sleep(0.5)
	return info


def take_groups_data(info):
	last_subs = {}
	delta_subs = {}
	all_subs = {}
	likes = {}
	for group_info in info:
		last_subs[group_info['id']] = group_info['subs']
		delta_subs[group_info['id']] = group_info['delta']
		all_subs[group_info['id']] = group_info['all']
		likes[group_info['id']] = group_info['likes']
	return {'last': last_subs, 'deltas': delta_subs, 'all': all_subs, 'likes': likes}


def create_post_content(info, mode, user_session):
	if mode == 'subs':
		post_text = 'Рейтинг групп на сегодня:\n\n'
		subs_sort_info = sorted(info, key=lambda x: x['subs'], reverse=True)

		i = 1
		for group_info in subs_sort_info:
			delta_sign = ''
			if group_info['delta'] > 0:
				post_text += '📈 '
				delta_sign = '+'
			elif group_info['delta'] < 0:
				post_text += '📉 '
			else:
				post_text += '⏸ '

			post_text += str(i) + '. '
			# post_text += '[' + group_info['id'] + '|'
			post_text += group_info['name'] + ']: ' + str(group_info['subs']) + \
				' (' + delta_sign + str(group_info['delta']) + ')\n'

			i += 1

		plot = generate_plot(info)

		return {'text': post_text, 'photo': plot}
	elif mode == 'likes':
		post_text = 'Актуальный топ лайков за неделю.\n\n'
		likes_sort_info = sorted(info, key=lambda x: x['delta_likes'], reverse=True)

		i = 1
		for group_info in likes_sort_info:
			post_text += str(i) + '. '
			# post_text += '[' + group_info['id'] + '|'
			post_text += group_info['name'] + ']: ' + str(group_info['delta_likes']) + '❤\n'
			i += 1

		photo = VkApi.upload_photo('likes', user_session)

		return {'text': post_text, 'photo': photo}