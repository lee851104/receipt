# 假品名屬性逐筆複核

2026-10-15；107 筆全部為公開假品名。以下由助理逐欄複核，使用者已檢查並確認 107 筆。確認來源為使用者對 commit 0e98b71 檢查表的核准，逐筆綁定屬性內容雜湊。這是合成集參考答案，不是私人真人發票的盲標成績。

舊模型與此複核有 53 筆／91 欄差異；新版實際重跑後仍有 46 筆／70 欄差異。有效快取採下表修正，原模型與新模型輸出都獨立保留。

## 原因對照

同一個 4B GGUF、temperature=0、seed=42、quantity=1，重跑全部 107 筆。指定 15 個錯誤：原批次 3 筆／有前綴／空店家為 15；移除前綴 10；只補店家 13；兩者合用 10；單筆保留前綴 7；單筆去前綴 7；單筆去前綴＋新版 prompt 5。

因此前綴、批次與 prompt 都會影響輸出，空白店家不是唯一原因。新版改成單筆、只移除開頭的「示範」、補充多標籤定義；保留原品名作快取鍵，merchant 仍空白。未加入按這 107 個名字查答案的規則。小模型仍會漏標與誤判，逐筆修正必須和模型品質分開計算。

新版相較「單筆去前綴／舊 prompt」，指定錯誤 7→5、與助理複核不同的品項 47→46，但不同欄位 60→63；不宣稱全面改善。對照實驗見 [attribute-input-experiment.json](../../datasets/synthetic/attribute-input-experiment.json)。

診斷實驗新版為 46 筆／63 欄差異；正式介面獨立重跑為 46 筆／70 欄、指定錯誤 4 個。相同 prompt 與 seed 仍有 7 筆／15 欄輸出不同，故這裡採正式重跑的實存輸出，不宣稱 GPU 推論逐次完全一致；離線配對則由固定快取重現。

## 可核對的資料

- [原版模型輸出](../../datasets/synthetic/attribute-cache.model-v1.jsonl)
- [新版實際模型輸出](../../datasets/synthetic/attribute-cache.model-v2.jsonl)
- [逐筆 23 欄複核](../../datasets/synthetic/attribute-review.jsonl)
- [有效快取與每欄差異](../../datasets/synthetic/attribute-cache.jsonl)

model_version：`qwen3-4b:2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e:5e86775fba0e8c8a2fe31adc0c3fc420cd37b5daa3a1538b214c3866c97511a9:guards-v1:input-v2:batch1`。每筆有 original_model_attributes、model_attributes、corrections；目前 review_status 為 human_confirmed, human_corrected；人工確認 107 筆，原始準備者 reviewer=assistant、確認者 confirmation.confirmed_by=user 分開保留。重建會保留確認；若屬性改變，舊確認自動失效。

## 107 筆檢查表

「成立屬性」列出 true 與有值的三個列舉欄位；未列布林為 false，未列 sugar/fun/species 為 null。「修正欄位」是相對新版模型的差異。

