# A. 概要・全体像

- 対象: KabuSys を初めて使う運用者
- 目的: 何ができるか、どの順で読めばよいかを短く把握する

---

## A-1. KabuSys とは何か

KabuSys は、日本株の日次運用を前提にした自動売買支援システムです。  
夜間バッチで翌営業日の候補を作り、朝に運用可否を確認し、ザラ場で注文と監視を行い、引け後に結果を記録します。

前提:

- Windows
- kabuステーション API
- J-Quants

---

## A-2. このシステムで何ができるか

Core 機能:

- 日次データ更新
- 特徴量生成
- AI によるニュース / regime 補助判定
- 売買シグナル生成
- ポートフォリオ構築
- 自動執行
- リスク管理と Kill Switch
- 日次 / 週次 / 月次レポート

運用インターフェース:

- CLI レポート
- Streamlit ダッシュボード
- Streamlit 内 WebManual ビュー

Streamlit で確認できる主なページ:

- `Home`
- `Initial Setup`（初期セットアップ確認）
- `Pre-Market`（朝の READY/BLOCKED 判定）
- `Execution Startup`（起動直後の差分確認）
- `Intraday Monitor`（ザラ場監視・自動更新）
- `Signal Queue`
- `Performance`（Paper Verification 含む）
- `Failure Recovery`（障害イベント集約）
- `WebManual`
- `Strategy Lab`

---

## A-3. 読む順番

1. [B_CoreSetup.md](./B_CoreSetup.md)
2. [A_OperationsCycle.md](./A_OperationsCycle.md)
3. [C_PaperTrading.md](./C_PaperTrading.md)
4. [D_LiveOperation.md](./D_LiveOperation.md)
5. [E_FailureRecovery.md](./E_FailureRecovery.md)
6. [A_StrategyFlow.md](./A_StrategyFlow.md) — 売買判断の詳細フロー（深掘り用）

---

## A-4. 1日の流れ

```text
15:30  data_update
16:00  feature_gen
18:00  ai_analysis
20:00  strategy_signal
21:00  portfolio_construction
21:30  Night Batch 状態確認
08:00  pre_market_report
08:30  execution start
09:00  monitoring start
15:00  market_close_report
```

運用判断は、個別ログだけでなく次のレポートで行う。

- `run_pre_market_report`
- Execution Startup Summary（`run_execution.py` 実行時に自動保存）
- `run_market_close_report`
- Night Batch 状態確認（Task Scheduler + Signal Queue）
- `run_performance_report`

---

## A-5. 画面で見るか、CLI で見るか

CLI が向くもの:

- バッチ結果の明示確認
- 障害時の詳細確認
- スクリプト再実行

Streamlit が向くもの:

- 日中監視
- Signal Queue / Performance の可視化
- WebManual の横断参照

方針:

- 実処理は CLI / service 側
- Streamlit は表示と導線

---

## A-6. 関連

- [A_OperationsCycle.md](./A_OperationsCycle.md)
- [B_CoreSetup.md](./B_CoreSetup.md)
- [C_PaperTrading.md](./C_PaperTrading.md)
- [D_LiveOperation.md](./D_LiveOperation.md)
- [E_FailureRecovery.md](./E_FailureRecovery.md)
