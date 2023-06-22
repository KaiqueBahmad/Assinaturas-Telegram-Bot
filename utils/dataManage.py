import json


def storeValue(value, attr, uid):
    print(value, attr, uid, sep='||')
    data_save = []
    uid = str(uid)
    with open('data.json', 'r') as file:
        data = json.load(file)
        if uid not in data:
            data.update({uid: {
                'chat-id': None,
                'nome': None,
                'email': None,
                'numero': None,
                'txid': None,
                'expires': None
            }
            })
        data[uid][attr] = value
        data_save.append(data)
    with open('data.json', 'w') as file:
        json.dump(data_save[0], file, indent=4)


def readValue(attr, uid):
    with open('data.json', 'r') as file:
        data = json.load(file)
        return data[uid][attr]
