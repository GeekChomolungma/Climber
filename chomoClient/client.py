import requests
url = 'http://127.0.0.1:8080/api/v1/account/accountinfo'

def PlaceOrder():
    data = {
        'aimsite': 'HuoBi',
        'body':"test"
    }
    response = requests.post(f'{url}', json=data)
    print(response.text)