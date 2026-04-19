# KabuSys

日本株自動売買システムの一部（ライブラリ・起動スクリプト・ユーティリティ群）です。  
このリポジトリには、実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買を支える汎用コンポーネント群です。本リポジトリは以下のような機能を提供します。

- ExecutionEngine 起動スクリプト（本番 / ペーパートレード選択）
- System / Trade / Risk を監視する Monitoring
- ポートフォリオ構築（候補選定・重み・サイズ決定・セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定、OpenAI 連携）
- 環境設定ウィザード（.env 生成）と設定検証ツール
- ペーパートレード検証レポート出力ツール

設計上の注意点：
- .env / 環境変数で柔軟に設定可能（自動ロード機能あり）
- ログはコンソール（stdout）と日次ローテーションファイルに出力
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を使用
- いくつかの処理（AI 等）は外部 API（OpenAI）を利用（APIキー必要）

---

## 主な機能一覧

- 実行（Execution）
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB に記録。
  - ブローカーのファクトリ、注文管理、リスク管理、照合処理を含む（engine 側の組立て）

- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine: System/Trade/Risk の定期チェック、Kill Switch 評価、アラート送信
  - MonitoringDB: SQLite を用いた永続化（system_status / trade_logs / positions / risk_logs / dashboard）

- ポートフォリオ構築
  - 候補選定（スコア順）、等比重・スコア重みの計算
  - リスク調整（セクター上限・レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap、可用現金でスケール調整）

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- AI
  - ニュース NLP（OpenAI による銘柄別センチメント評価、ai_scores へ保存）
  - レジーム判定（ETF MA とマクロニュースの LLM 評価を合成）

- ユーティリティ
  - config_setup.py: .env 対話式ウィザード（初期設定）
  - validate_config.py: .env と config/*.yaml の検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10+ を想定
- 必要ライブラリ（例: duckdb, psutil, openai, PyYAML 等）をインストール

1. リポジトリをクローン／展開し、依存をインストールします（プロジェクトに requirements.txt がある場合はそれを使用）。
   例:
   ```bash
   python -m pip install -r requirements.txt
   ```
   または最低限:
   ```bash
   python -m pip install duckdb psutil openai
   ```

2. .env を生成／編集します（対話式ウィザード推奨）:
   ```bash
   python -m kabusys.config_setup
   ```
   - 対話ウィザードは .env を作成・更新します。
   - 生成後、設定内容を検証します:
     ```bash
     python -m kabusys.validate_config
     # 警告も FAIL としたい場合:
     python -m kabusys.validate_config --strict
     ```

3. データディレクトリの確認:
   - デフォルトの DB/ファイルパスはリポジトリ直下の `data/`、ログは `logs/` に作成されます。必要に応じてディレクトリを作成してください（logging_setup は起動時に作成を試みます）。
   - 主要なデフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID ファイル / kill.flag: data/execution.pid, data/kill.flag

4. OpenAI を使う機能を利用する場合:
   - 環境変数 `OPENAI_API_KEY` を設定するか、該当関数に直接 api_key を渡します。

---

## 環境変数（主要）

- 必須（実行には設定必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行 / 動作に関する主要変数（例、デフォルト記載）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知用（任意）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

注意:
- monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（run_monitoring の仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動
  - 通常（env によって本番 or paper が切り替わる）
  ```bash
  python -m kabusys.run_execution
  ```
  - 説明:
    - 起動時にプロセス優先度を "high" に設定し、DB 接続・各コンポーネントを準備して ExecutionEngine を開始します。
    - 停止は data/stop_requested.flag によるフラグ検知または ExecutionEngine 内の停止処理経由で行われます。
    - paper_trading 時は MockBrokerClient を使用し paper_trading DB に記録します（本番 DB と完全分離）。

- 監視ループ起動
  ```bash
  # 環境変数で MONITOR_POLL_INTERVAL を上書き可
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 説明:
    - SystemMonitor のポーリングループを起動。既定は 60 秒。
    - 停止は data/stop_requested.flag の作成で検出して終了。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュールの利用例（ライブラリ関数）
  - ニュース NLP を実行して ai_scores に書き込む:
    ```py
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
    ```

---

## 重要な挙動と運用上の注意

- ログ:
  - 共通の logging 設定 (kabusys.utils.logging_setup.setup_logging) を使用。コンソール（stdout） + logs/<app>.log（日次ローテーション、30日保持）。
  - ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続。

- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼び出します。権限不足等で失敗した場合は警告のみ。

- Kill Switch:
  - リスク監視がトリガーした場合、KillSwitch が data/kill.flag を作成して ExecutionEngine に停止を促します。KILL_FLAG_CLEAR_ON_START による自動クリアは本番では危険（推奨は 0）。

- Paper Trading:
  - KABUSYS_ENV=paper_trading 時、実注文は行われず MockBroker を使用。DB は data/paper_trading.db を使うことで本番 DB と分離します。

- OpenAI:
  - AI 機能を使用するには OPENAI_API_KEY が必要。API 呼び出しはリトライやフォールバック（失敗時の安全挙動）を実装していますが、API 経験費用や利用制限に注意してください。
  - レスポンスのバリデーションを実装しているため、LLM の出力が不正な場合はスコア取得をスキップします。

---

## ディレクトリ構成（抜粋）

プロジェクトルートの src/kabusys 配下の主なファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py      — 共通ロギング設定
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ / 永続化層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （注文監視ロジック）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 制御
    - monitoring_engine.py  — 各 Monitor を束ねる
    - alert_manager.py      — （アラート送信管理）
  - execution/
    - execution_engine.py   — ExecutionEngine（発注セッション等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（OpenAI）
  - data/                   — 実行時に使用する DB / flag / pid etc.（デフォルトパス）
  - config/                 — YAML 設定ファイル群（system_config.yaml 等）

注: 上記は主なファイルの抜粋です。実際のファイル一覧はリポジトリを参照してください。

---

## 例: よく使うコマンドまとめ

- .env の対話式作成:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ起動（ポーリング間隔を 30 秒に設定）:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## 参考 / トラブルシューティング

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を読み込みます。OS 環境変数が優先されます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DB / ファイルパスの親ディレクトリが存在しない場合、起動時に自動作成されることがありますが、権限や環境により失敗することがあるため事前に作成しておくと確実です。

- OpenAI 呼び出しに関するエラーやレート制限はログに出力され、リトライ／フォールバックされます。APIキー・料金・制限に注意してください。

---

必要があればこの README を英語版に翻訳したり、各セクションをさらに詳述した運用手順（デプロイ、systemd ユニット例、Dockerfile、CI 設定など）を追加できます。どの部分を拡充しましょうか？