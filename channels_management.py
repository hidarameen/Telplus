#!/usr/bin/env python3
"""
دوال إدارة القنوات
"""

import json
import logging
import re
from datetime import datetime
from telethon import Button
from database.channels_db import ChannelsDatabase

logger = logging.getLogger(__name__)

class ChannelsManagement:
	"""إدارة القنوات"""
	
	def __init__(self, bot):
		self.bot = bot
		self.core_db = bot.db
		self.channels_db = ChannelsDatabase(bot.db)

	async def _notify(self, event, text: str):
		"""Safely notify user: use CallbackQuery.answer if available, else send/edit a message."""
		try:
			if hasattr(event, 'answer'):
				await event.answer(text)
				return
		except Exception:
			pass
		# Fallback for NewMessage events
		await self.bot.edit_or_send_message(event, text)

	async def show_channels_menu(self, event):
		"""Show channels management menu"""
		user_id = event.sender_id
		
		# Check if user is authenticated
		if not self.core_db.is_user_authenticated(user_id):
			await self.bot.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً لإدارة القنوات")
			return

		# Get channels count
		channels = self.channels_db.get_user_channels(user_id)
		channels_count = len(channels)
		admin_channels = len([c for c in channels if c.get('is_admin', False)])
		member_channels = channels_count - admin_channels

		buttons = [
			[Button.inline("➕ إضافة قناة", b"add_channel")],
			[Button.inline("📋 قائمة القنوات", b"list_channels")],
			[Button.inline("🔙 رجوع لإدارة المهام", b"manage_tasks")]
		]

		message_text = (
			f"📺 إدارة القنوات\n\n"
			f"📊 الإحصائيات:\n"
			f"• إجمالي القنوات: {channels_count}\n"
			f"• قنوات مشرف: {admin_channels}\n"
			f"• قنوات عضو: {member_channels}\n\n"
			f"💡 الميزات:\n"
			f"• إضافة قناة واحدة أو عدة قنوات دفعة واحدة عبر إدخال متعدد الأسطر\n"
			f"• عرض قائمة القنوات مع الصلاحيات\n"
			f"• استخدام القنوات كمصادر أو أهداف في المهام\n"
			f"• عرض أسماء القنوات بدلاً من الأرقام\n\n"
			f"اختر إجراء:"
		)
		
		await self.bot.edit_or_send_message(event, message_text, buttons=buttons)

	async def start_add_channel(self, event):
		"""Start adding a single channel"""
		user_id = event.sender_id

		# Check if user is authenticated
		if not self.core_db.is_user_authenticated(user_id):
			await self.bot.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً لإضافة قنوات")
			return

		# Set conversation state
		self.core_db.set_conversation_state(user_id, 'waiting_channel_link', json.dumps({}))

		buttons = [
			[Button.inline("📎 أرسل رابط/معرف/رقم أو قم بتوجيه رسالة من القناة", b"noop")],
			[Button.inline("❌ إلغاء", b"manage_channels")]
		]

		message_text = (
			"➕ إضافة قناة جديدة\n\n"
			"📋 أرسل إحدى الصيغ التالية أو قم بتوجيه رسالة من القناة:\n\n"
			"• رابط: https://t.me/channel_name\n"
			"• معرف: @channel_name\n"
			"• رقم: -1001234567890\n\n"
			"✳️ يمكنك أيضاً إرسال عدة قنوات في رسالة واحدة، كل قناة في سطر منفصل.\n"
			"سيتم إضافة جميع القنوات دفعة واحدة دون الحاجة لزر منفصل.\n\n"
			"💡 يمكنك أيضًا توجيه أي رسالة منشورة من القناة وسنستخرج القناة تلقائيًا"
		)
		
		await self.bot.edit_or_send_message(event, message_text, buttons=buttons)

	async def start_add_multiple_channels(self, event):
		"""Start adding multiple channels"""
		user_id = event.sender_id

		# Check if user is authenticated
		if not self.core_db.is_user_authenticated(user_id):
			await self.bot.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً لإضافة قنوات")
			return

		# Set conversation state
		self.core_db.set_conversation_state(user_id, 'waiting_multiple_channels', json.dumps({'channels': []}))

		buttons = [
			[Button.inline("✅ إنهاء الإضافة", b"finish_add_channels")],
			[Button.inline("❌ إلغاء", b"manage_channels")]
		]

		message_text = (
			"📤 إضافة عدة قنوات دفعة واحدة\n\n"
			"📋 **الخطوة 1: إرسال روابط القنوات**\n\n"
			"أرسل روابط القنوات واحداً تلو الآخر:\n\n"
			"• رابط القناة: (مثال: https://t.me/channel_name)\n"
			"• أو معرف القناة: (مثال: @channel_name)\n"
			"• أو رقم القناة: (مثال: -1001234567890)\n\n"
			"💡 ملاحظات:\n"
			"• أرسل رابط واحد في كل رسالة\n"
			"• اضغط 'إنهاء الإضافة' عند الانتهاء\n"
			"• يجب أن تكون عضو في القنوات أو مشرف عليها"
		)
		
		await self.bot.edit_or_send_message(event, message_text, buttons=buttons)

	async def list_channels(self, event):
		"""List user channels"""
		user_id = event.sender_id

		# Check if user is authenticated
		if not self.core_db.is_user_authenticated(user_id):
			await self.bot.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً لعرض القنوات")
			return

		channels = self.channels_db.get_user_channels(user_id)

		# Try to resolve real names for channels missing names when UserBot is connected (best-effort)
		try:
			from userbot_service.userbot import userbot_instance
			client = userbot_instance.clients.get(user_id)
			if client:
				for ch in channels:
					# Consider placeholders like 'قناة 123', 'source', 'target' as missing names
					name_value = str(ch.get('chat_name') or '').strip()
					name_missing = (not name_value) or name_value.startswith('قناة ') or name_value.lower() in ['source', 'target']
					if name_missing:
						try:
							chat = await client.get_entity(int(ch['chat_id']))
							new_name = getattr(chat, 'title', None) or getattr(chat, 'username', None) or str(ch['chat_id'])
							if new_name and new_name != ch.get('chat_name'):
								self.channels_db.update_channel_info(ch['chat_id'], user_id, {
									'chat_name': new_name,
									'username': getattr(chat, 'username', None),
								})
								ch['chat_name'] = new_name
						except Exception:
							pass
		except Exception:
			pass

		if not channels:
			buttons = [
				[Button.inline("➕ إضافة قناة", b"add_channel")],
				[Button.inline("🔙 رجوع لإدارة القنوات", b"manage_channels")]
			]

			message_text = (
				"📋 قائمة القنوات\n\n"
				"❌ لا توجد قنوات مضافة حالياً\n\n"
				"أضف قنواتك الأولى للبدء!"
			)
			
			await self.bot.edit_or_send_message(event, message_text, buttons=buttons)
			return

		# Build buttons list with real names per channel
		message = "📋 قائمة القنوات:\n\nاختر قناة لإدارتها:" 
		buttons = []

		for channel in channels[:30]:  # cap to avoid huge keyboards
			channel_id = channel.get('chat_id', 'غير محدد')
			channel_name = channel.get('chat_name') or str(channel_id)
			is_admin = channel.get('is_admin', False)
			status_icon = "👑" if is_admin else "👤"
			# Single button per channel opens edit menu
			buttons.append([Button.inline(f"{status_icon} {channel_name}", f"edit_channel_{channel_id}".encode())])

		# Add navigation buttons
		if len(channels) > 10:
			message += f"\n📄 عرض 1-10 من {len(channels)} قناة"
			buttons.append([Button.inline("📄 الصفحة التالية", b"channels_next_page")])

		buttons.extend([
			[Button.inline("➕ إضافة قناة", b"add_channel")],
			[Button.inline("🔙 رجوع لإدارة القنوات", b"manage_channels")]
		])

		await self.bot.edit_or_send_message(event, message, buttons=buttons)

	async def delete_channel(self, event, channel_id):
		"""Delete a specific channel"""
		user_id = event.sender_id
		
		try:
			# Get channel info before deletion
			channel = self.channels_db.get_channel_info(channel_id, user_id)
			if not channel:
				await self._notify(event, "❌ القناة غير موجودة")
				return

			channel_name = channel.get('chat_name', f'قناة {channel_id}')
			
			# Delete channel
			success = self.channels_db.delete_channel(channel_id, user_id)
			
			if success:
				await self._notify(event, f"✅ تم حذف القناة: {channel_name}")
				# Refresh channels list
				await self.list_channels(event)
			else:
				await self._notify(event, "❌ فشل في حذف القناة")
				
		except Exception as e:
			logger.error(f"❌ خطأ في حذف القناة: {e}")
			await self._notify(event, "❌ حدث خطأ في حذف القناة")

	async def edit_channel(self, event, channel_id):
		"""Edit channel information"""
		user_id = event.sender_id
		
		try:
			# Get channel info
			channel = self.channels_db.get_channel_info(channel_id, user_id)
			if not channel:
				await self._notify(event, "❌ القناة غير موجودة")
				return

			channel_name = channel.get('chat_name', f'قناة {channel_id}')
			is_admin = channel.get('is_admin', False)
			status_icon = "👑" if is_admin else "👤"
			status_text = "مشرف" if is_admin else "عضو"

			buttons = [
				[Button.inline("🔄 تحديث المعلومات", f"refresh_channel_{channel_id}".encode())],
				[Button.inline("🗑️ حذف القناة", f"delete_channel_{channel_id}".encode())],
				[Button.inline("🔙 رجوع لقائمة القنوات", b"list_channels")]
			]

			message_text = (
				f"✏️ تعديل القناة\n\n"
				f"📺 **{channel_name}**\n"
				f"📊 الصلاحية: {status_icon} {status_text}\n"
				f"🆔 المعرف: `{channel_id}`\n\n"
				f"اختر إجراء:"
			)

			await self.bot.edit_or_send_message(event, message_text, buttons=buttons)
				
		except Exception as e:
			logger.error(f"❌ خطأ في تعديل القناة: {e}")
			await event.answer("❌ حدث خطأ في تعديل القناة")

	async def refresh_channel_info(self, event, channel_id):
		"""Refresh channel information from Telegram"""
		user_id = event.sender_id
		
		try:
			# Get updated channel info from Telegram
			from userbot_service.userbot import userbot_instance
			
			if user_id not in userbot_instance.clients:
				await event.answer("❌ UserBot غير متصل. يرجى إعادة تسجيل الدخول")
				return

			client = userbot_instance.clients[user_id]
			
			# Try to get channel info
			try:
				chat = await client.get_entity(int(channel_id))
				new_name = getattr(chat, 'title', None) or getattr(chat, 'username', None) or str(channel_id)
				
				# Update channel info in database
				success = self.channels_db.update_channel_info(channel_id, user_id, {
					'chat_name': new_name,
					'username': getattr(chat, 'username', None),
					'updated_at': datetime.now().isoformat()
				})
				
				if success:
					await event.answer(f"✅ تم تحديث معلومات القناة: {new_name}")
					# Refresh channel edit page
					await self.edit_channel(event, channel_id)
				else:
					await event.answer("❌ فشل في تحديث معلومات القناة")
					
			except Exception as e:
				logger.error(f"❌ خطأ في الحصول على معلومات القناة من Telegram: {e}")
				await self._notify(event, "❌ لا يمكن الوصول للقناة. تأكد من أنك عضو فيها")
				
		except Exception as e:
			logger.error(f"❌ خطأ في تحديث معلومات القناة: {e}")
			await self._notify(event, "❌ حدث خطأ في تحديث معلومات القناة")

	async def finish_add_channels(self, event):
		"""Finish adding multiple channels"""
		user_id = event.sender_id
		
		try:
			# Get current state (tuple)
			state_tuple = self.core_db.get_conversation_state(user_id)
			if not state_tuple:
				await self._notify(event, "❌ لا توجد عملية إضافة قنوات نشطة")
				return

			state, data_str = state_tuple
			if state != 'waiting_multiple_channels':
				await self._notify(event, "❌ لا توجد عملية إضافة قنوات نشطة")
				return

			try:
				data_json = json.loads(data_str) if data_str else {}
			except Exception:
				data_json = {}

			channels = data_json.get('channels', [])
			
			if not channels:
				await self._notify(event, "❌ لم يتم إضافة أي قنوات")
				# Clear state and return to channels menu
				self.core_db.clear_conversation_state(user_id)
				await self.show_channels_menu(event)
				return

			# Clear state
			self.core_db.clear_conversation_state(user_id)
			
			# Show summary
			buttons = [
				[Button.inline("📋 عرض القنوات", b"list_channels")],
				[Button.inline("➕ إضافة المزيد", b"add_channel")],
				[Button.inline("🔙 رجوع لإدارة القنوات", b"manage_channels")]
			]

			message_text = (
				f"✅ تم إضافة {len(channels)} قناة بنجاح!\n\n"
				f"📋 القنوات المضافة:\n"
			)
			
			for i, channel in enumerate(channels[:5], 1):  # Show first 5
				channel_name = channel.get('chat_name', f"قناة {channel.get('chat_id')}")
				message_text += f"{i}. {channel_name}\n"
			
			if len(channels) > 5:
				message_text += f"... و {len(channels) - 5} قناة أخرى\n"
			
			message_text += "\nاختر إجراء:"

			await self.bot.edit_or_send_message(event, message_text, buttons=buttons)
				
		except Exception as e:
			logger.error(f"❌ خطأ في إنهاء إضافة القنوات: {e}")
			await self._notify(event, "❌ حدث خطأ في إنهاء إضافة القنوات")

	async def process_channel_link(self, event, channel_link, silent: bool = False):
		"""Process channel link and add to database"""
		user_id = event.sender_id
		
		try:
			link = str(channel_link).strip()
			# 1) Numeric ID fast-path (accept -100... or digits)
			if re.fullmatch(r"-?\d+", link):
				try:
					channel_id = int(link)
					channel_name = f"قناة {channel_id}"
					username = None
					is_admin = False
					# Add without remote lookup (useful for private channels)
					success = self.channels_db.add_channel(user_id, channel_id, channel_name, username, is_admin)
					if success:
						# Best-effort: try resolving real name via UserBot and update the record
						try:
							from userbot_service.userbot import userbot_instance
							client = userbot_instance.clients.get(user_id)
							if client:
								try:
									chat = await client.get_entity(channel_id)
									# Try to join (ignored if already a participant)
									try:
										from telethon.tl.functions.channels import JoinChannelRequest
										await client(JoinChannelRequest(chat))
									except Exception:
										pass
									resolved_name = getattr(chat, 'title', None) or getattr(chat, 'username', None) or str(channel_id)
									resolved_is_admin = False
									try:
										participants = await client.get_participants(chat)
										for p in participants:
											if getattr(p, 'id', None) == user_id:
												resolved_is_admin = getattr(p, 'admin_rights', None) is not None
												break
									except Exception:
										pass
									self.channels_db.update_channel_info(channel_id, user_id, {
										'chat_name': resolved_name,
										'username': getattr(chat, 'username', None),
										'is_admin': resolved_is_admin,
									})
									channel_name = resolved_name
									is_admin = resolved_is_admin
								except Exception:
									pass
						except Exception:
							pass
						if not silent:
							await self._notify(event, f"✅ تم إضافة القناة بالمعرف: {channel_id}")
						return {
							'chat_id': channel_id,
							'chat_name': channel_name,
							'username': username,
							'is_admin': is_admin
						}
					else:
						if not silent:
							await self._notify(event, "❌ فشل في إضافة القناة")
						return False
				except Exception as e:
					logger.error(f"❌ خطأ في معالجة معرف القناة: {e}")
					if not silent:
						await self._notify(event, "❌ حدث خطأ في معالجة معرف القناة")
					return False

			# 2) Resolve link/username using UserBot
			from userbot_service.userbot import userbot_instance
			if user_id not in userbot_instance.clients:
				if not silent:
					await self._notify(event, "❌ UserBot غير متصل. يرجى إعادة تسجيل الدخول")
				return False

			client = userbot_instance.clients[user_id]
			channel_id = None
			channel_name = None
			username = None
			try:
				# If it's a private invite link, try to import invite and join
				if isinstance(link, str) and ("t.me/+" in link or "/joinchat/" in link or link.strip().startswith("+")):
					try:
						from telethon.tl.functions.messages import ImportChatInviteRequest
						invite_hash = link.split("+")[-1].split("/")[-1]
						await client(ImportChatInviteRequest(invite_hash))
					except Exception:
						pass

				chat = await client.get_entity(link)
				channel_id = chat.id
				channel_name = getattr(chat, 'title', None) or getattr(chat, 'username', None) or str(channel_id)
				username = getattr(chat, 'username', None)
				# Ensure joined and detect admin status
				is_admin = False
				try:
					from telethon.tl.functions.channels import JoinChannelRequest
					await client(JoinChannelRequest(chat))
				except Exception:
					pass
				try:
					participants = await client.get_participants(chat)
					for p in participants:
						if getattr(p, 'id', None) == user_id:
							is_admin = getattr(p, 'admin_rights', None) is not None
							break
				except Exception:
					pass
			except Exception as e:
				logger.error(f"❌ خطأ في الحصول على معلومات القناة: {e}")
				if not silent:
					await self._notify(event, "❌ لا يمكن الوصول للقناة. تأكد من صحة الرابط وأنك عضو فيها")
				return False

			# Add channel to database
			success = self.channels_db.add_channel(user_id, channel_id, channel_name, username, is_admin)
			if success:
				status_text = "مشرف" if is_admin else "عضو"
				if not silent:
					await self._notify(event, f"✅ تم إضافة القناة: {channel_name} ({status_text})")
				return {
					'chat_id': channel_id,
					'chat_name': channel_name,
					'username': username,
					'is_admin': is_admin
				}
			else:
				if not silent:
					await self._notify(event, "❌ فشل في إضافة القناة. قد تكون مضافة مسبقاً")
				return False
				
		except Exception as e:
			logger.error(f"❌ خطأ في معالجة رابط القناة: {e}")
			if not silent:
				await self._notify(event, "❌ حدث خطأ في معالجة رابط القناة")
			return False

	async def show_channel_selection(self, event, task_id, selection_type):
		"""Show channel selection for sources/targets"""
		user_id = event.sender_id
		
		# Check if user is authenticated
		if not self.core_db.is_user_authenticated(user_id):
			await self._notify(event, "❌ يجب تسجيل الدخول أولاً")
			return

		channels = self.channels_db.get_user_channels(user_id)

		if not channels:
			buttons = [
				[Button.inline("➕ إضافة قناة", b"add_channel")],
				[Button.inline("🔙 رجوع", f"task_manage_{task_id}")]
			]

			message_text = (
				f"📺 اختيار {selection_type}\n\n"
				f"❌ لا توجد قنوات مضافة حالياً\n\n"
				f"أضف قنواتك أولاً لاستخدامها ك{selection_type}"
			)
			
			await self.bot.edit_or_send_message(event, message_text, buttons=buttons)
			return

		# Build channel selection list
		message = f"📺 اختر {selection_type}:\n\n"
		buttons = []

		for i, channel in enumerate(channels, 1):
			channel_id = channel.get('chat_id', 'غير محدد')
			channel_name = channel.get('chat_name', f'قناة {channel_id}')
			is_admin = channel.get('is_admin', False)
			status_icon = "👑" if is_admin else "👤"

			message += f"{i}. {status_icon} {channel_name}\n"
			# Put the status icon next to the channel name on the button itself
			buttons.append([Button.inline(f"{status_icon} {channel_name}", f"select_{selection_type}_{channel_id}_{task_id}")])

		# Add navigation buttons
		buttons.extend([
			[Button.inline("➕ إضافة قناة جديدة", b"add_channel")],
			[Button.inline("🔙 رجوع", f"task_manage_{task_id}")]
		])

		await self.bot.edit_or_send_message(event, message, buttons=buttons)