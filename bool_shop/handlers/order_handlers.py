from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from bool_shop.db import add_order_proof, get_user_orders, get_slot, update_order_status
from bool_shop.bot_token import ADMINS
import bool_shop.keyboards as kb

router = Router()


class OrderFSM(StatesGroup):
    waiting_for_size = State()
    waiting_for_proof = State()
    waiting_for_delivery = State()
    waiting_for_address = State()

# ================= START CHECKOUT =================
@router.callback_query(F.data.startswith("checkout:"))
async def start_checkout(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split(":")[1])
    slot = await get_slot(slot_id)

    if not slot:
        return await callback.message.answer("❌ Товар не найден.")

    await state.update_data(
        slot_id=slot_id,
        slot_name=slot["name"],
        slot_price=slot["price"]
    )

    sizes = slot["size"].split(",") if slot["size"] else ["Стандарт"]
    await callback.message.answer("Выберите размер:", reply_markup=kb.size_keyboard(slot_id, sizes))
    await state.set_state(OrderFSM.waiting_for_size)
    return None


# ================= RECEIVE PAYMENT =================
@router.message(F.photo, OrderFSM.waiting_for_proof)
async def receive_payment(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data["order_id"]
    file_id = message.photo[-1].file_id
    await add_order_proof(order_id, file_id)
    slot_id = data["slot_id"]
    size = data["size"]
    from bool_shop.db import get_slot
    slot = await get_slot(slot_id)

    product_name = slot["name"]
    product_price = slot["price"]
    for admin_id in ADMINS:
        try:
            await message.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=(
                    f"Новый платёж!\n\n"
                    f"Пользователь: @{message.from_user.username or '—'}\n"
                    f"Telegram ID: <code>{message.from_user.id}</code>\n\n"
                    f"Заказ #{order_id}\n"
                    f"Товар: {product_name}\n"
                    f"Размер: {size}\n"
                    f"Цена: {product_price}₽"
                ),
                reply_markup=kb.payment_approval_kb(order_id)
            )
        except Exception as e:
            print(f"Не удалось отправить админу {admin_id}: {e}")
        try:
            await message.delete()
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")

    await message.answer("✅ Чек отправлен администратору на проверку")
    await state.clear()



# ================= ПОСЛЕ АДМИНСКОГО ПОДТВЕРЖДЕНИЯ =================
async def continue_after_payment(user_id: int, order_id: int, bot):
    """Вызывается админским хендлером после подтверждения"""
    await update_order_status(order_id, "paid")
    await bot.send_message(
        user_id,
        "✅ Оплата подтверждена!\n\n🚚 Теперь выберите метод получения:",
        reply_markup=kb.delivery_keyboard
    )


# ================= MY ORDERS =================
@router.message(F.text == "/myorders")
async def my_orders(message: Message):
    orders = await get_user_orders(message.from_user.id)
    if not orders:
        return await message.answer("📭 У вас пока нет заказов.")

    STATUS_LABELS = {
        "pending": "⏳ В ожидании",
        "paid": "✅ Оплачен",
        "processing": "⚙️ В обработке",
        "shipped": "🚚 Доставляется",
        "completed": "👌 Выполнен",
        "rejected": "❌ Отменён"

    }

    text = "📋 Ваши заказы:\n\n"
    for order in orders:
        order_id, slot_id, size, address, status = order
        text += (
            f"🆔 Заказ #{order_id}\n"     
            f"📌 Размер: {size or '-'}\n"
            f"📍 Адрес: {address or '-'}\n"
            f"📦 Статус: {STATUS_LABELS.get(status, status)}\n\n"
        )

    await message.answer(text)
    return None
