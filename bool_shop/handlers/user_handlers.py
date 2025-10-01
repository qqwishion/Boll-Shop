import asyncio
import logging
import aiosqlite
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, CommandObject

import bool_shop.keyboards as kb
from bool_shop.db import get_slot, add_user, create_order, get_order_user, update_order_status, \
    DB_NAME, update_order_address, get_order, update_slot, decrement_slots, \
    get_users_with_orders, get_buyers
from bool_shop.states import OrderFSM
from bool_shop.bot_token import ADMINS

router = Router()
logger = logging.getLogger(__name__)



async def send_start_message(message: Message):
    await message.answer_photo(
        photo="AgACAgIAAxkBAAMLaNuXTNnP-er9DY8Q7WWscxIduh4AAnEJMhvYe9lK9avgKekeP-wBAAMCAAN5AAM2BA",
        caption="Привет! рады, что вы обратились именно к Boll Shop.\n"
                "Если возникли вопросы — пиши в поддержку 👨‍💻",
        reply_markup=kb.start_reply_kb
    )

async def send_about_message(message: Message):
    await message.answer_photo(
        photo="AgACAgIAAxkBAAMLaNuXTNnP-er9DY8Q7WWscxIduh4AAnEJMhvYe9lK9avgKekeP-wBAAMCAAN5AAM2BA",
        caption=f"Привет {message.from_user.username}! В боте ты можешь покупать или заказывать у администратора одежду"
                f"и не только."
                f"\nВсе команды:\n/start - перезапуск бота, пересоздание клавиатуры\n"
                f"/help - команда для просмотра возможностей\n/myorders - тут будут хранится все твои заказы\n\n"
                f"Если возникли какие-то вопросы или предложения писать в поддержку: @BollShop",
        reply_markup=kb.inline_back_kb
    )





@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    await add_user(message.from_user)

    if command.args:
        try:
            slot_id = int(command.args)
            slot = await get_slot(slot_id)
            if slot:
                text = (
                    f"🛒     Вы выбрали товар:\n\n"
                    f"{slot['name']}\n"
                    f"Размер: {slot['size']}\n"
                    f"Цена: {slot['price']}₽"
                )
                await message.answer_photo(photo=slot["png"],
                                           caption=text, parse_mode="HTML",
                                           reply_markup=kb.checkout_button(slot_id)
                                           )
                return
            else:
                await message.answer("❌ Товар не найден.")
        except ValueError:
            await message.answer("⚠ Неверный ID товара.")
    else:
        await send_start_message(message)

@router.callback_query(F.data.startswith("checkout:"))
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split(":")[1])
    slot = await get_slot(slot_id)

    if not slot:
        await callback.answer("❌ Товар не найден", show_alert=True)
        return

    await state.update_data(slot_id=slot_id)

    sizes = slot["size"].split(",") if slot["size"] else ["—"]

    await state.set_state(OrderFSM.waiting_for_size)
    await callback.message.answer(
        f"Вы выбрали товар: {slot['name']}\nВыберите размер:",
        reply_markup=kb.size_keyboard(slot_id, sizes)
    )
    await callback.answer()

@router.callback_query(OrderFSM.waiting_for_size, F.data.startswith("size:"))
async def choose_size(callback: CallbackQuery, state: FSMContext):
    _, slot_id, size = callback.data.split(":")
    slot_id = int(slot_id)

    order_id = await create_order(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        slot_id=slot_id,
        size=size
    )

    await state.update_data(order_id=order_id, size=size, slot_id=slot_id)

    await callback.message.answer(
        f"✅ Заказ #{order_id} создан!\n\n"
        f"💳 Оплатите на карту 2200 1539 9409 0240\n"
        f"и пришлите сюда скрин чека 📸"
    )
    await state.set_state(OrderFSM.waiting_for_proof)
    await callback.answer()






@router.message(Command("help"))
async def cmd_help(message: Message):
    await send_about_message(message)




