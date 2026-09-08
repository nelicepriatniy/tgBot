from aiogram.fsm.state import State, StatesGroup


class FunnelStates(StatesGroup):
    choosing_branch = State()
    waiting_subscription = State()
    ready_for_test = State()
    bolt_intro = State()
    bolt_waiting_start = State()
    bolt_running = State()
    done = State()


class AdminStates(StatesGroup):
    broadcast_text = State()
    broadcast_branch = State()
