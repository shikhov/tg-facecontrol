import logging
import asyncio
import random
import regex

from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.utils.text_decorations import html_decoration as hd
from aiogram.utils.keyboard import InlineKeyboardBuilder as KeyboardBuilder
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.client.default import DefaultBotProperties
from dynaconf import ValidationError
from config import config


class Group:
    def __init__(self, chat_id=None, chat=None):
        if chat_id:
            data = config.groups[int(chat_id)]
        elif chat:
            data = config.groups[chat.id]
        else:
            raise('Error object initialization')

        self.emoji_list = regex.findall(r'\X', data.get('emoji_list', config.defaults.emoji_list))
        self.emoji_rowsize = data.get('emoji_rowsize', config.defaults.emoji_rowsize)
        self.welcome_text = data.get('welcome_text', config.defaults.welcome_text)
        self.success_text = data.get('success_text', config.defaults.success_text)
        self.fail_text = data.get('fail_text', config.defaults.fail_text)
        self.error_text = data.get('error_text', config.defaults.error_text)
        self.timeout_text = data.get('timeout_text', config.defaults.timeout_text)
        self.captcha_timeout = data.get('captcha_timeout', config.defaults.captcha_timeout)
        self.delete_joins = data.get('delete_joins', config.defaults.delete_joins)
        self.logchatid = data.get('logchatid', config.defaults.logchatid)

        if chat:
            self.welcome_text = self.welcome_text.replace('%CHAT_TITLE%', chat.title)

    def random_emoji(self):
        return random.sample(self.emoji_list, len(self.emoji_list))

    def is_right_answer(self, answer):
        return answer == self.emoji_list[0]


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

try:
    config.validators.validate_all()
except ValidationError as e:
    print(e.details)
    exit()

group_ids = [group['id'] for group in config.groups]
log_ids = [group['logchatid'] for group in config.groups if 'logchatid' in group]
config.allowed_chats = group_ids + log_ids + [config.defaults.logchatid]
config.groups = {group['id']: group for group in config.groups}


# Initialize bot and dispatcher
bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
router = Router()


async def log(logchatid, text):
    logging.info(text)
    if logchatid:
        try:
            await bot.send_message(logchatid, text)
        except Exception:
            logging.warning(f'Cannot log to chat id: {logchatid}')


async def isChatAllowed(chat: types.Chat):
    if chat.id in config.allowed_chats:
        return True
    if chat.type == 'private':
        return True

    logging.warning(f'chat id {chat.id} ({chat.title}) is not allowed! Leaving chat')
    try:
        await bot.leave_chat(chat.id)
    except Exception:
        pass
    return False


@dp.update.outer_middleware()
async def outer_middleware(handler, event, data):
    chat = getattr(event.event, "chat", None)
    if chat and not await isChatAllowed(chat):
        return

    return await handler(event, data)


@router.message(F.new_chat_members)
async def deleteJoinMessage(message: types.Message):
    if message.chat.id not in config.groups:
        return
    group = Group(chat=message.chat)
    if not group.delete_joins:
        return

    try:
        await message.delete()
    except Exception:
        logging.warning(f'Cannot delete join message in "{message.chat.title}" (no admin rights?)')


@router.chat_join_request()
async def processJoinRequest(update: types.ChatJoinRequest):
    chat = update.chat
    if chat.id not in config.groups:
        logging.warning(f'ChatJoinRequest from unknown group: {chat.id} {chat.title}')
        return
    group = Group(chat=chat)
    user = update.from_user
    logname = f'{hd.quote(user.full_name)} (@{user.username})' if user.username else hd.quote(user.full_name)
    kb = KeyboardBuilder()
    for emoji in group.random_emoji():
        kb.button(text=emoji, callback_data=f"{emoji}#{chat.id}#{chat.username or ''}")
    kb.adjust(group.emoji_rowsize)
    message = await bot.send_message(user.id, group.welcome_text, reply_markup=kb.as_markup())
    await log(group.logchatid, f'{logname} wants to join {chat.title}')
    await asyncio.sleep(group.captcha_timeout)
    try:
        await bot.decline_chat_join_request(chat.id, user.id)
    except Exception:
        return
    await message.edit_text(group.timeout_text)


@router.callback_query()
async def callbackHandler(query: types.CallbackQuery):
    user = query.from_user
    msg_id = query.message.message_id
    logname = f'{hd.quote(user.full_name)} (@{user.username})' if user.username else hd.quote(user.full_name)
    (answer, chat_id, chat_username) = query.data.split('#')
    group = Group(chat_id=chat_id)
    if group.is_right_answer(answer):
        try:
            await bot.approve_chat_join_request(chat_id, user.id)
        except Exception:
            await bot.edit_message_text(group.error_text, chat_id=user.id, message_id=msg_id)
            return

        kb = None
        if chat_username:
            kb = KeyboardBuilder().button(text='Перейти', url='https://t.me/' + chat_username).as_markup()
        await bot.edit_message_text(group.success_text, chat_id=user.id, message_id=msg_id, reply_markup=kb)
        await log(group.logchatid, f'{logname} succeeded')
    else:
        await bot.edit_message_text(group.fail_text, chat_id=user.id, message_id=msg_id)
        try:
            await bot.decline_chat_join_request(chat_id, user.id)
        except Exception:
            return
        await log(group.logchatid, f'{logname} failed')


async def main():
    dp.include_router(router)
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())