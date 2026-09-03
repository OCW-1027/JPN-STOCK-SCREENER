import requests, json
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer":"https://m.stock.naver.com/","Accept":"application/json"}
r=requests.get("https://m.stock.naver.com/api/stock/005930/trend", headers=UA, timeout=15)
print("HTTP", r.status_code)
rows=r.json()
print("항목 수:", len(rows))
print("\n첫 항목 전체 필드:")
for k,v in rows[0].items(): print(f"  {k:34s} {str(v)[:24]}")
