import logging
import asyncio
import random
import regex

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, Chat, ChatJoinRequest, CallbackQuery
from aiogram.utils.text_decorations import html_decoration as hd
from aiogram.utils.keyboard import InlineKeyboardBuilder as KBuilder
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.client.default import DefaultBotProperties
from dynaconf import ValidationError
from config import config


class Group:
    def __init__(self, message: Message = None, request: ChatJoinRequest = None, callback: CallbackQuery = None):
        if message:
            data = config.groups[message.chat.id]
        elif request:
            data = config.groups[request.chat.id]
        elif callback:
            (self.answer, self.chat_id, self.chat_username) = callback.data.split('#')
            data = config.groups[int(self.chat_id)]
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

        if message:
            self.message = message
            self.user = message.from_user

        if request:
            self.chat = request.chat
            self.user = request.from_user
            self.key = f'{self.chat.id}_{self.user.id}'
            self.welcome_text = self.welcome_text.replace('%CHAT_TITLE%', self.chat.title)

        if callback:
            self.user = callback.from_user
            self.key = f'{self.chat_id}_{self.user.id}'
            self.msg_id = callback.message.message_id

        self.loguser = f'{self.user.full_name} @{self.user.username}' if self.user.username else self.user.full_name
        self.loguser = hd.quote(self.loguser)

    def is_right_answer(self):
        return self.answer == self.emoji_list[0]

    def buttons(self):
        kb = KBuilder()
        for emoji in random.sample(self.emoji_list, len(self.emoji_list)):
            kb.button(text=emoji, callback_data=f"{emoji}#{self.chat.id}#{self.chat.username or ''}")
        kb.adjust(self.emoji_rowsize)
        return kb.as_markup()

    def chat_link_button(self):
        if self.chat_username:
            kb = KBuilder().button(text='Перейти', url=f'https://t.me/{self.chat_username}')
            return kb.as_markup()
        return None

    async def send_captcha(self):
        if self.key in active_requests:
            return
        message = await bot.send_message(self.user.id, self.welcome_text, reply_markup=self.buttons())
        active_requests[self.key] = message.message_id
        await self.log(f'{self.loguser} is trying to join {self.chat.title}')
        await asyncio.sleep(self.captcha_timeout)

        if active_requests.get(self.key, 0) != message.message_id:
            return

        active_requests.pop(self.key, None)
        try:
            await bot.decline_chat_join_request(self.chat.id, self.user.id)
        except Exception:
            pass
        await message.edit_text(self.timeout_text)

    async def handle_callback(self):
        active_requests.pop(self.key, None)
        if self.is_right_answer():
            try:
                await bot.approve_chat_join_request(self.chat_id, self.user.id)
            except Exception:
                await bot.edit_message_text(self.error_text, chat_id=self.user.id, message_id=self.msg_id)
                return

            await bot.edit_message_text(
                text=self.success_text,
                chat_id=self.user.id,
                message_id=self.msg_id,
                reply_markup=self.chat_link_button()
            )
            await self.log(f'{self.loguser} succeeded')
        else:
            await bot.edit_message_text(self.fail_text, chat_id=self.user.id, message_id=self.msg_id)
            try:
                await bot.decline_chat_join_request(self.chat_id, self.user.id)
            except Exception:
                return
            await self.log(f'{self.loguser} failed')

    async def handle_join(self):
        if self.delete_joins:
            try:
                await self.message.delete()
            except Exception:
                logging.warning(f'Cannot delete join message in "{self.message.chat.title}" (no admin rights?)')

    async def log(self, text):
        logging.info(text)
        if self.logchatid:
            try:
                await bot.send_message(self.logchatid, text)
            except Exception:
                logging.warning(f'Cannot log to chat id: {self.logchatid}')


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

try:
    config.validators.validate_all()
except ValidationError as e:
    print(e.details)
    exit()

config.allowed_chats = \
    [group['id'] for group in config.groups] + \
    [group['logchatid'] for group in config.groups if 'logchatid' in group] + \
    [config.defaults.logchatid]
config.groups = {group['id']: group for group in config.groups}
active_requests = {}

# Initialize bot and dispatcher
bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()


async def is_chat_allowed(chat: Chat):
    if chat.id in config.allowed_chats:
        return True
    if chat.type == 'private':
        return True

    logging.warning(f'Chat id {chat.id} ({chat.title}) is not allowed! Leaving chat')
    try:
        await chat.leave()
    except Exception:
        pass
    return False


@dp.update.outer_middleware()
async def outer_middleware(handler, event, data):
    chat = getattr(event.event, 'chat', None)
    if chat and not await is_chat_allowed(chat):
        return
    return await handler(event, data)


@dp.message(F.new_chat_members)
async def join_message_handler(message: Message):
    if message.chat.id in config.groups:
        await Group(message=message).handle_join()


@dp.chat_join_request()
async def join_request_handler(request: ChatJoinRequest):
    if request.chat.id in config.groups:
        await Group(request=request).send_captcha()


@dp.callback_query()
async def callback_handler(callback: CallbackQuery):
    await Group(callback=callback).handle_callback()


async def main():
    dp.callback_query.middleware(CallbackAnswerMiddleware())
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())