| # | 假品名 | 成立屬性 | 修正欄位 |
|---:|---|---|---|
| 1 | 示範95無鉛汽油 | 無 | car_care: null → false |
| 2 | 示範乳清蛋白粉 | sport_supply, food | food: false → true |
| 3 | 示範停車費 | 無 | 無 |
| 4 | 示範健身入場 | sport | 無 |
| 5 | 示範傳輸線 | tech | tech: false → true |
| 6 | 示範冬瓜青茶 | food, drink | 無 |
| 7 | 示範冰美式 | food, drink | 無 |
| 8 | 示範半糖拿鐵 | sugar=0.5, food, drink | quick: true → false, sport: true → false |
| 9 | 示範半糖焦糖拿鐵 | sugar=0.5, food, drink | quick: true → false, sport: true → false |
| 10 | 示範即期咖哩飯 | clearance, food, meal | clearance: false → true, quick: true → false |
| 11 | 示範即期御飯糰 | clearance, quick, food, meal | clearance: false → true, meal: false → true |
| 12 | 示範即期排骨便當 | clearance, food, meal | clearance: false → true, quick: true → false |
| 13 | 示範即期雞腿便當 | clearance, food, meal | clearance: false → true, quick: true → false |
| 14 | 示範可樂 | food, drink | 無 |
| 15 | 示範可頌 | food | quick: true → false |
| 16 | 示範咖哩飯 | food, meal | 無 |
| 17 | 示範地瓜 | cooking, food, fresh | cooking: false → true |
| 18 | 示範客運票 | 無 | daily: true → false |
| 19 | 示範密室逃脫 | fun=遊樂 | quick: true → false, bulk: true → false, food: true → false, drink: true → false, sport: true → false |
| 20 | 示範微波炒飯 | quick, food, meal | 無 |
| 21 | 示範微波義大利麵 | quick, food, meal | meal: false → true |
| 22 | 示範手帳 | stationery, daily | daily: false → true |
| 23 | 示範手沖咖啡 | food, drink | 無 |
| 24 | 示範排骨便當 | food, meal | 無 |
| 25 | 示範擴香瓶 | home, daily | daily: false → true |
| 26 | 示範旅店雙人房 | 無 | 無 |
| 27 | 示範桌遊時段 | fun=遊樂 | quick: true → false, food: true → false, drink: true → false, sport: true → false |
| 28 | 示範機械鍵盤 | tech | 無 |
| 29 | 示範歡唱時段 | fun=唱歌 | quick: true → false, food: true → false, sport: true → false |
| 30 | 示範洋蔥 | cooking, food, fresh | cooking: false → true |
| 31 | 示範洗碗精3入 | bulk, daily | 無 |
| 32 | 示範洗衣精家庭號 | bulk, daily | home: true → false |
| 33 | 示範洗面乳 | daily | 無 |
| 34 | 示範海鮮套餐 | food, meal | 無 |
| 35 | 示範滷肉飯 | food, meal | 無 |
| 36 | 示範火腿三明治 | quick, food, meal | 無 |
| 37 | 示範無糖四季春 | sugar=0.0, food, drink | 無 |
| 38 | 示範無糖烏龍 | sugar=0.0, food, drink | 無 |
| 39 | 示範無糖烏龍茶 | sugar=0.0, food, drink | 無 |
| 40 | 示範無糖綠茶 | sugar=0.0, food, drink | 無 |
| 41 | 示範無糖豆漿 | sugar=0.0, food, drink | 無 |
| 42 | 示範無糖青茶 | sugar=0.0, food, drink | 無 |
| 43 | 示範焦糖布丁 | food | drink: true → false |
| 44 | 示範熱美式 | food, drink | 無 |
| 45 | 示範燒肉套餐 | food, meal | 無 |
| 46 | 示範燕麥拿鐵 | food, drink | 無 |
| 47 | 示範牙刷 | daily | 無 |
| 48 | 示範牙膏 | daily | 無 |
| 49 | 示範牙膏量販包 | bulk, daily | 無 |
| 50 | 示範牛肉堡 | food, meal | quick: true → false |
| 51 | 示範牛肉燴飯 | food, meal | 無 |
| 52 | 示範牛肉麵 | food, meal | 無 |
| 53 | 示範犬用飼料 | pet_food, species=dog | 無 |
| 54 | 示範狗零食 | pet_food, species=dog | 無 |
| 55 | 示範珍珠奶茶 | food, drink | 無 |
| 56 | 示範班尼迪克蛋 | food, meal | meal: false → true, fresh: true → false |
| 57 | 示範生啤酒 | alcohol, food, drink | 無 |
| 58 | 示範番茄義大利麵 | food, meal | cooking: true → false |
| 59 | 示範白米 | kitchen, food | 無 |
| 60 | 示範百香果茶 | food, drink | 無 |
| 61 | 示範石鍋拌飯 | food, meal | quick: true → false |
| 62 | 示範礦泉水 | food, drink | 無 |
| 63 | 示範筆記本 | stationery, daily | 無 |
| 64 | 示範精釀啤酒 | alcohol, food, drink | 無 |
| 65 | 示範紙膠帶貼紙 | stationery, daily | daily: false → true |
| 66 | 示範耳機 | tech | 無 |
| 67 | 示範肉桂捲 | food | quick: true → false |
| 68 | 示範肉鬆飯糰 | quick, food, meal | meal: false → true |
| 69 | 示範舒肥雞沙拉 | food, meal | cooking: true → false, meal: false → true, fresh: true → false |
| 70 | 示範花椰菜 | cooking, food, fresh | cooking: false → true |
| 71 | 示範花生豆花 | food | drink: true → false |
| 72 | 示範蔬食餐盒 | food, meal | 無 |
| 73 | 示範行動電源 | tech | 無 |
| 74 | 示範衛生紙 | daily | 無 |
| 75 | 示範衛生紙箱 | bulk, daily | bulk: false → true |
| 76 | 示範調酒 | alcohol, food, drink | 無 |
| 77 | 示範豚骨拉麵 | food, meal | quick: true → false |
| 78 | 示範豬肉片 | cooking, food, fresh | 無 |
| 79 | 示範貓砂 | pet_supply, species=cat, daily | daily: false → true |
| 80 | 示範貓罐頭 | pet_food, species=cat | 無 |
| 81 | 示範貓飼料 | pet_food, species=cat | 無 |
| 82 | 示範越南河粉 | food, meal | 無 |
| 83 | 示範遊樂園門票 | fun=遊樂 | sport: true → false |
| 84 | 示範醬油 | kitchen, food | cooking: true → false |
| 85 | 示範重訓課 | sport | 無 |
| 86 | 示範鋼筆 | stationery, daily | daily: false → true |
| 87 | 示範陶瓷杯 | home, daily | daily: false → true |
| 88 | 示範雞排堡 | food, meal | quick: true → false |
| 89 | 示範雞肉餐盒 | food, meal | 無 |
| 90 | 示範雞胸肉 | cooking, food, fresh | 無 |
| 91 | 示範雞腿便當 | food, meal | 無 |
| 92 | 示範雞腿簡餐 | food, meal | 無 |
| 93 | 示範雞腿肉 | cooking, food, fresh | 無 |
| 94 | 示範雞蛋 | cooking, food, fresh | 無 |
| 95 | 示範電影票 | fun=電影 | stationery: true → false, food: true → false, drink: true → false, daily: true → false, tech: true → false, sport: true → false |
| 96 | 示範青醬燉飯 | food, meal | cooking: true → false |
| 97 | 示範韭菜豬肉水餃 | food, meal | cooking: true → false |
| 98 | 示範香氛蠟燭 | home, daily | daily: false → true |
| 99 | 示範體適能體驗票 | sport | 無 |
| 100 | 示範高鐵車票 | 無 | 無 |
| 101 | 示範高麗菜 | cooking, food, fresh | cooking: false → true |
| 102 | 示範鬆餅套餐 | food, meal | quick: true → false, meal: false → true |
| 103 | 示範鬆餅早午餐 | food, meal | 無 |
| 104 | 示範鮪魚飯糰 | quick, food, meal | meal: false → true |
| 105 | 示範鮭魚定食 | food, meal | 無 |
| 106 | 示範鮮奶 | food, drink | 無 |
| 107 | 示範黑糖珍珠鮮奶 | food, drink | 無 |

重建有效快取及此表：`python -m scripts.review_synthetic_cache`。重建只讀公開的模型輸出與逐筆複核，不重新推論、不讀取真人品名。