@router.message(F.text.in_(["🛒Меню", "меню", "Меню"]))
async def menu(message: Message):
    await message.answer_photo(
        photo="AgACAgIAAxkBAAMLaNuXTNnP-er9DY8Q7WWscxIduh4AAnEJMhvYe9lK9avgKekeP-wBAAMCAAN5AAM2BA",
        caption="⬇️ выбери действие ⬇️",
        reply_markup=kb.inline_kb
    )

@router.message(F.text.in_(["☎️Поддержка", "поддержка", "Поддержка"]))
async def support(message: Message):
    await message.answer(
        "Поддержка работает с 9:00 до 21:00 по МСК.\n"
        "Основные сотрудники поддержки:\n      @BollShop",
        reply_markup=kb.inline_back_kb
    )

@router.message(F.text.in_(["📂Каналы", "каналы", "Каналы"]))
async def channels(message: Message):
    await message.answer_photo(
        photo="AgACAgIAAxkBAAMLaNuXTNnP-er9DY8Q7WWscxIduh4AAnEJMhvYe9lK9avgKekeP-wBAAMCAAN5AAM2BA",
        caption="вот все наши каналы:",
        reply_markup=kb.inline_channels_kb
    )

@router.callback_query(F.data.startswith("approve_payment:"))
async def approve_payment(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split(":")[1])

    await update_order_status(order_id, "paid")

    user_id, slot_name = await get_order_user(order_id)
    await callback.message.delete()

    await callback.bot.send_message(
        user_id,
        f"✅ Оплата за {slot_name} подтверждена.\n"
        f"Выберите метод получения:",
        reply_markup=kb.delivery_keyboard(order_id)
    )

    await state.update_data(order_id=order_id)
    await state.set_state(OrderFSM.waiting_for_delivery)

    await callback.answer("Оплата подтверждена ✅")

@router.callback_query(F.data.startswith("reject_payment:"))
async def reject_payment(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])

    user_id, slot_name = await get_order_user(order_id)

    await update_order_status(order_id, "rejected")

    await callback.message.delete()

    await callback.bot.send_message(
        user_id,
        f"❌ Чек за {slot_name} не подтверждён.\n"
        f"Попробуйте ещё раз или обратитесь к администратору - @BollShop."
    )

    await callback.answer("Отметил как ❌ не пришло")


@router.callback_query(F.data.startswith("delivery:"))
async def process_delivery(callback: CallbackQuery, state: FSMContext):
    method, order_id = callback.data.split(":")[1:]
    order_id = int(order_id)

    order = await get_order(order_id)
    if not order:
        return await callback.answer("⚠ Заказ не найден", show_alert=True)

    await state.update_data(order_id=order_id)

    if method == "courier":
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE orders SET delivery = ? WHERE id = ?",
                ("Доставка по МСК", order_id)
            )
            await db.commit()

        await state.set_state(OrderFSM.waiting_for_address)
        await callback.message.answer("🚚 Введите адрес для доставки по Москве:")
        await callback.message.delete()
        return None

    elif method == "avito":
        delivery = "Авито доставка"
        text_user = (
            "📦 Для оформления через Авито перейдите по ссылке и ОБЯЗАТЕЛЬНО пришлите тот же чек в личные сообщения:\n"
            "👉 https://www.avito.ru/moskva/odezhda_obuv_aksessuary/veschi_s_tgk_7652463600?utm_campaign="
            "native&utm_medium=item_page_android&utm_source=soc_sharing_seller"
        )
    elif method == "pickup":
        delivery = "Самовывоз"
        text_user = (
            "🏬 Самовывоз доступен по адресу:\nМосква, метро Новокосино\n\n"
            "📲 Для согласования времени напишите администратору: @BollShop."
        )
    else:
        return await callback.answer("⚠ Неизвестный метод доставки", show_alert=True)

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE orders SET delivery = ?, status = ? WHERE id = ?",
            (delivery, "processing", order_id)
        )
        await db.commit()

        await asyncio.sleep(0.1)
        order = await get_order(order_id)

        await update_order_status(order_id, "processing")
        await remove_size_and_update_channel(callback.bot, order)

        await db.commit()

    await callback.message.delete()
    await callback.message.answer(text_user)

    for admin_id in ADMINS:
        await callback.bot.send_message(
            admin_id,
            f"📦 Заказ #{order['id']}\n"
            f"@{order['username']} (id: {order['user_id']})\n"
            f"{order['slot_name']} — {order['size']}\n"
            f"Способ: {delivery}\n"
            f"Адрес: {order.get('address', '—')}\n"
            f"{order['price']}₽\n\n"
            f"Статус: processing",
            reply_markup=kb.admin_confirm_kb(order_id)
        )

    await callback.answer()
    return None


