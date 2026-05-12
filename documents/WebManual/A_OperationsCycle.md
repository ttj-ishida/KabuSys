# WEBマニュアル: 実運用サイクルと役割分担

- 対象: KabuSys の日次実運用
- 想定読者: 運用者、管理者、将来の利用者
- 目的: システムが実運用に入った後、1日の中で何が自動で行われ、どこでユーザーが確認・介入するのかを理解できるようにする

---

## 1. このシステムはどう動くか

KabuSys は、**市場が閉まっている時間に翌営業日の売買準備を行い、ザラ場中は発注と監視に専念する** システムです。

1日の流れは大きく分けて次の4段階です。

1. 引け後から夜間に、データ更新と分析を行う
2. 翌朝、Execution を起動し、売買準備を整える
3. ザラ場中に、発注・約定確認・監視を行う
4. 引け後に、当日結果を保存し、次の夜間バッチへ移る

この構成により、ザラ場中に重い計算処理を持ち込まず、発注処理を最優先にできます。

---

## 2. 1日の運用タイムライン

```text
07:50  PC・kabuステーション起動確認
08:00  Pre-Market Checklist（手動確認）
08:30  Execution 起動（自動）
09:00  Monitoring 起動（自動） / 前場開始
09:00-11:30  前場監視
11:30-12:30  昼休み
12:30-15:00  後場監視
15:00  市場クローズ確認
17:30  data_update バッチ（自動）
17:33  yahoo_news_collection バッチ（自動・News Addon のみ）
18:30  feature_generation バッチ（自動）
19:00  ai_analysis バッチ（自動・AI Addon のみ）
20:00  strategy_signal バッチ（自動）
21:00  portfolio_construction バッチ（自動）
21:15  night_batch_report 自動生成（KabuSys_NightBatchReport）
21:30  夜間バッチ結果確認（手動）
```

---

## 3. 時間帯ごとの処理内容

### 3.1 朝の確認（07:50-08:00）

この時間帯は、システムが安全に稼働できる前提を整える時間です。

ユーザーが確認すること:

- Windows PC が起動している
- スリープしていない
- kabuステーションが起動している
- kabuステーションにログイン済みである
- API 接続が正常である

システムはこの時点では、まだ売買を始めません。

### 3.2 Pre-Market Checklist（08:00）

市場開始前に、ユーザーが手動で運用チェックを行います。

確認方法:

`run_pre_market_report.py` が 08:00 前後に自動実行され、`artifacts/pre_market/{date}/report.md` にレポートを生成します。ステータスが `READY` であれば運用開始可能です。`BLOCKED` の場合は原因を確認して対処してください。

確認項目:

- 前日分データが正常に取り込まれている
- 本日の `Signal Queue` に `pending` シグナルが存在する
- DB 上のポジションと証券口座のポジションが一致している
- `data/stop_requested.flag` が存在しない
- Task Scheduler の KabuSys タスクが `Ready` 状態である

ここはユーザーの責任範囲です。  
この確認をせずに運用を始めると、Execution が正常に起動しても古いデータや不整合ポジションのまま売買する可能性があります。

### 3.3 Execution 起動（08:30）

Execution は Task Scheduler により自動起動します。

Execution が自動で行うこと:

1. 停止フラグの確認
2. 注文の自動リコンシリエーション
3. `pending` シグナルの読み込み
4. 発注準備開始

ユーザーが確認すること:

Execution 起動直後に `artifacts/execution_startup/{date}/report.md` が自動生成されます。ステータスが `READY` であれば継続可能です。

- `BLOCKED`（`orders_no_status > 0`）: 注文ステータス不明。二重発注リスクがあるため手動対応が必要
- `READY_WITH_WARNINGS`（`position_discrepancies` あり）: 執行は継続可能だが DB とブローカー間の数量差分を確認すること。差分の `kind` が `CLOSED_STATE_CONSTRAINT` の場合は `Filled→Closed` 遷移未実装による既知差分のため対応不要
- `READY`: 問題なし。発注ループを継続する

### 3.4 Monitoring 起動 / 前場開始（09:00）

09:00 からは、Monitoring も起動し、ザラ場監視体制に入ります。

ザラ場中に動くのは主に以下です。

- `execution_service`
- `monitoring_service`

夜間バッチのような重い分析処理は動きません。

### 3.5 ザラ場中（09:00-11:30 / 12:30-15:00）

システムが自動で行うこと:

- `pending` シグナル取得
- 発注
- 約定確認
- ポジション更新
- 口座余力チェック
- 二重発注防止
- ポジション上限チェック
- ドローダウン監視
- API 接続監視
- Kill Switch 判定

