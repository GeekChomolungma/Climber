import requests
import json

urlAccountBalance = 'http://127.0.0.1:8080/api/v1/account/accountbalance'
urlOrder = 'http://127.0.0.1:8080/api/v1/order/placeorder'

def PlaceOrder(amout):
    dict = {
        "model": "buy-market",
        "amount": amout,
        "price": "100"
    }
    body = json.dumps(dict)
    data = {
        'aimsite': 'HuoBi',
        'body': body
    }
    response = requests.post(f'{urlOrder}', json=data)
    print(response.text)

def GetAccountBalance():
    dict = {
        "currency": "usdt",
    }
    body = json.dumps(dict)
    data = {
        'aimsite': 'HuoBi',
        'body':body
    }
    response = requests.post(f'{urlAccountBalance}', json=data)
    balance = json.loads(response.text)
    print(balance)
    return balance["data"]
