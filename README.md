# KabuSys

日本株自動売買システムのサブコンポーネント群（モニタリング / 実行エンジン / ポートフォリオ構築 / リサーチ / AI ニュース NLP 等）の実装。  
このリポジトリはモジュール単位で再利用可能な純粋関数群や I/O 層（SQLite / DuckDB / 外部 API 呼び出しラッパー）を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買運用を支援するライブラリ兼ランタイムです。主な目的は以下です。

- ExecutionEngine：ブローカーへの発注・注文状態管理・リスク管理・再起動時のリコンシリエーション
- Monitoring：システム健全性（CPU/メモリ/ディスク）、プロセス生存、注文滞留、約定異常、ドローダウンなどの監視と通知
- Portfolio construction：シグナルから候補選定、重み付け、ポジションサイズ算出
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI 支援：OpenAI を用いたニュースセンチメント解析（ai.news_nlp）・市場レジーム判定（ai.regime_detector）
- ユーティリティ：Streamlit ダッシュボード、Paper Trading 検証レポート生成ツール 等

---

## 主な機能一覧

- SystemMonitor：CPU/メモリ/ディスク・プロセスの死活・データ鮮度の監視（SQLite に記録）
- TradeMonitor：滞留注文検出・約定価格の異常検出・リスクログ記録
- RiskMonitor：ドローダウン監視・ポジション上限監視・ダッシュボード更新
- KillSwitch：リスク条件に応じてフラグファイル（data/kill.flag）を書き込み ExecutionEngine を停止
- AlertManager：LINE Messaging API への一方向通知（クールダウン付き）
- MonitoringEngine：各モニタを束ねて定期的に実行しアラート/KillSwitch を評価
- Execution エンジン関連：OrderManager、Reconciler、OrderRepository 等による注文フロー管理
- Portfolio モジュール：候補選定・等重/スコア重み・リスク調整・株数計算（lot 単位丸め、aggregate cap）
- Research：momentum/value/volatility ファクター計算、将来リターン、IC 計算、統計サマリ
- AI：OpenAI を使ったニュースセンチメント（銘柄別）と市場レジーム判定
- Tools：Paper Trading 検証レポート（paper_verification_report.py）、Streamlit ダッシュボード

---

## セットアップ手順

1. Python（推奨: 3.9+）を用意します。

2. 依存パッケージをインストールします（例）:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   実際にはプロジェクトで使うモジュールに応じて追加してください。

   主要なパッケージ
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

3. 環境変数の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（.env に記載例）
   ```
   KABUSYS_ENV=development            # development | paper_trading | live
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=xxxx
   LINE_USER_ID=Uxxxxxxxxxxxx
   PAPER_FILL_MODE=instant           # instant | partial | never | reject
   ```

4. データディレクトリを作成:
   ```
   mkdir -p data
   ```

5. 注意点
   - Monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を使用します（環境に依存しない）。
   - Execution は `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を用いて paper_sqlite_path（デフォルト: data/paper_trading.db）へ記録します（本番 DB と分離）。
   - OpenAI を使う機能（ニュース NLP / レジーム判定）は `OPENAI_API_KEY` が必要です。

---

## 使い方

以下は主な実行例です。プロジェクトのルートで実行してください。

- モニタリングループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 停止はプロセスの KeyboardInterrupt またはプロジェクトルートの `data/stop_requested.flag` を作成して行います。

- Execution エンジンを起動
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合は paper trading 専用 DB を使い、MockBrokerClient が用いられます。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行いません。
  - エンジンの PID はデフォルト `data/execution.pid` に記録されます。

- Paper Trading 検証レポートを生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
  ```
  - `--db` を省略すると環境変数 `PAPER_TRADING_SQLITE_PATH` またはデフォルト `data/paper_trading.db` を使います。

- Streamlit ダッシュボードを起動（監視 DB を読み取り専用で開く）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI 関連（Python API 経由）
  - ニューススコアを計算して書き込む:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定を書き込む:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## 主要環境変数（Summary）

- KABUSYS_ENV: development | paper_trading | live（既定: development）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定: 60）
- SQLITE_PATH: 監視ログ用 SQLite（既定: data/monitoring.db）
- DUCKDB_PATH: 時系列データ用 DuckDB（既定: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（既定: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行制御用ファイルパス
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 認証
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

.env 自動読み込みについて:
- プロジェクトルートの `.env`、その後 `.env.local`（上書き）を自動読み込みします（OS 環境変数が protected）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                            — 環境変数読み込みと Settings クラス
- run_monitoring.py                    — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py                     — ExecutionEngine 起動スクリプト

ai/
- news_nlp.py                          — ニュース NLP（OpenAI）による銘柄別センチメント
- regime_detector.py                   — 市場レジーム判定（ETF + マクロ NLP）

monitoring/
- monitoring_db.py                     — SQLite テーブル作成・監視ログ I/O
- system_monitor.py                    — CPU/メモリ/ディスク・プロセス・データ鮮度監視
- trade_monitor.py                     — 注文滞留・約定異常検出
- risk_monitor.py                      — ドローダウン・ポジション上限監視
- kill_switch.py                       — kill.flag 書き込みユーティリティ
- alert_manager.py                     — LINE 通知
- monitoring_engine.py                 — 各モニタを束ねる実行エンジン
- streamlit_dashboard.py               — Streamlit ダッシュボード

execution/
- order_manager.py
- reconciler.py
- order_repository.py
- order_record.py
- execution_engine.py
- broker_factory.py
- (その他: broker API プロトコル / MockBrokerClient 実装 等)

portfolio/
- portfolio_builder.py                 — 候補選定・重み計算
- position_sizing.py                   — 株数算出・資金配分・単元丸め
- risk_adjustment.py                   — セクターキャップ・レジーム乗数

research/
- factor_research.py                   — ファクター計算（momentum/value/volatility）
- feature_exploration.py               — 将来リターン・IC・統計サマリ

tools/
- paper_verification_report.py         — Paper Trading 検証レポート生成スクリプト

utils/
- process_priority.py                  — プロセス優先度 / CPU affinity 設定ユーティリティ

data/
- (ランタイムで生成されるファイル)
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite)
  - kabusys.duckdb (DuckDB)
  - stop_requested.flag
  - kill.flag
  - execution.pid

---

## 運用上の注意 / 補足

- モニタリングは monitoring DB に常に本番 sqlite_path を用いて記録します。テスト目的で .env に別パスを設定する場合は注意してください。
- Execution 起動時に `KABUSYS_ENV=paper_trading` を設定すると本番 DB と完全に分離された paper_trading DB を使います（安全）。
- OpenAI API を使う箇所は外部ネットワークに依存するため、API 失敗時はフェイルセーフ（0.0 フォールバック、部分失敗時に既存スコアは保護）を意図しています。ただし API キーの漏洩・課金には注意してください。
- process_priority.set_process_priority() はプラットフォーム差（Windows / POSIX）を吸収しますが、権限不足で設定できない場合は警告となりスキップされます。
- KillSwitch は `data/kill.flag` に理由文字列を書き込むことで ExecutionEngine に停止を促します（Execution 側はフラグを監視して停止する設計）。

---

必要であれば、README に含めるサンプル .env、起動スクリプトの systemd ユニット例、テストの実行方法、あるいはより詳細な API ドキュメント（各モジュールの public API）も追加できます。どの情報を優先して追加しましょうか？