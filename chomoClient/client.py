import requests
import json

urlAccountBalance = 'http://139.196.155.97:8080/api/v1/account/accountbalance'
urlPlaceOrder = 'http://139.196.155.97:8080/api/v1/order/placeorder'
urlCancelOrder = 'http://139.196.155.97:8080/api/v1/order/cancelorder'
urlGetOrder = 'http://139.196.155.97:8080/api/v1/order/getorder'

def PlaceOrder(symbol, model, amout, price, source):
    dict = {
        "symbol":symbol,
        "model": model,
        "amount": amout,
        "price": price,
        "source":source
    }

    body = json.dumps(dict)
    data = {
        'aimsite': 'HuoBi',
        "accountid":"3667382",
        'body': body
    }
    response = requests.post(f'{urlPlaceOrder}', json=data)
    print(response.text)

def CancelOrder(orderID):
    dict = {
        "orderid":orderID
    }

    body = json.dumps(dict)
    data = {
        'aimsite': 'HuoBi',
        "accountid":"3667382",
        'body': body
    }
    response = requests.post(f'{urlCancelOrder}', json=data)
    print(response.text)

def GetOrder(orderID):
    dict = {
        "orderid":orderID
    }

    body = json.dumps(dict)
    data = {
        'aimsite': 'HuoBi',
        "accountid":"3667382",
        'body': body
    }
    response = requests.post(f'{urlGetOrder}', json=data)
    print(response.text)

def GetAccountBalance(currency):
    dict = {
        "currency": currency,
    }
    body = json.dumps(dict)
    data = {
        'aimsite': 'HuoBi',
        "accountid":"3667382",
        'body':body
    }
    response = requests.post(f'{urlAccountBalance}', json=data)
    balance = json.loads(response.text)
    print(balance)
    return balance["data"]
