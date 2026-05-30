# Phase 2 バックテスト戦略

- 対象: KabuSys Phase 2（資産規模 〜500万円）の戦略検証
- 作成: 2026-05-31
- 前提: Phase 1 最終採用設定 P2_n1b_o2 の実運用が開始済みであること

---

## 1. Phase 2 の位置づけ

### 1.1 フェーズ定義

| フェーズ | 資産規模  | 優先目標                       |
| -------- | --------- | ------------------------------ |
| Phase 1  | 〜100万円 | 生存・学習。ドローダウン最小化 |
| **Phase 2**  | **〜500万円** | **安定成長。Sharpe > 1.0**    |
| Phase 3  | 500万円〜 | リターン最大化                 |

### 1.2 Phase 2 移行条件（Phase 1 Section 27.5 より）

| 条件                   | 閾値    |
| ---------------------- | ------- |
| 実運用継続期間         | ≥ 6ヶ月 |
| 実績 CAGR（年換算）    | > 5%    |
| 実績 Max DD            | < 25%   |

---

## 2. Phase 1 の知見・引き継ぎ

### 2.1 Phase 1 最終採用設定（P2_n1b_o2）

| パラメータ              | 値                              |
| ----------------------- | ------------------------------- |
| max_positions           | 3                               |
| max_utilization         | 30%                             |
| MA200 フィルター        | ON                              |
| TOPIX Bear Guard        | OFF（weak=1.0 / strong=1.0）    |
| DD stop                 | 12%（30日タイムアウト）         |
| threshold               | 0.58（基本）                    |
| 施策A（動的閾値）       | ON: vol<12% 時に 0.62 へ引き上げ |
| 施策B（多段階ストップ） | ON: Stage2=1.8×, Stage3=1.5×   |
| stop_loss               | 9%                              |
| max_holding_days        | 60日                            |
| trailing_stop_atr_mult  | 2.0（Stage1）                   |

### 2.2 Phase 1 最終成績（2017〜2025通算）

| 指標          | 値         | Phase 1 基準 | Phase 2 目標 |
| ------------- | ---------- | ------------ | ------------ |
| CAGR          | **8.31%**  | > 5% ✅      | > 8%         |
| Sharpe        | **0.428**  | > 0.5 ❌     | > 0.5 → 1.0  |
| Max DD        | **19.10%** | < 25% ✅     | < 20%        |
| Profit Factor | **1.321**  | > 1.1 ✅     | > 1.3        |

### 2.3 Sharpe 頭打ちの構造的原因

Group A〜Q（延べ 100+ シナリオ）の検証を通じて判明した根本原因:

**「max_positions=3 + util=30% という高集中構成が、2018・2024 年の高ボラ局面に収益を偏中させている」**

```
年次リターン分布（P2_n1b_o2）:
  2017: -6.5%    2018: +64.3%   2019: +0.8%
  2020: +4.2%    2021: -3.4%    2022: -2.2%
  2023: -0.8%    2024: +27.7%   2025: +2.1%
  → 2018・2024 の 2 年で CAGR の大半を生成
  → 残る 7 年がフラット〜マイナス → 年次標準偏差が大きく Sharpe が低い
```

### 2.4 Phase 1 で試して有効だった手法

| 手法                         | 効果                  | 採用 |
| ---------------------------- | --------------------- | ---- |
| util=30%（Group G/H/I）      | MaxDD < 25% 達成の主因 | ✅   |
| MA200 銘柄フィルター（Group I）| MaxDD 26.2% → 24.96% | ✅   |
| 施策A: 動的閾値（Group N）    | Sharpe +0.038          | ✅   |
| 施策B: 多段階ストップ（Group P）| MaxDD -5.86pt（A との複合）| ✅ |

### 2.5 Phase 1 で試して機能しなかった手法（Phase 2 でも注意）

| 手法                             | 結果              |
| -------------------------------- | ----------------- |
| TOPIX Bear Guard（Group E）      | CAGR を 12pt 毀損 |
| MA200 単体フィルター（Group H2）  | CAGR -5.29% に悪化 |
| RSI フィルター（Group K2/K7/K9） | I1 を大幅下回る   |
| 銘柄集中（max_positions=2）      | CAGR マイナス転落 |
| ボラティリティターゲティング（Group L）| 全シナリオ I1 以下 |
| BB 逆張り戦略（Group BB）        | MaxDD 95%+（採用不可）|

