# Strategy Configuration Reference

## strategy_config.json 概覽

`strategy_config.json` 為 CBAS 的核心設定檔，負責定義：

- 濾網條件
- R / P 權重
- 各指標的加分與懲罰規則

此檔案會在**第一次執行時自動生成**，之後可手動微調。

---

## 範例結構

```json
{
  "risk": {
    "price": {
      "safe": 102,
      "comfort": 105,
      "danger": 110
    },
    "premium": {
      "discount": -5,
      "safe": 3,
      "danger": 10
    }
  },
  "potential": {
    "time_window": {
      "min_days": 365,
      "score": 3
    },
    "balance": {
      "min_amount": 5000,
      "score": 2
    },
    "conversion_zone": {
      "min": 0.9,
      "max": 1.1,
      "score": 3
    },
    "technical": {
      "above_87ma": 2
    },
    "volume": {
      "surge": 2,
      "dead": -3
    }
  }
}
```

---

## Risk（R）參數說明

### price
- **safe / comfort / danger**
- CB 市價分級門檻
- 超過 danger 將給予高風險懲罰

### premium
- 折價具保護性
- 高溢價代表風險快速上升

---

## Potential（P）參數說明

### time_window
- 上市滿一定天數才加分

### balance
- 未轉餘額門檻
- 決定是否還有行情空間

### conversion_zone
- 轉換價值甜蜜點區間

### technical
- 是否站上關鍵均線

### volume
- 放量加分
- 殭屍量扣分

---

## 調參建議

- **保守型**：提高 R 懲罰、降低 P 加分
- **積極型**：放寬 R、提高技術與成交量權重
- 建議一次只調整一個維度，避免誤判

---

## Best Practice

- 不要頻繁調整參數
- 用歷史案例驗證後再實盤
- 保留原始設定作為對照


---

## 📚 Documentation Index

完整系統說明請參考 `docs/` 目錄：

- **docs/architecture.md**：系統整體架構、資料流程、R/P 評分模型工程化說明
- **docs/strategy.md**：鄭大 CB 策略白話版（交易邏輯、風險思維、實戰哲學）
- **docs/config.md**：`strategy_config.json` 參數全解與調參原則

建議閱讀順序：
1. `docs/strategy.md`
2. `docs/architecture.md`
3. `docs/config.md`

---

## 🗺️ Roadmap

### v1.x（目前）
- 單一 R/P 策略引擎
- Excel 輸入 + Streamlit UI
- Gemini AI 戰術指令生成
- LINE 即時戰報通知

### v2.0（規劃中）
- 多策略並存（保守 / 進攻 / 事件型）
- 策略 Preset 與快速切換
- 回測模組（Historical CB Data）

### v3.0（遠期）
- Web 化（非 Streamlit）
- 多市場支援（TW / JP CB）
- 商業級權限與策略管理

---

## 🤝 Contributing

歡迎任何形式的貢獻：

1. Fork 本專案
2. 建立 feature branch (`feature/xxx`)
3. 提交 Pull Request，請清楚說明變更目的

建議貢獻方向：
- 新策略模型（替代 R/P）
- 資料源擴充（不同 CB 市場）
- UI/UX 改善

---

## ⚠️ Disclaimer

本專案僅為**研究與教育用途**，不構成任何投資建議。

使用者需自行承擔所有交易風險。
