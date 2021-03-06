import flask
import requests
import html
import random
from flask import abort, render_template, request, session
from html.parser import HTMLParser
import json
import os
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Length, ValidationError
from wtforms.fields.html5 import EmailField
from flask_wtf import FlaskForm
import datetime
import threading
app = flask.Flask(__name__)
app.config['SECRET_KEY'] = 'шуе ппш шпш 12342'
results = {}    


def validate_test_id(form, field):
    if form.solveType.data == 'control' and len(form.TestId.data) == 0:
        raise ValidationError('Необходимо заполнить это поле')


class SolveRequest(FlaskForm):
    login = StringField('Логин', validators=[DataRequired(), Length(0, 250)])
    password = StringField('Пароль', validators=[DataRequired(), Length(0, 250)])
    solveType = SelectField('Тип решения', choices=[('lesson', 'Решить урок'), ('control', 'Решить контрольную'), ('training', 'Решить тренировку')], validators=[DataRequired()], render_kw={'onchange': "ContentShow()"})
    Score = SelectField('Оценка', choices=[('5', '5'), ('4', '4'), ('3', '3'), ('2', '2')], validators=[DataRequired()])
    lessonId = StringField('Айди урока', validators=[DataRequired(), Length(0, 250)])
    TestId = StringField('Номер контрольной', validators=[validate_test_id])
    submit = SubmitField('Решить')


"""
хеш - указатель на обьект, подразумевает перечисление множества (порядки, выделения)
отсутствие ответа подразумевает его проверку на клиенте и true\false в ответе соответствено (кроссворды и пр..)
ключи RESPONSE - поля ввода (текст, числа)

"""
headers= {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
}
data_headers = {
        'Host': 'resh.edu.ru',
        'X-Requested-With': 'XMLHttpRequest'
        }


def request_checker(response):
    if response and response.status_code == 200:
        return True
    return False


def try_get(func, checker, *args, **kwargs):
    for i in range(5):
        try:
            result = func(*args, **kwargs)
            print(result)
            if checker(result):
                return result
        except Exception as e:
            print(e)
            continue
    print(*args)
    abort(400, {'result': 'Ошибка подключения к серверу, возможно, введены неверные данные'})


def filter_ans_json(x):
    keys = ['score', 'success']
    res = {}
    for i in keys:
        if i in x:
            res[i] = x[i]
    return res


class Solver:
    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.create_session()

    def logout(self):
        logout = try_get(self.session.get, request_checker, 'https://resh.edu.ru/logout')

    def create_session(self):
        self.session = requests.Session()
        payload={'_username': self.login,'_password': self.password}
        logging = try_get(self.session.post, request_checker, 'https://resh.edu.ru/login_check', data=payload)

    def solve_test(self, control_request, need_score):
        page = try_get(self.session.get, request_checker, control_request, headers=headers)
        page = str(html.unescape(page.text))
        ids = []
        for i in page.split('data-test-id'):
            if len(i) <= 0 or i[0] != '=':
                continue
            ids.append(i.split('"')[1])
        if not len(ids):
            return {'result': 'Задания не найдены'}
        result = {"answers": {}}
        for i in ids:
            ans = try_get(requests.get, request_checker, 'https://resh.edu.ru/tests/' + i + '/get-answers', headers=data_headers)
            ans = ans.json()
            if not ans:
                ans = {"RESPONSE1": True}
            else:
                new_ans = {}
                for g in ans.items():
                    if type(g[1]) == list:
                        if not len(g[1]):
                            new_ans[g[0]].append(True)
                        new_ans[g[0]] = []
                        for k in g[1]:
                            new_ans[g[0]].append(k['value'])
                    elif type(g[1]) == dict:
                        new_ans[g[0]] = g[1]['value']
                    else:
                        new_ans[g[0]] = g[1]
                ans =  new_ans
            result["answers"][i] = ans
        cut_coff = 0
        if need_score == '4':
            cut_coff = min(1, len(ids))
        elif need_score == '3':
            cut_coff = min(2, len(ids))
        elif need_score == '2':
            cut_coff = len(ids)
        for i in range(cut_coff):
            result['answers'][ids[i]] = ''
        result['answers'] = json.dumps(result['answers'])
        try:
            resp = try_get(self.session.post, request_checker, control_request + 'result/', data=result, headers=headers)
        except Exception as e:
            return {'result': 'Сервер не принял решение, тест уже решен либо указаны неверные данные'}

        return {'result': filter_ans_json(resp.json())}      
        
    def solve_lesson(self, id, score):
        former_url = 'https://resh.edu.ru/subject/lesson/' + id + '/control/'
        ind = 1
        result = {'result': {}}
        while True:
            control = try_get(self.session.get, request_checker, former_url + str(ind) + '/', headers=headers)
            ans = self.solve_test(former_url + str(ind) + '/', score)
            if ans['result'] == 'Задания не найдены':
                break
            result['result']['control' + str(ind)] = ans
            ind += 1
        if len(result['result']) == 0:
            result['result']['control'] = 'Контрольные не найдены или указаны неверные логин\пароль'
        result['result']['training'] = self.solve_test('https://resh.edu.ru/subject/lesson/' + id + '/train/', score)
        return result


def solve(form, id):
    func = {'lesson': solve_lesson, 'control': solve_control, 'training': solve_training}
    try:
        res = func[form.solveType.data](form.login.data, form.password.data, form.lessonId.data, form.TestId.data, form.Score.data)
    except Exception as E:
        try:
            print(E)
            if 'result' in E:
                res = E
            else:
                res = {'result': 'ошибка! Неверный формат'}
        except:
            res = {'result': 'ошибка! Неверный формат'}
    with open('logs.txt', 'a+') as st:
        st.write(str(form.lessonId.data) + ' ' + str(form.TestId.data) + ' ' + str(res) + '\n')
    results[id] = res


@app.route('/result', methods=['GET', 'POST'])
def get_result(): 
    if 'id' not in session:
            return {'result': ''}
    if request.method == 'GET':
        if session['id'] not in results:
            return {'result': ''}
        res = results[session['id']]
        if results[session['id']] != {'result': 'Процесс выполняется...'}:
            del results[session['id']]
        return res
    else:
        if session['id'] in results:
            return {'result': ''}
        form = SolveRequest()
        print(form.Score.data)
        threading.Thread(target = solve, args = (form, session['id'])).start()
        results[session['id']] = {'result': 'Процесс выполняется...'}
        return {'result': 'Процесс выполняется...'}

    
@app.route('/')
@app.route('/index')
def index():
    if 'id' not in session:
        session['id'] = random.randint(-100000000, 100000000)
    form = SolveRequest()
    if session['id'] in results:
        return render_template("index.html", form=form, result=get_result)
    return render_template("index.html", form=form, result={'result': ''})
        

def solve_lesson(login, password, lessonId, id, score):
    solver = Solver(login, password)
    result = solver.solve_lesson(lessonId, score)
    solver.logout()
    return result


def solve_control(login, password, lessonId, id, score):
    solver = Solver(login, password)
    result = solver.solve_test('https://resh.edu.ru/subject/lesson/' + lessonId + '/control/' + id + '/', score)
    solver.logout()
    return result


def solve_training(login, password, lessonId, id, score):
    solver = Solver(login, password)
    result = solver.solve_test('https://resh.edu.ru/subject/lesson/' + lessonId + '/train/', score)
    solver.logout()
    return result


def main():
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, host='0.0.0.0')


if __name__ == '__main__':
    main()
