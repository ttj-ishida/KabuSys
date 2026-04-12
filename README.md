# KabuSys

日本株自動売買システムの軽量実装（ライブラリ / ツール群）。  
このリポジトリはトレード実行ロジック、監視・アラート、ポートフォリオ構築、研究用ファクター計算、LLM を使ったニュース NLP 等のコンポーネントを含みます。

以下はコードベースから抽出した README です。

## 概要

- Python 製の日本株自動売買システム（モジュール群）。
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）を別プロセスで動かす設計。
- Paper Trading モードを用意しており、本番 DB と分離された専用の SQLite を使える（data/paper_trading.db）。
- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等）を想定した研究／ファクター計算機能。
- OpenAI API を利用したニュースのセンチメント計算（ai.news_nlp）や市場レジーム判定（ai.regime_detector）。
- 監視ログ（システム状態・注文ログ・リスクログ等）は SQLite（MonitoringDB）に永続化。
- Streamlit によるシンプルな監視ダッシュボードを同梱。

## 主な機能一覧

- 実行（Execution）
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理（OrderManager / OrderRepository）
  - リコンシリエーション（Reconciler）で再起動時の状態同期
  - RiskManager によるリスクチェック（利用率、ドローダウンなど）
  - Paper Trading 用の MockBroker（KABUSYS_ENV=paper_trading 時）

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / PID 存在確認
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込んで ExecutionEngine を停止させる仕組み
  - AlertManager: LINE Push による通知（トークン未設定時はログにフォールバック）
  - MonitoringDB: 監視ログ用の SQLite スキーマ初期化と読み書き

- 研究・ポートフォリオ
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（スピアマン）や統計サマリ
  - portfolio: 候補選定、重み計算、ポジションサイズ算出、セクターキャップ、レジーム乗数

- AI（OpenAI）
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄別センチメントを ai_scores に書き込む
  - regime_detector: ma200 乖離とマクロニュースの LLM 評価を合成して市場レジームを判定

- ツール
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report
  - Streamlit ダッシュボード: monitoring/streamlit_dashboard.py

## セットアップ（ローカル開発向け）

前提: Python 3.10+ が推奨（typing の一部で型注釈を使用）。

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（requirements.txt が無ければ下記を参考に）
   - pip install duckdb psutil requests openai streamlit

   例:
   - pip install "duckdb" "psutil" "requests" "openai" "streamlit"

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を参照して自動ロードされます（既存の OS 環境変数は上書きされません）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数（必要に応じて設定）:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=<token>
     - KABU_API_PASSWORD=<password>
     - OPENAI_API_KEY=<key>
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LOG_LEVEL=INFO|DEBUG|...
     - MONITOR_POLL_INTERVAL=60
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

5. データディレクトリ作成
   - mkdir -p data

## 起動・使い方

※ すべての起動スクリプトはパッケージモジュールとして実行できます。

- 監視ループ（SystemMonitor 単体）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を "high" に設定し（可能な環境で）、監視用 SQLite（settings.sqlite_path）と DuckDB に接続してポーリングを行います。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視用 DB は本番 DB と想定）。

- 実行エンジン（ExecutionEngine）
  - Paper Trading モード時（KABUSYS_ENV=paper_trading）は MockBrokerClient を使用し、data/paper_trading.db に記録されます（本番 DB と分離）。
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を "high" に設定し、必要なコンポーネント（Broker, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を組み立ててセッションを実行します。

- Streamlit ダッシュボード（監視用）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、ダッシュボード（Overview / Positions / Orders / System）を表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書きできます。

- AI 機能（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を与えてニュースセンチメントを ai_scores に書き込む。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを算出して market_regime テーブルへ書き込む。

## 設定（Settings）

設定は環境変数から読み込まれます（kabusys.config.Settings）。自動的にプロジェクトルートの `.env` / `.env.local` を読み込む実装です。重要な設定項目:

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- OPENAI_API_KEY（ai モジュールで必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager）

必須の環境変数（実行コンポーネントにより要求）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
（これらは Settings のプロパティアクセス時に未設定なら例外を送出します）

.env の書式は shell ライク（export 対応、クォートやコメント処理あり）です。

自動読み込みを無効にする場合:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 監視 / 安全停止（Kill Switch）

- RiskMonitor がドローダウンやポジション上限を検知した場合、KillSwitch が data/kill.flag を書き込みます。
- ExecutionEngine は起動時に kill.flag の存在を確認し、必要に応じて起動時に削除する設定（Settings.kill_flag_clear_on_start）があります。
- kill.flag の書き込みは冪等：既に存在する場合は書き直しません。

## マイグレーション / DB 初期化

- monitoring_db.init_monitoring_db(conn) はスキーマを冪等に作成し、必要に応じて簡単な ALTER（カラム追加）を行います。
- run_monitoring / run_execution 起動時に自動で init_monitoring_db が呼ばれます。

## 依存関係（主な外部パッケージ）

- duckdb
- psutil
- requests
- openai
- streamlit

（実際の requirements.txt がある場合はそちらを参照してください。）

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ma200）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - （Broker API / Engine 等 他ソース）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

## 開発メモ / 注意事項

- ルックアヘッドバイアス対策: AI / リサーチ系の関数は内部で datetime.today()/date.today() を直接参照しない実装方針。
- DuckDB クエリは prices_daily / raw_financials 等のテーブルを前提とします。外部データは事前にロードしてください。
- Paper Trading は本番 DB と完全分離することを強く推奨します（デフォルトで別ファイル）。
- OpenAI API 呼び出しはリトライやバックオフを行う設計になっていますが、API キー・コスト管理に注意してください。
- AlertManager はトークン/ユーザーID 未設定時は送信せずログ出力します（安全設計）。
- プロセス優先度や CPU affinity の設定はプラットフォーム依存（psutil を利用）で、権限不足時は警告を吐いてスキップします。

---

この README はコードベース（src/kabusys 以下）から抽出した情報を元に作成しています。より具体的な運用手順（AM/PM 起動スクリプト、systemd ユニット、Docker 化、CI/CD、テスト方針等）は運用要件に応じて追加してください。必要であれば README にサンプル .env.example や systemd サービス例、docker-compose.yml などのテンプレートを追加します。