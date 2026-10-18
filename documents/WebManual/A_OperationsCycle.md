# WEBマニュアル: 実運用サイクルと役割分担

- 対象: KabuSys の日次実運用
- 想定読者: 運用者、管理者、将来の利用者
- 目的: 1日の中で何が自動で行われ、どこでユーザーが確認・判断・入力するのかを理解できるようにする

---

## 1. このシステムはどう動くか

KabuSys は、**市場が閉まっている時間に翌営業日の売買候補を作り、前日夜・当日朝にユーザーが手動注文を判断できるようにする** システムです。

現在の運用方式は **手動注文メイン** です。

- KabuSys は候補（BUY / SELL・株数・買付可能な価格の範囲）を出すだけで、発注はしません
- ユーザーが証券画面で手動で注文し、約定したら KabuSys に約定を入力します
- kabuステーション API による自動執行は停止中です（`.env` の `ENABLE_AUTO_EXECUTION=false`）
- **自動売却の機能はありません。** SELL は「売却候補」として提示されるだけで、売るかどうかはユーザーが決めます

1日の流れは大きく分けて次の4段階です。

1. 引け後から夜間に、データ更新・分析・候補作成を行う（自動）
2. 夜と翌朝に、LINE とレポートで候補を確認する
3. ユーザーが証券画面で手動注文し、約定結果を KabuSys に登録する
4. 売却候補が出たら、売るかどうかを判断して対応する

この構成により、kabuステーションの起動・ログイン維持に依存せず、日次の売買判断を継続できます。

---

## 2. 1日の運用タイムライン

```text
08:00  pre_market_report（自動。自動執行の可否判定。手動運用中は BLOCKED でも問題なし）
08:02  signal_queue_report（自動）
08:05  manual_order_report --phase morning（自動・朝 LINE「【KabuSys 手動注文 当日朝】」）
08:05〜 朝のレポートを確認して注文内容を決める（手動）
09:00  寄り付き。証券画面で手動注文（手動）
約定後  約定を CLI / Streamlit で入力（手動）
15:35  tdnet_collection（自動・ENABLE_TDNET=true のみ）
17:30  data_update（自動）
17:33  yahoonews_collection（自動・ENABLE_YAHOONEWS=true のみ）
18:30  feature_gen（自動）
19:00  ai_analysis（自動・ENABLE_AI_SENTIMENT=true のみ）
20:00  strategy_signal（自動。手動保有の売却候補もここで作る）
21:00  portfolio_construction（自動・夜 LINE で翌営業日の BUY / SELL を通知）
21:10  manual_order_report --phase evening（自動・LINE なし）
21:15  night_batch_report（自動）
21:30  夜 LINE と夜間バッチ結果を確認（手動）
```

> 自動執行用の 08:30 `execution_start`、08:35 `position_reconciliation_report`、09:00 `monitoring_start` は、手動運用中はスケジューラーが実行しません。

---

## 3. 時間帯ごとの処理内容

### 3.1 夜（21:00〜21:30）: 翌営業日の候補を知る

**夜 LINE（21:00 portfolio_construction）**

翌営業日の BUY / SELL 候補が届きます。手動で保有している銘柄には `[手動保有]`、手動保有中の銘柄が BUY 候補になった場合は不足分だけが `[買い増し]` と表示されます。

**夜のレポート（21:10）**

`artifacts/manual_orders/{日付}/evening.md` に、朝のレポートとほぼ同じ内容（BUY / SELL・資金・見送りルール）が出ます。LINE は送りません。

**夜間バッチ結果（21:15）**

`artifacts/reports/{日付}/report.md` に night_batch_report が出ます。確認するのは、必須ジョブ（`data_update` / `feature_gen` / `ai_analysis` / `strategy_signal` / `portfolio_construction`）がすべて `success` かどうかです。