---

## 3. Phase 2 アプローチ概要

### 3.1 推奨アプローチと実行順序

Sharpe の構造的問題（収益の年次偏中）を解決するため、以下の順で検証する。

```
Step 0: Section 47 — OOS 検証（先行必須）
  ├─ P2_n1b_o2 の過剰適合リスクを確認
  └─ クリア → Phase 2 設定探索 Go

Step 1: Section 48 — Group R（ポジション数・utilization グリッド）
  ├─ 実装変更ゼロ。パラメータ変更のみ
  ├─ Phase 2 資本（〜500万円）で初めて現実的になる選択肢
  └─ 採択設定 → Step 2 のベースとして使用

Step 2: Section 49 — Group S（マルチレジーム適応閾値）
  ├─ Group N 施策A（+0.038 Sharpe 実証済み）を 3 値レジームに拡張
  └─ Group R 採択設定と組み合わせて Sharpe 0.5+ 突破を狙う
```

### 3.2 優先度と工数

| Step | Issue | アプローチ | 実装工数 | 期待効果 |
| ---- | ------ | ---------- | -------- | -------- |
| 0 | #374 | OOS 検証 | 低（スクリプト作成のみ） | リスク確認 |
| 1 | #375 | Group R: ポジション数・util グリッド | 低（実装変更ゼロ） | Sharpe 構造改善（0.5+ 狙い） |
| 2 | #376 | Group S: マルチレジーム閾値 | 中（signal_generator 拡張） | Sharpe +0.05〜0.10 |

---

## 4. バックテスト採択基準

9 年間データ（2017〜2025）を使用。Phase 1 より厳格化する。

| 指標          | Phase 1 基準 | **Phase 2 基準** | 根拠                           |
| ------------- | ------------ | ---------------- | ------------------------------ |
| CAGR          | > 5%         | **> 8%**         | P2 実績（8.31%）を超えること   |
| Sharpe        | > 0.5        | **> 0.5**        | Phase 2 の最優先目標           |
| Max DD        | < 25%        | **< 25%**        | Phase 1 実績（19.10%）を維持   |
| Profit Factor | > 1.1        | **> 1.3**        | P2 実績（1.321）を維持         |
| 利益年数      | ≥ 6/9年      | **≥ 6/9年**      | 継続                           |

---

## 5. Section 47 — Phase 2 事前検証: OOS 検証（Issue #374）

### 5.1 目的

P2_n1b_o2 の最適化サンプル（2017〜2021）以外のデータでロバスト性を確認し、
Phase 2 設定探索の前提として過剰適合リスクを定量化する。

### 5.2 シナリオ定義

設定: P2_n1b_o2 固定（全シナリオ共通）

| シナリオ       | 期間            | 目的                                     |
| -------------- | --------------- | ---------------------------------------- |
| OOS_full       | 2017〜2025      | P2 参照値の再現確認（CAGR 8.31% と一致するか）|
| OOS_2022_2025  | 2022〜2025      | 直近 4 年の OOS 成績                     |
| OOS_2023_2025  | 2023〜2025      | 最新 3 年の OOS 成績                     |
| OOS_walk_fwd   | 2017〜2025（1年ウォークフォワード） | IS→OOS のロールでの一貫性 |

### 5.3 採択基準

| 指標                  | 基準    |
| --------------------- | ------- |
| OOS CAGR              | > 5%    |
| OOS Max DD            | < 25%   |
| IS/OOS Sharpe の乖離  | < 0.15  |

### 5.4 採択判断ロジック

```
OOS 基準クリア → Phase 2 設定探索 Go（Section 48 へ）
OOS 大幅乖離   → P2 設定を OOS データで再調整してから移行
```

### 5.5 実行スクリプト

```
backtest/backtest_improvement_plan/run_phase2_oos.py
```

```powershell
python backtest/backtest_improvement_plan/run_phase2_oos.py --workers 4
```

