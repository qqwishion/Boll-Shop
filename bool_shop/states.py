from aiogram.fsm.state import StatesGroup, State

class EditSlotForm(StatesGroup):
    field = State()
    value = State()

class SlotForm(StatesGroup):
    name = State()
    png = State()
    price = State()



class OrderFSM(StatesGroup):
    waiting_for_size = State()
    waiting_for_delivery = State()
    waiting_for_proof = State()
    waiting_for_address = State()


class AdminFSM(StatesGroup):
    waiting_for_new_size = State()


class AddSlot(StatesGroup):
    waiting_name = State()
    waiting_price = State()
    waiting_png = State()
    waiting_sizes = State()
    waiting_description = State()