| 判定 | 意味 | 手動運用での扱い |
|---|---|---|
| `READY` | 全必須ジョブ成功・`signal_queue` 作成済み | 翌朝のレポートどおりに進める |
| `READY_WITH_WARNINGS` | 警告はあるが翌営業日の準備は完了 | 警告内容を確認する |
| `BLOCKED` | 必須ジョブ失敗 / `signal_queue == 0` / `prices_daily == 0` / `features == 0` | ジョブ失敗なら復旧が必要。ジョブがすべて成功していて BUY が 0 件なだけ（例: `breadth_stop`）なら正常 |

手動で再生成する場合:

```cmd
python scripts/run_night_batch_report.py
```

### 3.2 朝（08:05〜）: 朝のレポートを読む

08:05 に `manual_order_report_morning` が `artifacts/manual_orders/{日付}/morning.md`（と `.json`）を作り、LINE「【KabuSys 手動注文 当日朝】」を送ります。

**ステータスの読み方:**

| ステータス | 意味 | 対応 |
|---|---|---|
| `OK` | 警告なし | BUY 表・SELL 表を見て注文を検討する |
| `警告あり` | 警告がある（データ鮮度など） | 警告を読んでから判断する |
| `BUY 見送り` | 停止フラグ・DD 停止・休場日・シグナルが古い のいずれか | BUY は全件「見送り候補」に移る。SELL は常に表示されるので SELL だけ対応する |

> **既知の誤警告（Issue #421）:** シグナルが 0 件の正常な日（例: `breadth_stop` で BUY 全件停止）でも「シグナルが古い」と出ます。夜間バッチが本当に失敗したかどうかは `logs/scheduler.log` と night_batch_report で確認してください。

**BUY 表の読み方:**

| 列 | 意味 |
|---|---|
| コード・銘柄名 | 5 桁コード（例: `72030`） |
| 株数 | 推奨株数（買い増しの場合は不足分だけ） |
| 参考価格 | 前日終値 |
| 想定金額 | 株数 × 参考価格 |
| スコア | 戦略スコア（順位も表示） |
| この価格以下なら買付可（上限） | 寄り付きがこれ以下なら買ってよい（前日終値比 +5% の境界） |
| この価格以上なら買付可（下限） | 寄り付きがこれ以上なら買ってよい（前日終値比 −3% の境界） |
| 備考 | 新規 / 買い増し |

見送りルールは「寄り付きが前日終値比 +5% 超 / −3% 以下なら見送り」です。寄り前の気配は取得しないため、ギャップ率は自動計算しません。**寄り付き価格が下限以上・上限以下なら買付可、範囲外なら見送り**と判断します。

**資金欄（`MANUAL_TRADING_ENABLED=true` のとき）:**

- 総資産 = 元手（`MANUAL_TRADING_INITIAL_CASH`）− 手動の買付額（手数料込み）+ 売却額（手数料差引）+ 保有時価
- 1 銘柄上限 = 総資産の 10%

**08:00 の pre_market_report について:**

pre_market_report は**自動執行を開始してよいか**の判定です（前営業日の `signal_queue` に pending がない・停止フラグ・スケジューラー未稼働 → `BLOCKED`）。手動運用では BUY 候補 0 件の日などに `BLOCKED` になりますが、手動注文の判断には朝の手動注文レポートを使うので問題ありません。

### 3.3 寄り付き: 証券画面で手動注文する

1. 朝のレポートの BUY 表から注文する銘柄・株数を決める
2. 寄り付き価格が上限・下限の範囲外なら見送る
3. SELL 表（売却候補）の銘柄は、売るかどうかを判断して売り注文を出す

### 3.4 約定後: 約定を入力する

約定したら、運用フォルダ（`C:\Projects\KabuSys`）で約定を入力します。銘柄コードは 5 桁です。

```powershell
# プレビュー（--apply なしでは保存しない）
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0

# 保存
.venv\Scripts\python.exe -m kabusys.manual_trades add --date 2026-10-15 --code 44770 --side buy --qty 100 --price 387 --fees 0 --apply

# 対話式
.venv\Scripts\python.exe -m kabusys.manual_trades wizard

# 確認・保有・削除
.venv\Scripts\python.exe -m kabusys.manual_trades list --date 2026-10-15
.venv\Scripts\python.exe -m kabusys.manual_trades positions
.venv\Scripts\python.exe -m kabusys.manual_trades delete <trade_id>
```

