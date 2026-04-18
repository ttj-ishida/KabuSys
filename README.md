# KabuSys — 日本株自動売買システム（README）

本リポジトリは日本株の自動売買／リサーチ／監視を目的とした小規模なシステムです。  
この README ではプロジェクト概要、機能一覧、セットアップ手順、主な使い方、ディレクトリ構成を日本語でまとめます。

※ 本ドキュメントはソースコード（src/kabusys 以下）を参照して作成しています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- マーケットデータの分析（DuckDB を利用）
- ファクター計算 / 特徴量探索 / リサーチ機能
- ポートフォリオ構築（銘柄選定・配分・ポジションサイズ）
- ExecutionEngine（発注エンジン）および Paper Trading（ペーパートレード）サポート
- システム監視（リソース・プロセス・データ鮮度・取引ログの監視）
- AI（LLM）を使ったニュースセンチメント評価・レジーム判定
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定）

設計方針として、DuckDB や SQLite をストレージに用い、外部 API（kabuステーション / J-Quants / OpenAI）へ接続する機能を持ちます。Paper Trading は本番 DB と分離して運用可能です。

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話式作成）: `kabusys.config_setup`
- 設定検証 CLI（.env / config/*.yaml のチェック）: `kabusys.validate_config`
- Execution エンジン起動スクリプト: `kabusys.run_execution`
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading 用 SQLite に記録
- Monitoring（常駐監視）起動スクリプト: `kabusys.run_monitoring`
  - システムリソース・プロセス状態・データ鮮度・取引ログ・リスクを周期的にチェック
  - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き可能（デフォルト 60 秒）
- Kill Switch：閾値超過時に `data/kill.flag` を書いて ExecutionEngine を停止
- Paper Trading 検証レポート生成スクリプト: `kabusys.tools.paper_verification_report`
- AI 機能:
  - ニュース NLP による銘柄センチメント評価（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュース LLM）
- ポートフォリオ構築ユーティリティ（等配分・スコア加重・リスクベース等）
- ロギング設定ユーティリティ（console + 日次ローテートファイル）

---

## セットアップ手順（開発/実行前）

1. Python 環境を用意（推奨: 3.10+）
2. 必要なパッケージをインストール（例）:
   ```
   pip install duckdb psutil openai
   ```
   - オプション / 実行により PyYAML（設定 YAML 検証用）もあると便利:
     ```
     pip install pyyaml
     ```
3. プロジェクトルートに `.env` を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 必須の環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
     - KABU_API_PASSWORD（kabuステーション API）
   - AI 機能を使う場合:
     - OPENAI_API_KEY（OpenAI クライアント用。news/regime 機能で必要）
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - --strict を付けると警告も失敗扱いになります
5. データディレクトリなど（`data/`, `logs/`）は通常自動作成されますが、権限に注意してください。

環境変数の自動ロード:
- `.env` と `.env.local` はプロジェクトルートを基準に自動ロードされます（デフォルト）。
- テストなどで自動ロードを無効にする場合:
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL, LOG_DIR
- OPENAI_API_KEY（AI 機能）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔を秒で上書き）

---

## 使い方（主要コマンド）

- 設定ウィザード（.env の生成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、デフォルトで `data/paper_trading.db` に記録されます。
  - エンジンの停止は kill flag（data/kill.flag）により制御されます。監視側から自動書込される場合があります。

- Monitoring を起動（常駐）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で秒数を指定できます（例: 30）。
  - 監視は Settings.sqlite_path（デフォルト: data/monitoring.db）を用いて永続化します（監視側は環境に関わらず本番 sqlite_path を使用する設計）。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl-C。

- Paper Trading 検証レポート（CLI）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: `data/paper_trading.db`。`--db` でパスを指定可能。

- AI 機能の利用（プログラム呼び出し）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn は DuckDB 接続、target_date は date オブジェクト
    score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```

ログ:
- デフォルトでコンソール出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` により行われます。

停止・Kill フラグ:
- `kabusys.monitoring.kill_switch.KillSwitch` がリスク条件を満たすと `data/kill.flag` を書き、ExecutionEngine に停止を促します。
- 手動でエンジンを停止する場合は `data/stop_requested.flag`（監視/実行スクリプトが検知する）を作成または `execution.pid` を参照してプロセスを制御します。

---

## ディレクトリ構成（概要）

以下は src/kabusys の主要ファイル・ディレクトリ（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 永続化レイヤ（監視ログ）
    - system_monitor.py       — システム監視（CPU/MEM/DISK/データ鮮度）
    - trade_monitor.py        — 取引監視（滞留注文等）※詳細ファイルが存在
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - monitoring_engine.py    — 各 Monitor を束ねる
    - alert_manager.py        — アラート送信（LINE 等）※詳細ファイルが存在
  - execution/
    - execution_engine.py     — 実行エンジン本体（発注ロジック）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — Broker クライアント生成（Mock / Live）
    - risk_manager.py
    - reconciler.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py      — ファクター計算（Momentum/Value/Volatility）
    - feature_exploration.py  — IC 計算・統計サマリー
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ma200 + LLM）
  - tools/
    - paper_verification_report.py

---

## 注意事項 / 運用上のポイント

- 本番運用時は KABUSYS_ENV=live の設定に注意し、特に Kill Switch や LINE の通知設定を確認してください。
- OpenAI API を使用する機能は API キーが必要です（課金・レート制限に注意）。
- Paper Trading は本番 DB と分離しているため、ペーパートレード結果は `PAPER_TRADING_SQLITE_PATH` に記録されます。
- ログディレクトリ/データディレクトリの書き込み権限を実行環境で事前に確認してください。
- 実行スクリプトは `python -m kabusys.<module>` で起動できます。cron や systemd 等でサービス化することを想定しています。

---

必要であれば、セットアップ用の requirements.txt、systemd ユニット例、より詳細な運用手順（監視アラートの設定、バックアップ、DB マイグレーション手順など）も作成できます。どの情報を優先して補足しますか？