# -*- coding: utf-8 -*-
import asyncio
import json
import os
import random
import time
import traceback

import requests

import vk
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def upload_photo(name, user_session):
    photo_server = user_session.photos.getWallUploadServer(group_id=int(os.environ.get('GROUP_ID')),
                                                           v=str(os.environ.get('API_VERSION')))
    upload_url = photo_server['upload_url']
    if name == 'likes':
        img = {'photo': ('like_post_pic.png', open('likes.png', 'rb'))}
    else:
        raise Exception('Wrong photo name')
    response = requests.post(upload_url, files=img)
    result = json.loads(response.text)
    photo = user_session.photos.saveWallPhoto(photo=result['photo'],
                                              hash=result['hash'],
                                              server=result['server'],
                                              group_id=int(os.environ.get('GROUP_ID')),
                                              v=str(os.environ.get('API_VERSION')))
    return photo


def create_session():
    token = os.environ.get('GROUP_TOKEN')
    g_id = int(os.environ.get('GROUP_ID'))

    api = vk_api.VkApi(token=token)
    longpoll = VkBotLongPoll(api, g_id)
    session = api.get_api()
    print('session created')
    return {'session': session, 'longpoll': longpoll}


def create_user_session():
    session = vk.Session(access_token=os.environ.get('USER_TOKEN'))
    api = vk.API(session)
    return api


def get_groups_info(ids, user_session, optional=False):
    result = []
    for gid in ids:
        try:
            result.append(user_session.groups.getById(group_id=gid,
                                                      fields='members_count',
                                                      v=str(os.environ.get('API_VERSION')))[0])
        except Exception:
            traceback.format_exc()
        time.sleep(0.5)
    return result


def get_photo_to_send(url, session, uid):
    photo_file = session.photos.getMessagesUploadServer(peer_id=uid)
    r_data = {'photo': (str(random.randint(10, 100000)) + '.jpg', requests.get(url).content)}
    photo_data = requests.post(photo_file['upload_url'], files=r_data).json()
    photo = session.photos.saveMessagesPhoto(server=photo_data['server'],
                                             photo=photo_data['photo'],
                                             hash=photo_data['hash'])[0]
    return photo


def get_photo_to_post(url, user_session):
    photo_file = user_session.photos.getWallUploadServer(group_id=int(os.environ.get('GROUP_ID')),
                                                         v=str(os.environ.get('API_VERSION')))
    r_data = {'photo': (str(random.randint(10, 100000)) + '.jpg', requests.get(url).content)}
    photo_data = requests.post(photo_file['upload_url'], files=r_data).json()
    photo = user_session.photos.saveWallPhoto(server=photo_data['server'],
                                              photo=photo_data['photo'],
                                              hash=photo_data['hash'],
                                              group_id=int(os.environ.get('GROUP_ID')),
                                              v=str(os.environ.get('API_VERSION')))[0]
    return photo


def upload_photo_to_post(photo_b, user_session):
    photo_file = user_session.photos.getWallUploadServer(group_id=int(os.environ.get('GROUP_ID')),
                                                         v=str(os.environ.get('API_VERSION')))
    r_data = {'photo': (str(random.randint(10, 100000)) + '.jpg', photo_b)}
    photo_data = requests.post(photo_file['upload_url'], files=r_data).json()
    photo = user_session.photos.saveWallPhoto(server=photo_data['server'],
                                              photo=photo_data['photo'],
                                              hash=photo_data['hash'],
                                              group_id=int(os.environ.get('GROUP_ID')),
                                              v=str(os.environ.get('API_VERSION')))[0]
    return photo


def get_chat_users(msg, session):
    users = session.messages.getConversationMembers(peer_id=msg['peer_id'])
    profiles = []
    for user in users['profiles']:
        profiles.append(user['id'])
    return profiles


def get_user_id(short_name, session):
    return session.users.get(user_ids=short_name)[0]['id']


def get_group_id(short_name, session):
    return session.groups.getById(group_id=short_name)[0]['id']


def can_send_to_user(session, uid):
    return session.users.get(user_ids=uid, fields='can_write_private_message')[0]['can_write_private_message']


def get_posts(user_session, group_id, count):
    return user_session.wall.get(domain=group_id, count=count, v=os.environ.get('API_VERSION'))['items']


def get_last_post(user_session, group_id):
    posts = user_session.wall.get(domain=group_id, count=2, v=os.environ.get('API_VERSION'))['items']
    if len(posts) == 1 or not ('is_pinned' in list(posts[0].keys())):
        return posts[0]
    else:
        return posts[1]


def send_message(msg, session, uid):
    if can_send_to_user(session, uid):
        session.messages.send(peer_id=uid,
                              message=msg,
                              random_id=random.randint(100000, 999999))


def send_message_attach(msg, session, uid, photo=None, buttons=None):
    if can_send_to_user(session, uid):
        attach = ''
        keyboard = VkKeyboard(inline=True)
        if photo is not None:
            attach = 'photo' + str(photo['owner_id']) + '_' + str(photo['id']) + ','
        if buttons is not None:
            for button in buttons:
                keyboard.add_button(button['text'], VkKeyboardColor.PRIMARY,
                                    payload=json.dumps({button['payload_key']: button['payload_value']}))

        session.messages.send(peer_id=uid,
                              message=msg,
                              attachment=attach,
                              keyboard=keyboard.get_keyboard(),
                              random_id=random.randint(100000, 999999))


def send_lazy_photo(msg, photo_url, session, uid):
    if can_send_to_user(session, uid):
        photo = get_photo_to_send(photo_url, session, uid)
        send_message_attach(msg, session, uid, photo=photo)


def post(text, user_session, photos_url=None, photos_ready=None):
    if photos_ready is None and photos_url is None:
        user_session.wall.post(owner_id=str(-1 * int(int(os.environ.get('GROUP_ID')))), from_group=1, message=text,
                               v=str(os.environ.get('API_VERSION')))
    elif photos_ready is not None:
        photos = ''
        for photo in photos_ready:
            photos += 'photo' + str(photo['owner_id']) + '_' + str(photo['id']) + ','
        photos = photos[:-1]
        user_session.wall.post(owner_id=str(-1 * int(int(os.environ.get('GROUP_ID')))), from_group=1, message=text,
                               attachment=photos,
                               v=str(os.environ.get('API_VERSION')))
    else:
        photos = ''
        for url in photos_url:
            photo = get_photo_to_post(url, user_session)
            photos += 'photo' + str(photo['owner_id']) + '_' + str(photo['id']) + ','
        photos = photos[:-1]
        user_session.wall.post(owner_id=str(-1 * int(int(os.environ.get('GROUP_ID')))), from_group=1, message=text,
                               attachment=photos,
                               v=str(os.environ.get('API_VERSION')))


def repost(obj, msg, user_session, group_id=None, mark_as_ads=None):
    if mark_as_ads is None:
        is_ads = False
    else:
        is_ads = mark_as_ads

    if group_id is not None:
        user_session.wall.repost(object=obj, message=msg, mark_as_ads=is_ads, group_id=group_id,
                                 v=str(os.environ.get('API_VERSION')))
    else:
        user_session.wall.repost(object=obj, message=msg, mark_as_ads=is_ads,
                                 v=str(os.environ.get('API_VERSION')))


def is_event_message(event):
    return event == VkBotEventType.MESSAGE_NEW


def is_event_form(event):
    return event == 'lead_forms_new'