- 同日・同銘柄・同売買の 2 件目以降は ID に `_2`、`_3`… が付きます
- 全く同じ内容を 2 回入れると重複エラーになります（意図的なら `--allow-duplicate`）
- 保有を超える売却はエラーになります（記録開始前から持っていた株などは `--allow-oversell`）
- 夜間バッチ中（17:30〜21:20 頃）は DuckDB が排他利用されるため、入力はこの時間帯を避けてください

Streamlit の **Manual Trades** ページ（入力／手動ポジション／売却候補／履歴）からも入力できます。

### 3.5 売却候補への対応

手動保有にも自動売買と同じ SELL ルール（損切り・トレーリングストップ・保有期限・スコア低下・決算回避）が適用され、20:00 の `strategy_signal` で「売却候補」として記録されます。夜 LINE と朝のレポートの SELL 表にも出ます。

1. 証券画面で売却する
2. 約定を `--side sell` で入力する
3. Streamlit **Manual Trades > 売却候補** で「対応済み」にする（売らない場合は「見送り」）

### 3.6 Streamlit ダッシュボード

```powershell
python -m streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

ダッシュボードは Home と 11 ページで構成されています。

| ページ（サイドバー） | 主な確認内容 | 手動運用での使用 |
|---|---|---|
| **Home** | Kill Switch 状態 / Execution・Monitoring プロセス状態 / ドローダウン / 直近エラーイベント | 参考 |
| **Initial Setup** | 環境変数・設定・DB・Task Scheduler の初期セットアップ確認 | 導入時 |
| **Pre-Market** | 朝の READY/BLOCKED 判定 / データ鮮度 / 停止フラグ確認 | 参考 |
| **Execution Startup** | 起動直後のリコンシリエーション差分 / ポジション整合確認 | 自動執行時のみ |
| **Intraday Monitor** | ザラ場監視（自動更新）/ Kill Switch 状態 / 注文エラー / ドローダウン | 自動執行時のみ |
| **Signal Queue** | 翌営業日の BUY 候補（`signal_queue`）/ ポートフォリオ目標 / 直近シグナル（参照専用） | 使う |
| **Performance** | エクイティカーブ / 保有ポジション / 取引履歴 / Paper Verification | 参考 |
| **Failure Recovery** | 障害イベント集約 / 復旧ガイド | 障害時 |
| **WebManual** | 運用マニュアル閲覧ビュー | 使う |
| **Strategy Lab** | 市場レジームスコア / AI スコアランキング / シグナル推移 | 参考 |
| **Process Monitor** | バッチジョブ実行状況 / 孤立プロセス（クラッシュ検知）/ 直近の完了ジョブ一覧 | 使う（夜間バッチ確認） |
| **Manual Trades** | 約定入力 / 手動ポジション（評価日の終値で評価）/ 売却候補（対応済み・見送りに更新、日付で絞り込み）/ 履歴 | **毎日使う** |

### 3.7 夜間バッチ（15:35〜21:15）

夜間バッチは、翌営業日のための準備時間です。

> **スケジュール設計の根拠**: J-Quants の日足データは東証引け（15:30）直後ではなく 16:30〜17:00 頃に公開されるため、data_update を 17:30 に設定しています。

> ℹ️ スケジューラーデーモン（`KabuSys_Scheduler`）は、DuckDB に書き込むジョブの前に Execution が動いていれば自動停止します（DuckDB ロック解消）。土日・祝日は全ジョブがスキップされます。

#### 17:30 `data_update`

- J-Quants から株価・財務・TOPIX などを取得
- 更新テーブル: `prices_daily` / `fundamentals` / `raw_news` / `topix_daily`

#### 18:30 `feature_gen`

- モメンタム・ボラティリティ・流動性などの特徴量を計算
- 保存先: `features`

#### 19:00 `ai_analysis`

- ニュースセンチメント分析・市場レジーム判定
- 保存先: `ai_scores` / `market_regime`
- ⚠️ 現在スコアが出ていません（ニューススコア 0 件・レジーム常に neutral。Issue #419）

#### 20:00 `strategy_signal`

- 戦略スコア算出・BUY / SELL シグナル生成
- 手動保有の売却候補を `manual_action_queue` に記録
- 保存先: `signals`

#### 21:00 `portfolio_construction`

- ポジションサイズ計算・リスク制御
- 翌営業日の BUY 候補を `signal_queue` に保存（`signal_queue` には BUY だけが入る）
- 夜 LINE を送信

---

## 4. システムとユーザーの役割分担

## 4.1 システムの役割

- データ取得
- 特徴量生成
- AI 分析
- 売買シグナル生成
- ポートフォリオ構築（BUY 候補と株数）
- 夜 LINE・朝 LINE・手動注文候補レポート
- 手動保有の評価
- 売却候補の提示

要するに、**分析・候補提示・評価はシステム** が担当します。

## 4.2 ユーザーの役割

- 夜 LINE・朝のレポートの確認
- 注文候補の採否判断（寄り付きと上限・下限の比較）
- 証券画面での手動発注（BUY・SELL とも）
- 約定結果の入力
- 売却候補への対応
- 夜間バッチ成功の確認
- スケジューラー（`KabuSys_Scheduler`）の稼働確認・必要時の手動復旧

要するに、**発注と最終判断、稼働環境の維持はユーザー** が担当します。

---

## 5. 異常時の基本フロー

1. `logs/scheduler.log` で失敗したジョブを確認する（`REQUIRES ATTENTION: ジョブ失敗`）
2. `logs/<job_name>.log` でエラー内容を確認する
3. 原因を解消して、必要なジョブを手動で再実行する
4. 翌朝に復旧する場合は `--date <前営業日>` を付けて `strategy_signal` と `portfolio_construction` を再実行する

詳細は [E_FailureRecovery.md](./E_FailureRecovery.md) と `documents/08_Operations/FailureRecovery.md` を参照してください。

### 代表的な異常

- 夜間バッチ失敗（データ未取得・特徴量 0 件など）
- スケジューラー停止（PC スリープ・ログオフ）
- 朝のレポートが `BUY 見送り`（停止フラグ・DD 停止・シグナルが古い。#421 の誤警告に注意）

---

## 6. 運用の考え方

このシステムは、完全放置型ではありません。

正しい理解は以下です。

- システムが翌営業日の売買候補を自動で作る
- ユーザーが候補を見て判断し、証券画面で発注する
- 約定は KabuSys に入力し、システムが保有を評価して売却候補を出す
- 運用継続の最終責任はユーザーが持つ

つまり、KabuSys は **候補提示 + 手動注文型** の運用モデルです。自動執行は停止中で、再開する場合の手順は [D_LiveOperation.md](./D_LiveOperation.md) の「自動執行を再開する場合」を参照してください。

---

## 7. 運用者向けチェックリスト

### 夜（21:30 頃）

- 夜 LINE が届いたか（翌営業日の BUY / SELL）
- night_batch_report の必須ジョブがすべて `success` か
- 失敗があれば `logs/scheduler.log` を確認

### 朝（08:05〜）

- 朝 LINE が届いたか
- ステータスが `OK` / `警告あり` / `BUY 見送り` のどれか
- BUY 表の上限・下限と寄り付き価格を比べて注文を決める
- SELL 表（売却候補）があれば対応を決める

### 約定後

- 約定を `manual_trades add ... --apply`（または `wizard` / Streamlit）で入力したか
- `manual_trades positions` で保有が合っているか
- 売った売却候補を「対応済み」にしたか

---

## 8. まとめ

KabuSys の実運用は、次の分担で回ります。

- 夜間: システムが翌営業日の候補を作り、夜 LINE で知らせる
- 朝: システムが朝のレポートと朝 LINE を出し、ユーザーが注文内容を決める
- 寄り付き: ユーザーが証券画面で発注する
- 約定後: ユーザーが約定を入力し、システムが保有を評価して売却候補を出す

この運用サイクルを守ることで、Single Windows Node 上でも安全性と再現性を保った運用が可能になります。
