from aiogram import  Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from bool_shop.db import add_slot, get_slots, delete_slot, reset_slots, get_all_orders, \
    get_slot, update_slot, update_slot_size, get_all_orders_history
from bool_shop.states import EditSlotForm, AddSlot, AdminFSM
import bool_shop.keyboards as kb
from bool_shop.bot_token import ADMINS, CHANNEL_ID

router = Router()



# ---------- Управление слотами ----------

@router.message(Command("addslot"))
async def add_slot_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет доступа.")

    await message.answer("📌 Введи название товара:")
    await state.set_state(AddSlot.waiting_name)
    return None

@router.message(AddSlot.waiting_name)
async def slot_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите цену:")
    await state.set_state(AddSlot.waiting_price)


@router.message(AddSlot.waiting_price)
async def slot_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await message.answer("Отправь фото товара:")
    await state.set_state(AddSlot.waiting_png)


@router.message(AddSlot.waiting_png, F.photo)
async def slot_png(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(png=file_id)
    await message.answer("Укажи размеры через запятую (например: 40, 41, 42):")
    await state.set_state(AddSlot.waiting_sizes)




@router.message(AddSlot.waiting_sizes)
async def slot_sizes(message: Message, state: FSMContext):
    sizes_text = message.text
    sizes_list = [s.strip() for s in sizes_text.split(",")]
    await state.update_data(size=",".join(sizes_list))

    await message.answer("Введи хэштеги товара:")
    await state.set_state(AddSlot.waiting_description)

@router.message(Command("all_orders"))
async def all_orders(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет доступа.")

    orders = await get_all_orders_history()
    if not orders:
        return await message.answer("📭 История заказов пуста.")

    text = "📜 История заказов:\n\n"
    for o in orders:
        text += (
            f"📦 Заказ #{o[0]}\n"
            f"👤 @{o[1] or '—'}\n"
            f"📌 {o[2]} — {o[3] or '—'}\n"
            f"📊 Статус: {o[4]}\n"
            f"🕒 {o[5]}\n\n"
        )

    await message.answer(text)
    return None


@router.message(F.from_user.id.in_(ADMINS), Command("addsize"))
async def cmd_addsize(message: Message, state: FSMContext):
    try:
        slot_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        return await message.answer("⚠ Используй: /addsize <slot_id>")

    await state.update_data(slot_id=slot_id)
    await state.set_state(AdminFSM.waiting_for_new_size)
    await message.answer(f"Введи новый размер для слота #{slot_id}")
    return None


@router.message(AdminFSM.waiting_for_new_size, F.from_user.id.in_(ADMINS))
async def process_new_size(message: Message, state: FSMContext):
    new_size = message.text.strip()
    data = await state.get_data()
    slot_id = data["slot_id"]

    success = await update_slot_size(slot_id, new_size)
    if not success:
        await message.answer("❌ Слот не найден")
        return await state.clear()

    slot = await get_slot(slot_id)

    await message.answer(f"✅ Размер {new_size} добавлен в слот #{slot_id}")

    if slot.get("channel_id") and slot.get("message_id"):
        caption = (
            f"🔥 {slot['name']}\n"
            f"Размеры: {slot['size']}\n"
            f"Цена: {slot['price']}₽\n"
            f"{slot['description']}\n\n"
            f"👉 Жми кнопку ниже, чтобы заказать!"
        )

        try:
            await message.bot.edit_message_caption(
                chat_id=slot["channel_id"],
                message_id=slot["message_id"],
                caption=caption,
                reply_markup=kb.product_button(slot_id)
            )
            await message.answer("📢 Пост в канале обновлён ✅")
        except Exception as e:
            await message.answer(f"⚠ Не удалось обновить пост: {e}")

    await state.clear()
    return None


@router.message(AddSlot.waiting_description)
async def slot_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)

    data = await state.get_data()
    await add_slot(
        name=data["name"],
        png=data["png"],
        price=data["price"],
        size=data["size"],
        description=data["description"],
        user_id=None
    )

    await message.answer(
        f"✅ Товар {data['name']} добавлен!\n"
        f"Размеры: {data['size']}\n"
        f"Цена: {data['price']}₽\n"
        f"{data['description']}",
        parse_mode="HTML"
    )
    await state.clear()



@router.message(Command("delete_slot"))
async def cmd_delete_slot(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет доступа.")

    try:
        slot_id = int(message.text.split(maxsplit=1)[1])
    except (IndexError, ValueError):
        return await message.answer("⚠ Укажи ID слота: /delete_slot <id>")

    slot = await get_slot(slot_id)
    if not slot:
        return await message.answer(f"❌ Слот {slot_id} не найден.")

    channel_id = slot.get("channel_id")
    message_id = slot.get("message_id")

    if channel_id and message_id:
        try:
            await message.bot.delete_message(chat_id=channel_id, message_id=message_id)
        except Exception as e:
            await message.answer(f"⚠ Не удалось удалить сообщение в канале: {e}")

    await delete_slot(slot_id)

    await message.answer(f"🗑 Слот {slot_id} удалён из БД и из канала.")
    return None


@router.message(Command("slots"))
async def cmd_slots(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("⛔ Нет доступа.")

    slots = await get_slots()
    if not slots:
        return await message.answer("📭 Слотов пока нет.")

    text = "\n".join([f"{s['id']}: {s['name']} — {s['price']}₽" for s in slots])
    await message.answer("📦 Слоты:\n" + text)
    return None


@router.message(Command("reset_slots"))
async def cmd_reset_slots(message: Message):
    if message.from_user.id not in ADMINS:
        return await message.answer("❌ У вас недостаточно прав.")

    await reset_slots()
    await message.answer("♻️ Таблица слотов очищена и пересоздана")
    return None


@router.callback_query(F.data.startswith("edit_"))
async def choose_field(callback: CallbackQuery, state: FSMContext):
    _, field, slot_id = callback.data.split("_")
    slot_id = int(slot_id)

    await state.update_data(slot_id=slot_id, field=field)
    await state.set_state(EditSlotForm.value)

    field_names = {
        "name": "новое название",
        "size": "новый размер",
        "price": "новую цену",
        "png": "новую картинку (ссылку или file_id)"
    }
    await callback.message.answer(f"Введите {field_names[field]} для слота #{slot_id}:")
    await callback.answer()

@router.message(EditSlotForm.value)
async def save_edit(message: Message, state: FSMContext):
    data = await state.get_data()
    slot_id = data["slot_id"]
    field = data["field"]
    value = message.text

    await update_slot(slot_id, field, value)

    await message.answer(f"✅ Слот #{slot_id} обновлён: {field} → {value}")
    await state.clear()


@router.message(Command("postslot"))
async def post_slot(message: Message):
    if F.from_user.id.in_(ADMINS):
        try:
            slot_id = int(message.text.split()[1])
        except (IndexError, ValueError):
            return await message.answer("⚠ Используй так: /postslot <id>")

        slot = await get_slot(slot_id)
        if not slot:
            return await message.answer("❌ Слот не найден.")

        caption = (
            f"{slot['name']}\n"
            f"Размеры: {slot['size']}\n"
            f"Цена: {slot['price']}₽\n"
            f"{slot['description']}\n\n"
            f"👉 Жми кнопку ниже, чтобы заказать!"
        )

        msg = await message.bot.send_photo(
            chat_id=CHANNEL_ID,
            photo=slot["png"],
            caption=caption,
            reply_markup=kb.product_button(slot_id)
        )

        await update_slot(slot_id, "channel_id", CHANNEL_ID)
        await update_slot(slot_id, "message_id", msg.message_id)

        await message.answer(f"✅ Слот {slot_id} опубликован в канал и сохранён (msg_id={msg.message_id}).")

        return None
    else:
        await message.reply("⛔ Нет доступа.")
        return None


# ---------- Управление заказами ----------

@router.message(F.from_user.id.in_(ADMINS), F.text == "/orders")
async def list_orders(message: Message):
    orders = await get_all_orders()
    if not orders:
        return await message.answer("📭 Заказов пока нет.")

    text = "📋 Список заказов:\n\n"
    for order_id, username, slot_id, status, created_at in orders:
        text += (
            f"🆔 {order_id} | @{username}\n"
            f"Товар: {slot_id}\n"
            f"Статус: {status}\n"
            f"Дата: {created_at}\n\n"
        )

    await message.answer(text)
    return None






@router.message(F.from_user.id.in_(ADMINS), F.text.startswith("/slot"))
async def cmd_slot(message: Message):
    try:
        slot_id = int(message.text.split()[1])
    except (IndexError, ValueError):
        await message.answer("⚠ Используй: /slot <id>")
        return

    slot = await get_slot(slot_id)
    if not slot:
        await message.answer("❌ Слот не найден")
        return

    text = (
        f"📦 Слот #{slot['id']}\n\n"
        f"Название: {slot['name']}\n"
        f"Цена: {slot['price']}\n"
        f"Размер: {slot.get('size', '—')}\n"
        f"Описание: {slot.get('description', '—')}\n"
    )
    photo_url = slot.get('png')
    if photo_url:
        await message.answer_photo(photo=photo_url, caption=text)
    else:
        await message.answer(text)