出力先: `artifacts/backtest/backtest_phase2_oos/{timestamp}/`

---

## 6. Section 48 — Group R: ポジション数・utilization グリッドサーチ（Issue #375）

### 6.1 背景・仮説

Phase 1 の Sharpe 頭打ち（0.428）は **max_positions=3 + util=30% という高集中構成** に起因する。
Phase 2（資本 〜500万円）でポジション数を拡大することで銘柄分散が増し、
年次リターンのブレ（Sharpe の分母）を抑制できる。

Phase 1 の検証知見:
- Group G3（util=30%）→ Group I1（util=30% + MA200）: utilization 変更が MaxDD 改善の主要因
- Phase 1 では 1 銘柄あたり最大 10%（30% / 3 銘柄）を占める集中度

**この検証は追加実装ゼロ。パラメータ変更のみで実行できる。**

### 6.2 シナリオ定義

ベース設定: P2_n1b_o2（施策A+B ON、MA200 ON、BG OFF、DD stop=12%）  
固定設定: threshold=0.58, stop_loss=9%, 施策A ON, 施策B ON, 期間 2017〜2025

| シナリオ | max_positions | max_utilization | 1銘柄リスク比率 | 狙い |
| -------- | ------------- | --------------- | --------------- | ---- |
| R0_p2_ref | 3 | 30% | 10.0% | P2 参照（Phase 1 最終採用） |
| R1 | 5 | 40% | 8.0% | 銘柄数+2・投下率+10pt |
| R2 | 5 | 50% | 10.0% | 銘柄数+2・投下率+20pt |
| R3 | 7 | 40% | 5.7% | 銘柄数+4・投下率+10pt（分散重視） |
| R4 | 7 | 50% | 7.1% | 銘柄数+4・投下率+20pt |
| R5 | 7 | 60% | 8.6% | 銘柄数+4・投下率+30pt（積極） |
| R6 | 10 | 50% | 5.0% | 最大分散（Phase 2 上限候補） |

> **1銘柄リスク比率** = max_utilization / max_positions。R3（5.7%）が Phase 1（10.0%）の約半分。

**読み方**:
- R0 → R1〜R6: ポジション数と投下率の組み合わせが Sharpe・CAGR・MaxDD をどう動かすか
- `max_positions × (1銘柄あたりサイズ)` の総量が MaxDD と CAGR の両方を規定する

### 6.3 採択判断ロジック

```
いずれかのシナリオで Sharpe > 0.5 かつ CAGR > 8% かつ MaxDD < 25%
  → 当該設定を Phase 2 採用候補として選択 → Section 49 のベースとする

全シナリオで Sharpe > 0.5 未達だが R0（P2）より Sharpe が改善
  → 最良設定を Phase 2 ベースとして採用、Sharpe 改善は Group S に委ねる

全シナリオで R0 以下
  → ポジション数拡大では構造改善不可。Phase 3 課題として保留
```

### 6.4 実行スクリプト

```
backtest/backtest_improvement_plan/run_phase2_group_r.py
```

```powershell
python backtest/backtest_improvement_plan/run_phase2_group_r.py --workers 4
```

出力先: `artifacts/backtest/backtest_phase2_group_r/{timestamp}/`

---

## 7. Section 49 — Group S: マルチレジーム適応閾値（施策A 拡張）（Issue #376）

### 7.1 背景・仮説

Group N 施策A（TOPIX ボラティリティが低い局面で BUY 閾値を 0.58→0.62 に引き上げ）は
P2_n1b_o2 の Sharpe を **+0.038 改善**した実証済みのアプローチ。

現実装は 2 値（低ボラ時のみ引き上げ）。TOPIX の相場局面は実際には 3 段階ある:

```
高ボラ・強トレンド局面（2018・2024年）
  → 現行 threshold=0.58 でエントリー。高ボラ時は閾値を下げて機会を増やす余地あり

中ボラ・通常局面
  → 現行 threshold=0.58 を維持

低ボラ・レンジ局面（2017・2021年）
  → 現行: 施策A で 0.62 へ引き上げ（実証済み効果）
     拡張: 0.63〜0.65 へさらに厳格化する余地あり
```

