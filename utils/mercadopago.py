import requests
from utils.dataManage import storeValue, readValue
from ..constants import TOKEN_mercadopago

def genPixLink(value, uid):
    data = requests.post('https://api.mercadopago.com/v1/payments',
                         headers={
                             "Authorization": TOKEN_mercadopago},
                         json={
                             "transaction_amount": value,
                             "payment_method_id": "pix",
                             "description": "Buy telegram group acess",
                             "payer": {
                                 "email": readValue('email', str(uid))
                             }})
    storeValue(data.json()['id'], 'txid', uid)
    return data.json()['point_of_interaction']['transaction_data']['qr_code']


def checkTransaction(id):
    if id == None:
        return 'Not Found'
    data = requests.get(f'https://api.mercadopago.com/v1/payments/{id}',
                        headers={"Authorization": TOKEN_mercadopago})
    return [data.json()['status'], int(data.json()['transaction_details']['total_paid_amount'])]
