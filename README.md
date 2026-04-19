# KabuSys

日本株向け自動売買システムのリポジトリ（コードベースの抜粋に基づく README）。  
この README はプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤を想定した Python 製のモジュール群です。  
主な機能は以下の通りです：

- 発注エンジン（ExecutionEngine）と発注ロジック（OrderManager / RiskManager 等）
- システム監視（SystemMonitor / MonitoringEngine）と監視ログの永続化（SQLite）
- ペーパートレード環境の分離（paper_trading 用 DB とモックブローカー）
- ポートフォリオ構築（銘柄選定・重み計算・ポジションサイジング）
- ファクター・リサーチ（DuckDB を用いたファクター計算・特徴量解析）
- ニュースの NLP（OpenAI を用いたセンチメントスコア付与）
- 各種 CLI ツール（.env ウィザード、設定検証、検証レポート等）
- ロギング／プロセス優先度管理等のユーティリティ

設計の特徴として、実行環境（KABUSYS_ENV）による振る舞いの分離、DuckDB/SQLite を用いたデータ参照・永続化、外部 API（kabuステーション・J-Quants・OpenAI 等）の抽象化があります。

---

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading 時は MockBrokerClient を使用し本番 DB と分離
  - RiskManager による注文制御（最大ポジション比率や利用率制限等）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス存在、データ鮮度を監視
  - RiskMonitor: ドローダウン／ポジション上限監視、kill.flag の生成
  - Monitoring DB（SQLite）へのログ永続化（system_status, trade_logs, risk_logs, positions, dashboard）
  - MonitoringEngine: 各モニタを束ねて定期実行／アラート発行
- Portfolio
  - 候補選定(select_candidates)、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単位株丸め、aggregate cap）
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - DuckDB 接続を受け取り SQL + Python で計算
- AI
  - news_nlp: raw_news を LLM (gpt-4o-mini) でスコアリングし ai_scores に書き込み
  - regime_detector: ETF ma200 とマクロニュースから市場レジーム判定
- Tools
  - 環境設定ウィザード(.env 作成) — config_setup.py
  - 設定検証 CLI — validate_config.py
  - Paper Trading 検証レポート生成 — tools/paper_verification_report.py
- Utils
  - ロギング設定（setup_logging）
  - プロセス優先度 / CPU affinity 設定（set_process_priority / set_cpu_affinity）
  - 環境変数の自動読み込み（.env / .env.local）

---

## 要件（例）

- Python 3.10+（型ヒントに基づく）
- パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai（OpenAI SDK）
  - sqlite3 は標準ライブラリ
  - （開発用）PyYAML（config の検証で有用）
- その他：kabuステーションの API が必要な場合はその起動／接続情報

（実際の requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone … && cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は上の要件パッケージを個別にインストール

4. 環境変数の初期設定（.env）
   - 対話式で .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下の最低必須例参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告も FAIL 扱いにする

6. データベースファイルの場所
   - デフォルト:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 必要に応じて .env 中の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

---

## 最低必須 .env（例）

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

例（.env）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

※ .env はセキュリティ上、Git に含めないでください。

---

## 実行方法（よく使うコマンド）

- 環境ウィザード（.env を作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 備考:
    - 環境変数 KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient が使用され、data/paper_trading.db を使用して本番 DB と分離します。
    - 実行中は data/execution.pid（デフォルト）を利用します。
    - 停止シグナルは data/stop_requested.flag による検出です。

- System Monitor 起動（軽量な監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / Research 関数をライブラリとして使う（例）
  - DuckDB 接続を作成しモジュール関数を呼ぶ:
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 1), api_key="sk-...")

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- OPENAI_API_KEY（news_nlp / regime_detector の LLM 呼び出しに必要）
- LOG_LEVEL（例: INFO）
- LOG_DIR（ログ保存ディレクトリ、デフォルト logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔）
- KILL_FLAG_CLEAR_ON_START（本番起動時の Kill Flag 自動クリア制御）

---

## 停止・Kill スイッチについて

- ExecutionEngine の停止はフラグファイルで制御します:
  - data/kill.flag — KillSwitch によって書き込まれると ExecutionEngine 側で検知して停止します
  - data/stop_requested.flag — 外部から監視 / 実行ループを終了させたいときに使われるフラグ（run_execution / run_monitoring が検出）
- .env の KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動でクリアします（本番では 0 を推奨）

---

## ロギング

- ログはデフォルトで stdout とファイル（logs/<app_name>.log）に出力します。
- ログ設定は kabusys.utils.logging_setup.setup_logging により統一管理されます。
- ログレベルは LOG_LEVEL 環境変数で設定可能（または setup_logging の引数で上書き）。

---

## 注意点・運用上のヒント

- run_execution.py / run_monitoring.py は起動時にプロセス優先度を上げようとしますが、権限不足で失敗する場合があります（psutil.AccessDenied ログ）。
- DuckDB / SQLite のパスは環境変数で制御可能。監視 DB と paper_trading DB は分離する設計です。
- AI モジュール（news_nlp / regime_detector）は OpenAI の API 呼び出しを行います。APIキーが必要で、失敗時はフェイルセーフ（スコアを 0 にする等）で継続するよう設計されています。
- データ鮮度や Execution プロセスの停止などは MonitoringEngine で検知され、必要に応じて kill.flag の作成やアラート発行が行われます。
- config/*.yaml（例: system_config.yaml 等）が利用される想定箇所があります。validate_config で存在確認やパース検証が可能です（PyYAML が必要）。

---

## 主要なディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                       — 環境変数読み込み / Settings
- config_setup.py                 — .env ウィザード CLI
- validate_config.py              — 設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor 起動スクリプト
- tools/
  - paper_verification_report.py   — ペーパートレード検証レポート CLI
- ai/
  - news_nlp.py                    — ニュース NLP + OpenAI 呼び出し
  - regime_detector.py             — 市場レジーム判定
- monitoring/
  - monitoring_db.py               — SQLite DB 初期化 & DB 操作ラッパ
  - system_monitor.py              — システム状態監視
  - trade_monitor.py               — （発注ログ監視、抜粋内で参照あり）
  - risk_monitor.py                — ドローダウン・ポジション上限監視
  - kill_switch.py                 — kill.flag 制御
  - monitoring_engine.py           — 各 Monitor を束ねるエンジン
  - alert_manager.py               — （アラート送信機構、抜粋内で参照あり）
- execution/                       — Execution 関連（Engine, broker_factory, order_manager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py

プロジェクトルート:
- .env (生成)
- config/ (yaml 設定ファイル)
- data/ (DB, PID, フラグファイル)
- logs/ (ログファイル)
- pyproject.toml / requirements.txt（存在する場合）

---

## 開発者向け補足

- モジュールは「外部副作用を避ける設計（例: 日付参照の抑制）」がされている箇所があり、テストしやすい実装になっています（例: target_date を引数で受け取る）。
- DuckDB を利用する研究系関数は SQL と Python を組み合わせた実装で、prices_daily / raw_financials 等のテーブルが前提です。
- AI 呼び出し部分はリトライやレスポンス検証に注意深い実装になっています（JSON モードの扱い、429/5xx のバックオフ等）。

---

README はここまでです。実際の運用時は本リポジトリ内の `config/*.yaml`、`requirements.txt`、および各モジュールのドキュメント（存在する場合）を参照し、必要な外部サービス（kabuステーション、J-Quants、OpenAI）や権限（プロセス優先度変更権限など）を事前に整えてください。必要であれば README を拡張して具体的なデプロイ手順や systemd/サービスユニットの例も追加できます。