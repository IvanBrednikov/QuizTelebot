#@title Полный код бота для самоконтроля
import aiosqlite
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import F
from QuizData import quiz_data
from QuizDB import *

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)


API_TOKEN = '7799597845:AAETVYtDXiHdNWggqzKLwozC9HwYR71Yoig'

# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()

#создание калбек-клавиатуры с вариантами ответов
def generate_options_keyboard(answer_options, right_answer):
    # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()
        # В цикле создаем Inline кнопки, а точнее Callback-кнопки
    
    for option in range(len(answer_options)):
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=answer_options[option],
            callback_data=str(option))
        )

    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()


@dp.callback_query()
async def right_answer(callback: types.CallbackQuery):
    
    # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    
    #выводим ответ пользователя
    selected_button_text = await get_qtext(callback.from_user.id, int(callback.data))
    await callback.message.answer(selected_button_text)
    
    #определяем правильность ответа
    current_question_index = await get_quiz_index(callback.from_user.id)
    correct_option = quiz_data[current_question_index]['correct_option']
    print(correct_option, int(callback.data))
    #записываем текущую статистику
    cur_result = await get_result(callback.from_user.id)
    if correct_option == int(callback.data):
        await callback.message.answer("Верно!")
        #запись статистики
        cur_result += 1
    else:
        await callback.message.answer(f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    # Обновление номера текущего вопроса в базе данных
    current_question_index += 1
    await update_quiz_index(callback.from_user.id, current_question_index, cur_result)

    # Проверяем достигнут ли конец квиза
    if current_question_index < len(quiz_data):
        # Следующий вопрос
        await show_next_question(callback, current_question_index)
    else:
        # Уведомление об окончании квиза
        await callback.message.answer(f"Это был последний вопрос. Квиз завершен! Верных ответов: {cur_result}/{len(quiz_data)}")

# вывод следущего вопроса
async def show_next_question(callback, current_q_index):
    opts, correct_index = await get_question(callback.from_user.id)
    kb = generate_options_keyboard(opts, correct_index)
    if type(callback) == types.Message:
        await callback.answer(f"{quiz_data[current_q_index]['question']}", reply_markup=kb)
    else:
        await callback.message.answer(f"{quiz_data[current_q_index]['question']}", reply_markup=kb)

# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

# Хэндлер на команду /quiz
@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):

    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)
    # вывод первого вопроса
    await show_next_question(message, 0)

# Хэндлер на команду /result
@dp.message(Command("result"))
async def cmd_result(message: types.Message):
    results = await get_result(message.from_user.id)
    await message.answer(f'Последний результат: {results}/{len(quiz_data)} верных ответов')


# Запуск процесса поллинга новых апдейтов
async def main():

    # Запускаем создание таблицы базы данных
    await create_table()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())