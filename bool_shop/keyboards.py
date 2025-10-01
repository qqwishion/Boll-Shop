from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

contact_button = KeyboardButton(text="📱 Отправить контакт", request_contact=True)

start_reply_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒Меню", callback_data="menu")],
        [KeyboardButton(text="📂Каналы", callback_data="channels"), KeyboardButton(text="☎️Поддержка", callback_data="support"),],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

inline_channels_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📃Каталог", url="https://t.me/BollShopCatalog")],
        [InlineKeyboardButton(text="🔰Отзывы", url="https://t.me/BollShopFeedback"),
         InlineKeyboardButton(text="🆕Новости", url="https://t.me/BollShopNews")],
        [InlineKeyboardButton(text="◀️Назад", callback_data="back")]
    ]
)


def product_button(slot_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="Купить 🛒",
                url=f"https://t.me/BollShop_bot?start={slot_id}"
            )]
        ]
    )

inline_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📃Каталог", url="https://t.me/BollShopCatalog")],
        [InlineKeyboardButton(text="⚙️О нас", callback_data="about"), InlineKeyboardButton(text="◀️Назад", callback_data="back")]
    ]
)


inline_back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="◀️Назад", callback_data="back")]])


def size_keyboard(slot_id: int, sizes: list[str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=size, callback_data=f"size:{slot_id}:{size}")]
            for size in sizes
        ]
    )


def checkout_button(slot_id: int):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Оформить", callback_data=f"checkout:{slot_id}")]
        ]
    )
    return kb




def delivery_keyboard(order_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚚 Доставка по МСК", callback_data=f"delivery:courier:{order_id}")],
            [InlineKeyboardButton(text="📦 Авито доставка", callback_data=f"delivery:avito:{order_id}")],
            [InlineKeyboardButton(text="🏬 Самовывоз по МСК", callback_data=f"delivery:pickup:{order_id}")],
        ]
    )

def payment_approval_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, пришло",
                    callback_data=f"approve_payment:{order_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Нет, не пришло",
                    callback_data=f"reject_payment:{order_id}"
                ),
            ]
        ]
    )


def order_manage_kb(order_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Завершить",
                callback_data=f"order_complete:{order_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"order_decline:{order_id}"
            )
        ]
    ])


def admin_confirm_kb(order_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтверждаю", callback_data=f"admin_confirm:{order_id}")
    kb.button(text="❌ Отклоняю", callback_data=f"admin_reject:{order_id}")
    kb.adjust(2)
    return kb.as_markup()