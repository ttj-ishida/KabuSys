# KabuSys

日本株自動売買システムのコアライブラリ群 — ポートフォリオ構築、発注実行、監視、リサーチ、AI/NLP を含むモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買を支援するためのモジュール群です。主要な責務は次のとおりです。

- ファクター計算・特徴量生成（research）
- ポートフォリオ構築・ポジションサイズ計算（portfolio）
- 発注ロジック・ExecutionEngine（execution）
- システム監視・リスク監視・Kill Switch（monitoring）
- ニュースの LLM によるセンチメント解析・レジーム判定（ai）
- 各種ユーティリティ（設定読み込み・ログ設定・プロセス優先度等）
- Paper Trading 用の検証レポート生成ツール（tools）

設計方針の一部：
- 本番 DB（SQLite / DuckDB）へのアクセスは明示的に管理
- Paper Trading は本番 DB と分離（デフォルト: `data/paper_trading.db`）
- LLM 呼び出しは OpenAI（gpt-4o-mini）を前提（APIキー必須）
- .env ファイルを使った環境変数管理をサポート（対話ウィザードあり）

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み / 対話式ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行 / 監視
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
    - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、paper DB に記録
  - SystemMonitor 起動スクリプト（`run_monitoring.py`）
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 停止フラグ / Kill Switch（`data/stop_requested.flag`, `data/kill.flag`）

- 監視 DB（SQLite）ヘルパー
  - `monitoring_db`：system_status / trade_logs / positions / risk_logs / dashboard を管理

- リスク監視・アラート
  - ドローダウン検出・ポジション上限検出、kill flag 書き込み

- ポートフォリオ構築
  - 候補抽出、等加重・スコア加重、セクターキャップ、レジーム乗数、株数決定、単元丸め

- リサーチ
  - モメンタム・ボラティリティ・バリューのファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメントスコア算出（`kabusys.ai.news_nlp`）
  - マクロニュース + ETF MA による市場レジーム判定（`kabusys.ai.regime_detector`）
  - 失敗時のリトライ・フォールバックロジックあり

- ツール
  - Paper Trading の検証レポート生成（`kabusys.tools.paper_verification_report`）

---

## 必要な依存パッケージ（代表例）

このリポジトリには requirements.txt は含まれていませんが、以下が主な依存です。

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（設定 YAML の詳細検証を行う場合）
- （開発）pytest 等

インストール例:
pip install duckdb psutil openai pyyaml

（プロジェクトで配布される requirements.txt があればそちらを使用してください）

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローン / コピー

2. 仮想環境作成・依存インストール
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml

3. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下にサンプルを記載）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

6. 必要に応じて DuckDB / SQLite DB の初期化は各起動スクリプトが行います（monitoring は init_monitoring_db でテーブル作成）。

---

## 環境変数（主なもの）

最小必須（validate_config でチェックされる）:
- JQUANTS_REFRESH_TOKEN（J-Quants API 用）
- KABU_API_PASSWORD（kabuステーション API）

運用に重要なもの:
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
  - paper_trading: Execution は MockBroker を用い、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） — デフォルト: INFO
- OPENAI_API_KEY: OpenAI を使用する機能（news_nlp, regime_detector）で必須
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）
- PID_FILE_PATH / KILL_FLAG_PATH: PID・kill flag のパス（Settings でアクセス可能）

簡易 .env サンプル:
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

※ .env は絶対にコミットしないでください（config_setup でも警告があります）。

---

## 使い方（主要なコマンド）

- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を "high" に設定し、SQLite/DuckDB に接続
    - KABUSYS_ENV が paper_trading の場合は paper DB を使用
    - data/stop_requested.flag が既に存在すると起動を中止
    - 起動中に data/stop_requested.flag が作成されるとエンジン停止処理を行う
    - PID ファイルを data/execution.pid（デフォルト）に書きます

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（秒）
    - 監視は monitoring DB（Settings.sqlite_path）に書き込みます（環境に依らず本番 sqlite_path を使う）
    - data/stop_requested.flag 検知でループを終了

- .env 対話ウィザード
  - python -m kabusys.config_setup
  - .env の生成・更新を支援

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告がある場合に exit(1)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易レポート（稼働率・注文成功率・レイテンシ等）を標準出力に出力

- AI 関連（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と date を渡して呼び出します（OpenAI API キーが必要）

---

## 停止 / Kill フロー

- 一時停止／停止リクエスト用フラグ
  - data/stop_requested.flag
    - run_monitoring / run_execution はこのファイルの存在を監視して終了/停止します
  - data/kill.flag
    - KillSwitch（監視モジュール）が条件に該当した場合に書き込まれ、ExecutionEngine 停止のシグナルとなります
    - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では推奨しません）

---

## ロギング

- ログは `kabusys.utils.logging_setup.setup_logging` を通じて設定されます
  - コンソール出力（stdout）
  - 日次ローテーションでファイル出力（デフォルト保存先: logs/<app_name>.log、30 日保持）
- 環境変数 LOG_DIR を用いてログディレクトリを変更可能

---

## ディレクトリ構成（抜粋）

プロジェクト内の主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在する想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する想定)
  - execution/
    - execution_engine.py (存在する想定)
    - broker_factory.py (存在する想定)
    - order_manager.py (存在する想定)
    - order_repository.py (存在する想定)
    - reconciler.py (存在する想定)
    - risk_manager.py (存在する想定)
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

（上記は主要モジュールを抜粋したものです。実際のパッケージにはさらにモジュール/サブパッケージがあります。）

---

## 注意点 & 運用上のヒント

- 本番運用時は KABUSYS_ENV=live を慎重に設定してください。validate_config は live のときに追加警告を出します（LINE 通知など）。
- Paper Trading は本番 DB と分離されます。必ず `PAPER_TRADING_SQLITE_PATH` を確認してください。
- OpenAI 関連の機能は API 利用料・レート制限の影響を受けます。APIキーと呼び出し頻度を管理してください。
- ログディレクトリ作成に失敗した場合、ファイルハンドラは無効化されコンソールのみの出力となります（警告が出ます）。
- process_priority.set_process_priority はプラットフォーム差分を吸収しますが、権限不足で失敗することがあります（警告ログのみ）。

---

## ベースとなる開発・拡張ポイント

- ExecutionEngine / BrokerClient 実装を差し替えれば別ブローカー対応が可能
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news など）にデータを投入することで、research/ai 機能が利用可能
- ポートフォリオ/リスク設定は config/*.yaml で管理する想定（config ディレクトリ参照）

---

必要に応じて README の補足（CI / デプロイ手順、systemd ユニット例、詳しい設定項目一覧など）を追加できます。どの部分を詳しくしたいか教えてください。