@router.message(OrderFSM.waiting_for_address)
async def save_address(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    address = message.text
    order = await get_order(order_id)

    await update_order_address(order_id, address)
    await update_order_status(order_id, "processing")
    await remove_size_and_update_channel(message.bot, order)

    order = await get_order(order_id)

    await message.answer("✅ Адрес доставки сохранён. Менеджер свяжется с вами.")
    await state.clear()
    try:
        await message.delete()
    except:
        pass

    order = await get_order(order_id)

    slot = await get_slot(order['slot_id'])
    if slot and slot.get('size'):
        sizes = slot['size'].split(",")
        if order['size'] in sizes:
            sizes.remove(order['size'])
            new_sizes = ",".join(sizes)
            await update_slot(order['slot_id'], "size", new_sizes)

    for admin_id in ADMINS:
        await message.bot.send_message(
            admin_id,
            f"📦 Заказ #{order['id']}\n"
            f"@{order['username']} (id: {order['user_id']})\n"
            f"{order['slot_name']} — {order['size']}\n"
            f"Способ: {order['delivery']}\n"
            f"Адрес: {address}\n"
            f"{order['price']}₽\n\n"
            f"Статус: processing",
            reply_markup=kb.admin_confirm_kb(order_id)
        )


@router.message(F.from_user.id.in_(ADMINS), F.text.regexp(r"^/order(\s+\d+)?$"))
async def cmd_order(message: Message):
    try:
        order_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("⚠ Используй: /order <id>")
        return

    order = await get_order(order_id)
    if not order:
        await message.answer("❌ Заказ не найден")
        return

    text = (
        f"Заказ #{order['id']}\n\n"
        f"@{order['username']} (id: {order['user_id']})\n"
        f"{order['slot_name']} — {order['size']}\n"
        f"{order['price']}₽\n"
        f"{order.get('delivery', '—')}\n"
        f"{order.get('address', '—')}\n\n"
        f"Статус: {order['status']}"
    )

    await message.answer(text, reply_markup=kb.order_manage_kb(order_id))




async def remove_size_and_update_channel(bot, order):
    slot = await get_slot(order['slot_id'])
    if not slot or not slot.get("size"):
        return

    sizes = [s.strip() for s in slot["size"].split(",")]
    selected_size = str(order["size"]).strip()

    if selected_size in sizes:
        sizes.remove(selected_size)
        new_sizes = ",".join(sizes)

        await update_slot(order["slot_id"], "size", new_sizes)

        if slot.get("channel_id") and slot.get("message_id"):
            caption = (
                f"{slot['name']}\n"
                f"Размеры: {new_sizes if new_sizes else 'Нет в наличии'}\n"
                f"Цена: {slot['price']}₽\n"
                f"{slot['description']}\n\n"
                f"👉 Жми кнопку ниже, чтобы заказать!"
            )
            try:
                await bot.edit_message_caption(
                    chat_id=slot["channel_id"],
                    message_id=slot["message_id"],
                    caption=caption,
                    reply_markup=kb.product_button(slot["id"])
                )
            except Exception as e:
                print(f"Ошибка при обновлении поста в ТГК: {e}")


@router.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm(callback: CallbackQuery):
    order_id = int(callback.data.split(":")[1])
    await update_order_status(order_id, "shipped")
    await callback.answer("✅ Заказ отправлен в статус shipped")
    await callback.message.edit_reply_markup()


@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMINS:
        return await callback.answer("⛔ Нет доступа", show_alert=True)

    order_id = int(callback.data.split(":")[1])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE orders SET delivery = NULL, address = NULL, status = 'declined' WHERE id = ?",
            (order_id,)
        )
        await db.commit()

    order = await get_order(order_id)
    if order and order.get("user_id"):
        try:
            await callback.bot.send_message(
                order["user_id"],
                f"❌ Ваш заказ #{order_id} был отклонён администратором. "
                f"Для уточнения подробностей, напишите в поддержку - @BollShop."
            )
        except Exception as e:
            logger.warning(f"Не удалось уведомить пользователя {order['user_id']}: {e}")

    try:
        await state.clear()
    except:
        pass

    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("❌ Заказ отклонён")
    return None


