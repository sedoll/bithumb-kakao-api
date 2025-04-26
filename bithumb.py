import jwt
import uuid
import time
import requests
import json

### 🔑 API KEY 설정
accessKey = "" # bithumb access key
secretKey = "" # bithumb secret key, 외부에 노출 안되게 주의
apiUrl = "https://api.bithumb.com"
kakaoApiKey = "" # kakao rest api key

# path = "/apps/" # linux dir
path = "./" # pc test dir

# 토큰 불러오기
def load_tokens():
    with open(path + "kakao_code.json", "r") as fp:
        return json.load(fp)

# 토큰 저장
def save_tokens(tokens):
    with open(path + "kakao_code.json", "w") as fp:
        json.dump(tokens, fp)

# 토큰 재발급
# refresh 토큰으로 갱신
def refresh_token():
    tokens = load_tokens()
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": kakaoApiKey,
        "refresh_token": tokens['refresh_token']
    }
    response = requests.post(url, data=data)
    result = response.json()
    if 'access_token' in result: # access_token 값이 존재하는 경우 갱신
        tokens['access_token'] = result['access_token']
    if 'refresh_token' in result: # refresh_token 값이 존재하는 경우 갱신
        tokens['refresh_token'] = result['refresh_token']
    save_tokens(tokens)
    return tokens

# 내 빗썸 코인 정보 가져오기
def get_bithumb_coin():
    payload = {
        'access_key': accessKey,
        'nonce': str(uuid.uuid4()),
        'timestamp': round(time.time() * 1000)
    }
    jwt_token = jwt.encode(payload, secretKey)
    authorization_token = 'Bearer {}'.format(jwt_token)
    headers = {'Authorization': authorization_token}
    try:
        response = requests.get(apiUrl + '/v1/accounts', headers=headers)
        print("빗썸 응답: ", response.status_code)
        return response.json()
    except Exception as err:
        print(err)

# 코인 실시간 가격정보 가져오기
def get_price(currency):
    url = f"https://api.bithumb.com/v1/ticker?markets=KRW-{currency}"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return float(data[0]['trade_price'])
    else:
        print(f"Error fetching price for {currency}")
        return 0

# 카카오로 보낼 메세지 생성
def build_message(data):
    total_krw = 0
    total_investment = 0
    money = 0
    point = 0
    coins = []
    for asset in data:
        currency = asset['currency']
        locked = float(asset['locked'])
        balance = float(asset['balance']) + locked
        avg_buy_price = float(asset['avg_buy_price'])
        if currency == 'KRW':
            money += balance
            continue
        elif currency == 'P':
            point += balance
            continue
        else:
            total_investment += balance * avg_buy_price
        try:
            price = get_price(currency)
            if price == 0:
                continue
            value = balance * price
            profit_str = "정보 없음"
            if avg_buy_price > 0:
                profit = ((price - avg_buy_price) / avg_buy_price) * 100
                arrow = '📈' if profit >= 0 else '📉'
                profit_str = f"{arrow} {profit:+.1f}%"
            coins.append(f"\n{currency}: {balance:.4f}개 \n{int(value):,} KRW \n(평단가 {avg_buy_price:,} KRW) \n(현재가 {price:,} KRW | {profit_str}) \n(매수/매도 수량 {locked:.4f}개)")
            total_krw += value
        except Exception as e:
            print(f"Error processing {currency}: {e}")
            continue
    total_profit = total_krw - total_investment
    total_profit_percent = (total_profit / total_investment) * 100 if total_investment > 0 else 0
    profit_arrow = '📈' if total_profit >= 0 else '📉'
    profit_str = f"{profit_arrow} {total_profit_percent:+.1f}% ({int(total_profit):,} KRW)"
    coins.append(f"\n💰 총 평가금액: {int(total_krw):,} KRW")
    coins.append(f"\n💰 현금 : {int(money):,} KRW")
    coins.append(f"\n💰 포인트 : {int(point):,} KRW")
    coins.append(f"\n💰 총 보유 자산 : {(int(total_krw)+int(money)+int(point)):,} KRW")
    coins.append(f"\n💰 총 손익: {profit_str}")
    return "📊 보유 코인 현황\n" + "\n".join(coins)

# 카카오 메세지 전송
def send_kakao_message(msg):
    tokens = load_tokens()
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {
        "Authorization": "Bearer " + tokens["access_token"],
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "template_object": json.dumps({
            "object_type": "text",
            "text": msg,
            "link": {
                "web_url": "https://www.bithumb.com/react/trade/order/BTC-KRW",
                "mobile_web_url": "https://www.bithumb.com/react/trade/order/BTC-KRW"
            }
        })
    }
    response = requests.post(url, headers=headers, data=data) # 메세지 전송
    if response.status_code != 200: # 전송 실패할 경우
        print("토큰 갱신 후 재시도합니다...")
        refresh_token()
        tokens = load_tokens()
        headers["Authorization"] = "Bearer " + tokens["access_token"]
        response = requests.post(url, headers=headers, data=data)
    print("카카오톡 응답:", response.status_code)

if __name__ == "__main__":
    res = get_bithumb_coin()
    msg = build_message(res)
    send_kakao_message(msg)