ユーザーが行うこと:

`run_intraday_monitor` を起動して Intraday Monitoring Interface でステータスを確認する。

```cmd
python -m kabusys.run_intraday_monitor --watch
```

または Streamlit ダッシュボードを開いて常時監視する:

```cmd
python -m streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

> ⚠️ Streamlit はターミナルを占有します。レポートスクリプトなどを別途実行する場合は、**新しいターミナルウィンドウ**を開いて `.venv\Scripts\Activate.ps1` を有効化してから実行してください。

ダッシュボードは 11 ページ構成です。

| ページ（サイドバー） | 主な確認内容 |
|---|---|
| **Home** | Kill Switch 状態 / Execution・Monitoring プロセス UP 確認 / ドローダウン / 直近エラーイベント |
| **Initial Setup** | 環境変数・設定・DB・Task Scheduler の初期セットアップ確認 |
| **Pre-Market** | 朝の READY/BLOCKED 判定 / データ鮮度 / 停止フラグ確認 |
| **Execution Startup** | 起動直後のリコンシリエーション差分 / ポジション整合確認 |
| **Intraday Monitor** | ザラ場監視（自動更新）/ Kill Switch 状態 / 注文エラー / ドローダウン |
| **Signal Queue** | 翌営業日の発注キュー（pending 件数）/ ポートフォリオ目標 / 直近シグナル |
| **Performance** | エクイティカーブ / 保有ポジション / 取引履歴 / Paper Verification |
| **Failure Recovery** | 障害イベント集約 / 復旧ガイド |
| **WebManual** | 運用マニュアル閲覧ビュー |
| **Process Monitor** | バッチジョブ実行状況 / 孤立プロセス（クラッシュ検知）/ 直近の完了ジョブ一覧 |
| **Strategy Lab** | 市場レジームスコア / AI スコアランキング / シグナル推移 |

確認項目:

- **Home > Overview** で Kill Switch が「発動なし」、Execution が「🟢 UP」であれば継続監視
- **Home > Overview** の直近エラーイベントに `ORDER_ERROR` / `RISK_BREACH` が表示されている場合は即時対応
- ドローダウンが -10% 超の場合は警告バナーが表示される（Kill Switch 発動を検討）

ザラ場中の基本方針は、**売買判断と執行はシステム、継続運転の最終監督はユーザー** です。

### 3.6 市場クローズ確認（15:00）

市場終了後に、ユーザーが当日の締め状態を確認します。

確認項目:

- `signal_queue` に `pending` が残っていないか
- `positions` テーブルが更新されているか
- `portfolio_performance` に本日分が記録されているか
- 必要なら Execution を停止する

この時間帯は、新規売買のためではなく、当日運用結果が正常に締められたかを確認する時間です。

### 3.7 夜間バッチ（17:30-21:15）

夜間バッチは、翌営業日のための準備時間です。

> **スケジュール設計の根拠**: J-Quants の日足データは東証引け（15:30）直後ではなく 16:30〜17:00 頃に公開されるため、data_update を 17:30 に設定しています。

#### 17:30 `data_update_job`

システムが行うこと:

- J-Quants から株価取得
- ニュース取得
- データ保存

更新テーブル:

- `prices_daily`
- `raw_news`
- `fundamentals`

#### 18:30 `feature_generation_job`

システムが行うこと:

- モメンタム計算
- ボラティリティ計算
- 出来高指標計算

保存先:

- `features`

#### 19:00 `ai_analysis_job`

システムが行うこと:

- ニュースセンチメント分析
- 市場レジーム判定

保存先:

- `ai_scores`
- `market_regime`

#### 20:00 `strategy_signal_job`

システムが行うこと:

- 戦略スコア算出
- 銘柄ランキング
- 売買シグナル生成

保存先:

- `signals`

#### 21:00 `portfolio_construction_job`

システムが行うこと:

- ポジションサイズ計算
- リスク制御適用
- 発注キュー生成

保存先:

- `signal_queue`

### 3.8 夜間バッチ結果確認（21:30）

21:15 に `KabuSys_NightBatchReport` が自動実行し、`artifacts/night_batch/{date}/` にレポートを生成します。  
ユーザーはこのレポートを確認して翌日の準備が整っているか判断します。

手動実行（再生成・確認時）:

```cmd
python scripts/run_night_batch_report.py
```

確認項目:

- バッチがすべて成功しているか（`data_update` / `feature_gen` / `strategy_signal` / `portfolio_construction`）
- エラーログがないか
- 明日の `Signal Queue` が作られているか

判定:

- `READY`: 全必須ジョブ成功かつ `signal_queue` 作成済み → 翌日執行可
- `READY_WITH_WARNINGS`: 警告はあるが翌営業日の準備は完了 → 内容確認の上で判断
- `BLOCKED`: 以下のいずれかに該当 → 翌朝の自動執行を開始しない
  - 必須ジョブが失敗 / 欠落
  - `signal_queue == 0`
  - `prices_daily == 0`（価格データ未取得）
  - `features == 0`（特徴量未生成）

夜間バッチが失敗している場合、翌朝の自動執行は危険です。  
少なくとも `Signal Queue` が妥当かどうかは、ユーザーが確認する前提です。

---

## 4. システムとユーザーの役割分担

## 4.1 システムの役割

システムが自動で行う範囲は以下です。

- データ取得
- 特徴量生成
- AI 分析
- 売買シグナル生成
- ポートフォリオ構築
- `Signal Queue` 生成
- 発注
- 約定確認
- ポジション更新
- ドローダウン監視
- API 接続監視
- Kill Switch 発動

要するに、**分析・執行・一次監視はシステム** が担当します。

## 4.2 ユーザーの役割

ユーザーが担当する範囲は以下です。

- 朝の事前確認
- PC と kabuステーションの稼働確認
- API 接続状態の確認
- ポジション整合性の確認
- Task Scheduler の状態確認
- ザラ場中の異常監視
- アラート発生時の判断
- 必要時の手動再起動
- 緊急停止の実行
- 夜間バッチ成功確認

要するに、**稼働環境の維持と最終判断はユーザー** が担当します。

---

## 5. 異常時の基本フロー

異常時は以下の順で対応します。

1. Monitoring が異常を検知する
2. アラートを出す
3. 必要に応じて Kill Switch を発動する
4. Execution を停止する
5. ユーザーがログと状態を確認する
6. 必要なら再起動または手動復旧を行う

### 代表的な異常

- Max Drawdown 超過
- API 接続断
- Execution プロセス停止
- 注文拒否多発
- Night Batch 失敗
- Signal Queue 空

### ユーザーの基本判断

- 軽微: ログを確認して継続監視
- 中程度: 対象コンポーネントを再起動
- 重大: Kill Switch 発動後に手動確認

---

## 6. 運用の考え方

このシステムは、完全放置型ではありません。

正しい理解は以下です。

- システムが翌営業日の売買準備を自動で行う
- システムがザラ場中の執行と監視を自動で行う
- ただし、運用継続の最終責任はユーザーが持つ

つまり、KabuSys は **自動執行 + 人間監督型** の運用モデルです。

---

## 7. 運用者向けチェックリスト

### 毎朝

- PC は起動しているか
- kabuステーションはログイン済みか
- API 接続は正常か
- 本日の `Signal Queue` はあるか
- ポジション整合性は取れているか
- 停止フラグは残っていないか

### ザラ場中

`python -m kabusys.run_intraday_monitor --watch` を起動して以下を確認する:

- ステータスが `OK` であれば継続監視
- `WARNING`: 注文エラー・滞留注文・ドローダウン超過などの内容を確認し対処する
- `CRITICAL`: Kill Switch 発動または Execution 停止 → 即時対応する

### 引け後

`run_market_close_report.py` を実行して Market Close Summary を確認する。

```cmd
python -m kabusys.run_market_close_report --save
```

- ステータスが `OK` であれば夜間バッチへ進む
- `BLOCKED` の場合は Warnings を確認し、問題を解消してから再実行する

確認項目:

- `signal_queue` に当日 `pending` が残っていないか
- `positions` は当日分が更新されたか
- `portfolio_performance` は当日分が記録されたか

Market Close Summary が `OK` であれば、日次成績レポートを生成する。

```cmd
python -m kabusys.run_performance_report --type daily --save
```

レポートは `artifacts/performance/live/daily/{date}/report.md` に保存される。

### 夜

- `data_update` 成功
- `feature_generation` 成功
- `ai_analysis` 成功
- `strategy_signal` 成功
- `portfolio_construction` 成功
- 明日の `Signal Queue` がある

---

## 8. まとめ

KabuSys の実運用は、次の分担で回ります。

- 夜間: システムが翌営業日の準備を行う
- 朝: ユーザーが前提条件を確認する
- ザラ場: システムが執行し、ユーザーが監督する
- 引け後: システムが結果を保存し、ユーザーが締め確認を行う

この運用サイクルを守ることで、Single Windows Node 上でも安全性と再現性を保った実運用が可能になります。
