import os, random, asyncio, time, re, pytz, json, logging
from datetime import datetime
from Script import script
from database.users_db import db
from pyrogram import Client, filters
from pyrogram.errors import FloodWait
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from info import (
    BOT_USERNAME, URL, BATCH_PROTECT_CONTENT, ADMINS, PROTECT_CONTENT,
    OWNER_USERNAME, SUPPORT, PICS, FILE_PIC, CHANNEL, VERIFIED_LOG,
    LOG_CHANNEL, FSUB, BIN_CHANNEL, VERIFY_EXPIRE, BATCH_FILE_CAPTION,
    FILE_CAPTION, VERIFY_IMG, QR_CODE
)
from web.utils.file_properties import get_hash
from utils import get_readable_time, verify_user, check_token, get_size
from web.utils import StartTime, __version__
from plugins.rexbots import is_user_joined, rx_verification, rx_x_verification

logger = logging.getLogger(__name__)
BATCH_FILES = {}


# ================= START COMMAND =================
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):

    if not message.from_user:
        return

    user_id = message.from_user.id
    mention = message.from_user.mention
    me2 = (await client.get_me()).mention

    # ---------- FORCE SUB ----------
    if FSUB:
        if not await is_user_joined(client, message):
            return

    # ---------- SAVE USER ----------
    if not await db.is_user_exist(user_id):
        await db.add_user(user_id, message.from_user.first_name)
        await client.send_message(
            LOG_CHANNEL,
            script.LOG_TEXT.format(me2, user_id, mention)
        )

    # ---------- NORMAL START ----------
    if len(message.command) == 1:
        buttons = [[
            InlineKeyboardButton('• ᴜᴘᴅᴀᴛᴇᴅ •', url=CHANNEL),
            InlineKeyboardButton('• sᴜᴘᴘᴏʀᴛ •', url=SUPPORT)
        ], [
            InlineKeyboardButton('• ʜᴇʟᴘ •', callback_data='help'),
            InlineKeyboardButton('• ᴀʙᴏᴜᴛ •', callback_data='about')
        ]]

        return await message.reply_photo(
            photo=PICS,
            caption=script.START_TXT.format(mention, BOT_USERNAME),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ================= DEEP LINK =================
    msg = message.command[1]

    # ---------- SINGLE FILE ----------
    if msg.startswith("file_"):

        if not await rx_x_verification(client, message):
            return

        _, file_id = msg.split("_", 1)

        try:
            original_message = await client.get_messages(int(BIN_CHANNEL), int(file_id))
            media = original_message.document or original_message.video or original_message.audio

            caption = FILE_CAPTION.format(
                CHANNEL,
                media.file_name if media else "File"
            )

            return await client.copy_message(
                chat_id=user_id,
                from_chat_id=int(BIN_CHANNEL),
                message_id=int(file_id),
                caption=caption,
                protect_content=PROTECT_CONTENT
            )

        except Exception as e:
            logger.error(f"File send error: {e}")
            return await message.reply("❌ File not found or deleted.")

    # ---------- BATCH FILE ----------
    if msg.startswith("BATCH-"):

        if not await rx_x_verification(client, message):
            return

        file_id = msg.split("-", 1)[1]
        sts = await message.reply("<b>Please wait...</b>")

        msgs = BATCH_FILES.get(file_id)

        if not msgs:
            try:
                downloaded_file = await client.download_media(file_id)

                with open(downloaded_file, "r", encoding="utf-8") as f:
                    msgs = json.load(f)

                os.remove(downloaded_file)
                BATCH_FILES[file_id] = msgs

            except Exception as e:
                logger.error(f"Batch load error: {e}")
                await sts.edit("❌ FAILED to load batch file.")
                return

        for msg_data in msgs:

            title = msg_data.get("title", "Untitled")
            size = get_size(int(msg_data.get("size", 0)))

            f_caption = BATCH_FILE_CAPTION.format(
                CHANNEL,
                file_name=title,
                file_size=size,
                file_caption=""
            )

            try:
                await client.send_cached_media(
                    chat_id=user_id,
                    file_id=msg_data.get("file_id"),
                    caption=f_caption,
                    protect_content=BATCH_PROTECT_CONTENT
                )
                await asyncio.sleep(1)

            except FloodWait as e:
                await asyncio.sleep(e.value)

            except Exception:
                continue

        await sts.delete()


# ================= CALLBACK HANDLER =================
@Client.on_callback_query()
async def cb_handler(client, query):

    if query.data == "close_data":
        return await query.message.delete()

    # ---------- START ----------
    if query.data == "start":
        buttons = [[
            InlineKeyboardButton(' ᴜᴘᴅᴀᴛᴇᴅ ', url=CHANNEL),
            InlineKeyboardButton(' sᴜᴘᴘᴏʀᴛ ', url=SUPPORT)
        ], [
            InlineKeyboardButton(' ʜᴇʟᴘ ', callback_data='help'),
            InlineKeyboardButton(' ᴀʙᴏᴜᴛ ', callback_data='about')
        ]]

        return await query.message.edit_caption(
            caption=script.START_TXT.format(query.from_user.mention, BOT_USERNAME),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ---------- ABOUT ----------
    if query.data == "about":
        me2 = (await client.get_me()).mention

        buttons = [
            [InlineKeyboardButton('💻 Creator', url='https://t.me/cantarellabots')],
            [
                InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start'),
                InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
            ]
        ]

        return await query.message.edit_caption(
            caption=script.ABOUT_TXT.format(
                me2,
                me2,
                get_readable_time(time.time() - StartTime),
                __version__
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ---------- HELP ----------
    if query.data == "help":
        buttons = [
            [InlineKeyboardButton('• ᴀᴅᴍɪɴ •', callback_data='admincmd')],
            [
                InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start'),
                InlineKeyboardButton('• ᴄʟᴏsᴇ •', callback_data='close_data')
            ]
        ]

        return await query.message.edit_caption(
            caption=script.HELP_TXT,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ---------- ADMIN ----------
    if query.data == "admincmd":

        if query.from_user.id not in ADMINS:
            return await query.answer("Admins Only!", show_alert=True)

        buttons = [[InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start')]]

        return await query.message.edit_caption(
            caption=script.ADMIN_CMD_TXT,
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # ---------- FILE PAGINATION ----------
    if query.data.startswith("filespage_"):

        page = int(query.data.split("_")[1])
        user_id = query.from_user.id

        files, total = await db.get_user_files(user_id, page)

        if not files:
            return await query.answer("⚠️ No files found.", show_alert=True)

        btn = []

        for file in files:
            btn.append([
                InlineKeyboardButton(
                    file["file_name"],
                    callback_data=f"fileinfo_{file['file_id']}"
                )
            ])

        nav_btns = []

        if page > 1:
            nav_btns.append(
                InlineKeyboardButton("⬅️ Back", callback_data=f"filespage_{page-1}")
            )

        if total > (page * 7):
            nav_btns.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"filespage_{page+1}")
            )

        if nav_btns:
            btn.append(nav_btns)

        btn.append([InlineKeyboardButton('• ʜᴏᴍᴇ •', callback_data='start')])

        return await query.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(btn)
        )