@router.callback_query(F.data.startswith("order_complete:"))
async def order_complete(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return await callback.answer("⛔ Нет доступа", show_alert=True)

    try:
        order_id = int(callback.data.split(":")[1])
    except Exception:
        return await callback.answer("⚠ Неверные данные", show_alert=True)

    await update_order_status(order_id, "completed")

    order = await get_order(order_id)
    if not order:
        return await callback.answer("❌ Заказ не найден", show_alert=True)
    if order:
        await decrement_slots(order['user_id'])

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET buyer = 1 WHERE tg_id = ?", (order['user_id'],))
        await db.commit()

    await callback.message.edit_reply_markup(reply_markup=None)

    await callback.message.answer(f"✅ Заказ #{order_id} успешно завершён")

    try:
        await callback.bot.send_message(
            order["user_id"],
            f"✅ Ваш заказ #{order_id} помечен как выполненный."
        )
    except Exception as e:
        logger.warning(f"Не удалось отправить сообщение пользователю {order['user_id']}: {e}")

    await callback.answer()
    return None


@router.callback_query(F.data.startswith("order_decline:"))
async def order_decline(callback: CallbackQuery):
    if callback.from_user.id not in ADMINS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    try:
        order_id = int(callback.data.split(":")[1])
    except Exception as e:
        logger.exception("Bad callback data for order_decline: %s", callback.data)
        await callback.answer("⚠ Неверные данные", show_alert=True)
        return

    try:
        await update_order_status(order_id, "rejected")
    except Exception as e:
        logger.exception("Failed to update order status to rejected for %s", order_id)
        await callback.answer("❌ Ошибка при обновлении статуса", show_alert=True)
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.exception("Can't edit reply markup for callback message: %s", e)

    await callback.answer("❌ Заказ отклонён")

    try:
        order = await get_order(order_id)
        if order and order.get("user_id"):
            await callback.bot.send_message(order["user_id"], f"❌ Ваш заказ #{order_id} был отклонён.")
    except Exception as e:
        logger.exception("Failed to notify user about declined order: %s", e)

@router.message(Command("check_buyer"))
async def check_buyer(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет доступа.")

    buyers = await get_buyers()
    if not buyers:
        return await message.answer("📭 Нет покупателей.")

    text = "👥 Список покупателей:\n\n"
    for user in buyers:
        text += (
            f"🆔 {user['tg_id']} | @{user['username'] or '—'}\n"
            f"📦 Активные слоты: {user['active_slots']}\n\n"
        )

    await message.answer(text)
    return None


@router.message(Command("check"))
async def check_users(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет доступа.")

    users = await get_users_with_orders()
    if not users:
        return await message.answer("📭 Пользователей нет.")

    text = "👥 Все пользователи:\n\n"
    for u in users:
        text += (
            f"🆔 {u['tg_id']} | @{u['username'] or '—'}\n"
            f"👑 Покупатель: {'✅' if u['buyer'] else '❌'}\n"
            f"📦 Активные слоты: {u['active_slots']}\n\n"
        )

    await message.answer(text)
    return None


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    if callback.data == "catalog":
        await callback.message.answer("Нажата кнопка 📦 Каталог ✅")
    elif callback.data == "back":
        await send_start_message(callback.message)
    elif callback.data == "about":
        await send_about_message(callback.message)

    await callback.answer()

