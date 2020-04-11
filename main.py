import flask
import requests
import html
from flask import abort
from html.parser import HTMLParser
import json
import os
app = flask.Flask(__name__)


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
    for i in range(3):
        try:
            result = func(*args, **kwargs)
            if checker(result):
                return result
        except Exception as e:
            print(e)
            continue
    print(*args)
    abort(400, {'result': 'could not connect to resh.edu.ru or request is invalid'})


def filter_ans_json(x):
    keys = ['score', 'success']
    res = {}
    for i in keys:
        if i in x:
            res[i] = x
    return res


class Solver:
    def __init__(self, login, password):
        self.login = login
        self.password = password
        self.create_session()

    def create_session(self):
        self.session = requests.Session()
        payload={'_username': self.login,'_password': self.password}
        logging = try_get(self.session.post, request_checker, 'https://resh.edu.ru/login_check', data=payload)

    def solve_test(self, control_request):
        page = try_get(self.session.get, request_checker, control_request, headers=headers)
        page = str(html.unescape(page.text))
        ids = []
        for i in page.split('data-test-id'):
            if len(i) <= 0 or i[0] != '=':
                continue
            ids.append(i.split('"')[1])
        if not len(ids):
            return {'result': 'Tasks not found'}
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
        result['answers'] = json.dumps(result['answers'])
        try:
            resp = try_get(self.session.post, request_checker, control_request + 'result/', data=result, headers=headers)
        except Exception as e:
            return {'result': 'The test was solved successful but sever did not accept it'}

        return {'result': filter_ans_json(resp.json())}      
        
    def solve_lesson(self, id):
        former_url = 'https://resh.edu.ru/subject/lesson/' + id + '/control/'
        ind = 1
        result = {'result': {}}
        while True:
            control = try_get(self.session.get, request_checker, former_url + str(ind) + '/', headers=headers)
            ans = self.solve_test(former_url + str(ind) + '/')
            if ans['result'] == 'Tasks not found':
                break
            result['result'][ind] = ans
            ind += 1
        if len(result['result']) == 0:
            return {'result': 'Controls not found'}
        return result


@app.route('/')
def index():
    return 'Вот тут наверное будет форма крутая да...'


@app.route('/solve_lesson/<login>/<password>/<id>')
def solve_ls(login, password, id):
    return Solver(login, password).solve_lesson(id)


@app.route('/solve_control/<login>/<password>/<lid>/<id>')
def solve_ct(login, password, lid, id):
    return Solver(login, password).solve_test('https://resh.edu.ru/subject/lesson/' + lid + '/control/' + id + '/')


@app.route('/solve_training/<login>/<password>/<lid>')
def solve_training(login, password, lid):
    return Solver(login, password).solve_test('https://resh.edu.ru/subject/lesson/' + lid + '/train/')


def main():
    port = int(os.environ.get("PORT", 5000))
    app.run(port=port, host='0.0.0.0')


if __name__ == '__main__':
    main()
