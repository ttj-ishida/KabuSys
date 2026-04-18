# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群。バックテスト・リサーチ、ポートフォリオ構築、Execution Engine（発注処理）、Monitoring（監視・アラート）、AIベースのニュース・レジーム判定などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- モジュール化された自動売買フレームワーク（Execution / Monitoring / Research / Portfolio / AI）。
- DuckDB を分析用データベース、SQLite を監視・発注ログ用に使用。
- 本番（live）／ペーパートレード（paper_trading）／開発（development）環境を切替可能。
- OpenAI を使ったニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）をサポート。
- kill.flag / stop_requested.flag による外部停止シグナル、PID ファイルやログローテーション機能を備える。

---

## 主な機能一覧

- 実行（Execution）
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - ブローカークライアント切り替え（実口座 / MockBroker）
  - リスク管理（RiskManager）・注文管理（OrderManager）・リコンシリエーション

- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期実行する監視エンジン
  - kill.flag による自動停止（KillSwitch）
  - 監視ログ永続化（SQLite via MonitoringDB）

- ポートフォリオ構築（Portfolio）
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイジング、セクター上限・レジーム乗数適用

- リサーチ（Research）
  - ファクター計算（Momentum / Value / Volatility）
  - 将来リターン、IC（Information Coefficient）、統計要約

- AI（OpenAI）
  - ニュースのセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定

- ツール
  - 設定ウィザード（kabusys.config_setup）で .env を対話的に生成
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- ユーティリティ
  - ロギング設定の統一（logs/<app>.log、日次ローテーション）
  - プロセス優先度／CPU affinity 設定ユーティリティ
  - 環境変数自動読み込み（.env / .env.local）

---

## 必要要件（例）

- Python 3.9+
- 主要依存パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- 推奨: 仮想環境（venv / poetry / pipenv）

インストール例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ 実際のプロジェクトでは requirements.txt や pyproject.toml に依存関係をまとめてください。

---

## セットアップ手順（クイックスタート）

1. リポジトリをクローンし、Python 仮想環境を作成して依存をインストールする。

2. .env の作成（対話式ウィザード）
   ```bash
   python -m kabusys.config_setup
   ```
   - ウィザードは J-Quants トークンや kabu API パスワードなどを対話的に入力して `.env` を生成します。
   - 出力先はデフォルトでプロジェクトルートの `.env`（変更可能）。

3. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

4. DB 初期化
   - 監視用 SQLite と DuckDB はスクリプト起動時に必要なテーブルを初期化します。
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時）

5. 環境変数（重要なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（ペーパートレード用、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（例: INFO）
   - LOG_DIR（デフォルト: logs/）
   - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
   - KILL_FLAG_CLEAR_ON_START（本番で kill.flag を自動クリアするか: 0/1、推奨 0）

   .env の自動ロード:
   - 起動時、プロジェクトルートが検出できれば `.env` と `.env.local` が自動で読み込まれます。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要コマンド）

- 実行エンジン起動（ExecutionEngine）
  ```bash
  # 通常起動
  python -m kabusys.run_execution

  # KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

  - 起動時に data/execution.pid が作成されます。
  - data/stop_requested.flag を作成するとループは検知して安全に終了します。
  - Kill Switch（data/kill.flag）が書き込まれると ExecutionEngine を停止します（本番保護機能）。

- 監視ループ起動（Monitoring）
  ```bash
  # 監視ループを起動
  python -m kabusys.run_monitoring

  # ポーリング間隔を環境変数で上書き（秒）
  MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  ```

  - 監視は Settings に従い常に本番 sqlite_path（SQLITE_PATH）を使用します（監視データは本番 DB に保存）。
  - stop_requested.flag を検知してループを終了します。

- Paper Trading 検証レポート
  ```bash
  # デフォルト DB（環境変数で上書き可能）
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB ファイルを直接指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- 設定ウィザード / 検証
  ```bash
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

---

## 実運用に関する注意点 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は推奨されません。誤設定で重要な停止保護を無効化するリスクがあります。
- ログは logs/<app>.log に日次ローテーションで出力されます。LOG_DIR で変更可能です。
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。OPENAI_API_KEY を必ず設定してください。API 呼び出しはリトライ・フォールバック実装済みですが、API 費用やレートに注意してください。
- Paper Trading モードは本番 DB と分離しており、PAPER_TRADING_SQLITE_PATH を使用します。ペーパートレードデータが誤って本番 DB を汚さないよう注意してください。
- データ鮮度チェック、稼働率監視、リスクアラート（ドローダウン、ポジション上限など）は monitoring サービスで実施されます。監視を常時稼働させることを推奨します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数／設定管理（Settings）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (実装ファイルがある前提)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (実装ファイルがある前提)
  - execution/
    - execution_engine.py (実装ファイルがある前提)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は本リポジトリに含まれる主要ファイルの抜粋です。実装ファイルはさらにあります。）

---

## 開発者向けメモ

- Settings クラス（kabusys.config）を通じて環境変数を参照してください。自動的にプロジェクトルートの `.env` / `.env.local` がロードされます（無効化可）。
- ログ設定は必ず起動時に setup_logging(app_name=...) を呼んで統一してください。
- Monitoring の DB 初期化（init_monitoring_db）は複数回呼んでも安全（冪等）。マイグレーション処理（カラム追加）も含まれます。
- AI モジュール内の OpenAI 呼び出しは個別のラッパー関数に分離しているため、テスト時はモックしやすく設計されています（_call_openai_api を patch など）。

---

## ライセンス / 貢献

- この README は内部開発向けの簡易ドキュメントです。正式なライセンス・コントリビュート手順はリポジトリのルートにある別ファイル（LICENSE / CONTRIBUTING 等）を参照してください。

---

問題や追加ドキュメント（API リファレンス・設計書の節など）が必要であれば教えてください。README を用途（運用マニュアル / 開発者ガイド / デプロイ手順）別に分割して拡張できます。