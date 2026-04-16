# KabuSys

KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・実行・監視・AI 補助）の一部実装です。本リポジトリは、ExecutionEngine（発注実行）・Monitoring（監視）・Research（因子計算）・Portfolio（銘柄選定・配分・株数算出）・AI（ニュースセンチメント / レジーム判定）などの機能群を含みます。

---

## 概要

- 実行（Execution）
  - ブローカー抽象化（実運用・ペーパートレードを分離）
  - OrderManager / ExecutionEngine / Reconciler による状態管理と起動時リコンシリエーション
- 監視（Monitoring）
  - システム稼働・データ鮮度・注文滞留・約定異常・ドローダウン監視
  - SQLite に永続化する監視テーブル群（monitoring.db）
  - LINE Push によるアラート送信、Streamlit ダッシュボード表示
  - KillSwitch によるフラグファイルでの ExecutionEngine 強制停止
- 研究（Research）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC 計算、統計サマリ
- ポートフォリオ構築（Portfolio）
  - 候補選定、等重／スコア加重、セクター制限、ポジションサイズ計算（単元丸め／資金制約考慮）
- AI（OpenAI）
  - ニュース記事のセンチメントを LLM でスコアリングして ai_scores に保存
  - ETF（1321）MA200 とマクロ記事センチメントの組合せで市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成スクリプト（period 指定可）

---

## 主な機能一覧

- Monitoring
  - system_status / trade_logs / positions / risk_logs / dashboard の永続化（SQLite）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス存在チェック、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限の監視と通知
  - KillSwitch: 条件に応じて data/kill.flag を書いて ExecutionEngine を停止
  - AlertManager: LINE push（クールダウン管理）
  - Streamlit ダッシュボード（監視情報の可視化）
- Execution
  - ExecutionEngine（起動・セッション実行）
  - BrokerClientFactory（本番 / ペーパートレードの分離）
  - OrderManager / OrderRepository による注文ライフサイクル管理
  - Reconciler による起動時リコンシリエーション
- Portfolio
  - 候補選定（スコア順）、等重 / スコア重み付け、セクター制限、リスクベースの枚数算出、lot_size（単元）対応
- Research
  - calc_momentum / calc_volatility / calc_value（DuckDB 参照）
  - calc_forward_returns / calc_ic / factor_summary
- AI
  - score_news: raw_news を LLM で銘柄別センチメント評価し ai_scores に書込
  - score_regime: ma200 と LLM マクロセンチメントを合成して market_regime に書込
- Tools
  - paper_verification_report: Paper Trading DB から検証レポート出力

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | Y` を使用）
- システムに sqlite3 が利用可能（標準ライブラリ）
- 必要な外部パッケージ（例）

推奨インストール例:
```bash
python -m pip install duckdb psutil requests streamlit openai
```

（実プロジェクトでは requirements.txt を用意して pip install -r で管理してください）

初期ディレクトリ作成:
```bash
mkdir -p data
```

.env の自動読み込み
- プロジェクトルートに `.env` / `.env.local` を置くと、自動で読み込まれます（OS 環境変数は上書きされません）。
- 自動ロードを無効化するには環境変数を設定します:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

重要な環境変数（Settings クラス由来）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (LINE 通知用、空なら送信スキップ)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db) — Monitoring は常に sqlite_path を使用（環境に依らず本番パス）
- PAPER_FILL_MODE (paper_trading の MockBroker の約定挙動; valid: instant|partial|never|reject; default: instant)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 SQLite、デフォルト: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか、"1" で有効)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY（AI 呼び出し用）

データベース初期化
- Monitoring 用テーブルは `init_monitoring_db()` により冪等で作成されます。run_monitoring / run_execution 起動時に自動で実行されます。

---

## 使い方（実行例）

環境変数の例（bash）
```bash
export KABUSYS_ENV=development
export OPENAI_API_KEY=sk-...
export KABU_API_PASSWORD=your_password
# 必要に応じて他の env を設定
```

1) 監視ループの起動
- デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます（秒）。
- 実行:
```bash
python -m kabusys.run_monitoring
```
- 停止: プロジェクトルートの data/stop_requested.flag を作成するとループが検出して終了します。

2) ExecutionEngine の起動
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）を使用します。
- 実行:
```bash
python -m kabusys.run_execution
```
- 実行中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を作成するか、KillSwitch（監視が書いた data/kill.flag）で制御されます。

3) Streamlit ダッシュボード（監視画面）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- read-only URI を使って SQLite を開きます。MonitoringEngine が先に監視データを書き込んでいる必要があります。

4) Paper Trading 検証レポート
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```
- デフォルト DB は `data/paper_trading.db`。--db で上書き可能。

5) AI モジュール（プログラムから呼び出す例）
```python
from datetime import date
import duckdb
from kabusys.ai import score_news
conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
print("scored codes:", count)
```

6) Research / Portfolio をスクリプトから利用
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value
conn = duckdb.connect("data/kabusys.duckdb")
res = calc_momentum(conn, date(2026,4,10))
```

---

## 停止 / フラグ制御

- data/stop_requested.flag
  - run_monitoring / run_execution のループがこれを検知して安全に終了します（手動停止用）。
- data/kill.flag
  - KillSwitch が条件達成時に書き込み、ExecutionEngine に停止シグナルを送ります（実際の ExecutionEngine は起動時に kill.flag をクリアする設定がある）。
- data/execution.pid
  - ExecutionEngine が PID を書き込みます。SystemMonitor はこの PID の存在を確認してプロセスの稼働監視を行います。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定読み込みロジック
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - broker_api.py
    - 等（注文実装関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py
  - data/ (runtime 用ディレクトリ、DB・フラグファイルなどを配置)

---

## 実装上の重要な注意点 / 動作原則

- Monitoring の sqlite_path は KABUSYS_ENV に関係なく本番の `SQLITE_PATH` を使用します（監視ログは常に集中管理を想定）。
- ExecutionEngine は KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB と MockBroker を利用して本番 DB と完全分離します。
- Process priority（優先度）は run_monitoring / run_execution 起動時に set_process_priority("high") を呼び出します。プラットフォームにより適用されない場合は警告でスキップします。
- .env のパースは独自実装で、コメント・クォート・エスケープに対応しています。システム環境変数は protected されます。
- AI 系（news_nlp / regime_detector）は OpenAI API を利用します。OPENAI_API_KEY を必ず設定してください。API エラー時はフォールバック（0.0 等）で処理継続する実装が多く、失敗で即例外とならない設計です。
- Streamlit ダッシュボードは SQLite を read-only モードで開くことを推奨します。

---

## よくある操作

- 監視のポーリング間隔変更:
  - MONITOR_POLL_INTERVAL=30 を設定すると 30 秒間隔になります（デフォルト 60 秒）。
- kill.flag を手動でクリア:
  - 実行前に kill.flag を手動で削除する場合は:
    ```bash
    rm -f data/kill.flag
    ```
  - Settings.kill_flag_clear_on_start を "1" にすると Execution 起動時に自動クリアします（挙動はコードで確認してください）。

---

この README はコードベースの主要な機能と利用方法をまとめたものです。追加の使い方（API 詳細・Broker 実装・OrderRepository スキーマ等）は各モジュールの docstring を参照してください。必要であれば、運用手順書（起動順・環境の切り替え手順・監視運用フロー）や requirements.txt のテンプレートも作成しますのでお知らせください。