3 値レジームに拡張することで、施策A の効果をさらに引き出す。

### 7.2 シナリオ定義

ベース設定: Group R 採択設定（未確定時は P2_n1b_o2）  
固定設定: 施策B ON、MA200 ON、BG OFF、DD stop=12%、期間 2017〜2025

| シナリオ | vol 閾値（低） | vol 閾値（高） | thr 低ボラ | thr 中ボラ | thr 高ボラ | 狙い |
| -------- | -------------- | -------------- | ---------- | ---------- | ---------- | ---- |
| S0_p2_ref | 0.12 | — | 0.62 | 0.58 | — | 施策A 現行（2値・参照） |
| S1 | 0.12 | 0.25 | 0.62 | 0.58 | 0.55 | 高ボラ積極化の単体効果 |
| S2 | 0.10 | 0.20 | 0.63 | 0.58 | 0.55 | 閾値帯を広げる |
| S3 | 0.12 | 0.25 | 0.62 | 0.58 | 0.58 | 高ボラ積極化のみ（低ボラ維持） |
| S4 | 0.12 | 0.25 | 0.65 | 0.58 | 0.55 | 低ボラ時をより厳格化 |
| S5 | 0.15 | 0.30 | 0.62 | 0.58 | 0.55 | vol 帯を広め設定 |

**読み方**:
- S0 → S1: 高ボラ時の threshold 引き下げ（0.58→0.55）の単体効果
- S0 → S4: 低ボラ時の threshold 引き上げ（0.62→0.65）の追加効果
- S1〜S5: vol 閾値・threshold 組み合わせのグリッド探索

### 7.3 必要な実装変更

| ファイル | 変更内容 |
| -------- | -------- |
| `src/kabusys/strategy/signal_generator.py` | `adaptive_threshold_vol_regime` を 3 値レジーム対応に拡張。`topix_vol_high_threshold`・`adaptive_threshold_lo` パラメータを追加 |
| バックテストスクリプト | `--adaptive-threshold-lo`・`--topix-vol-high-threshold` CLI フラグを追加 |

### 7.4 採択判断ロジック

```
いずれかのシナリオで Sharpe > 0.5 かつ CAGR > 8% かつ MaxDD < 25%
  → 当該設定を Phase 2 最終採用（Group R 設定 + 施策A 3 値）

Sharpe が 0.428〜0.5 の範囲で S0 を上回るシナリオが存在
  → 最良シナリオを Phase 2 ベースとして採用
  → Sharpe 0.5 突破は Phase 3 以降の課題

全シナリオで S0 以下
  → マルチレジーム拡張では改善不可。別アプローチを検討
```

### 7.5 実行スクリプト

```
backtest/backtest_improvement_plan/run_phase2_group_s.py
```

```powershell
python backtest/backtest_improvement_plan/run_phase2_group_s.py --workers 4
```

出力先: `artifacts/backtest/backtest_phase2_group_s/{timestamp}/`

---

## 8. 今後の研究課題（Group R/S 以降）

Group R・S でも Sharpe > 1.0（Phase 2 主目標）に届かない場合の次手候補。
詳細設計は Group R/S の結果を踏まえて策定する。

| 課題 | 概要 | 優先度 |
| ---- | ---- | ------ |
| マルチ戦略化 | 第二戦略（例: クオリティ安定配当）との組み合わせで収益の年次偏中を解消 | 高（長期） |
| ATR リスク均等化サイジング | 個別銘柄 ATR 逆数でポジションサイズを調整。K8（PF 1.428）の MaxDD を改善 | 中 |
| OOS ウォークフォワード継続評価 | 実運用 6ヶ月ごとに IS/OOS の乖離をモニタリング | 継続 |
| Phase 3 移行設計 | 500万円超での max_positions・utilization・戦略の再設計 | 低（先行） |

---

## 9. 参考

- `documents/07_Research/Phase1_Backtest_Strategy.md`（Section 27〜46: Phase 1 全検証結果）
- `documents/10_Runtime/RuntimeJobSchedule.md`
- GitHub Issues: #374（OOS検証）、#375（Group R）、#376（Group S）
