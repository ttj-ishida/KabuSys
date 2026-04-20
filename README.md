# KabuSys

日本株自動売買システムのコードベース。売買実行、監視、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）などのユーティリティ群を含みます。

---

## 概要

KabuSys は以下を目的とするモジュール群で構成された自動売買システムの基盤です。

- 発注エンジン（ExecutionEngine）
- システム・トレード監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算
- ファクター計算・リサーチ機能（DuckDB を用いる）
- ニュースの NLP スコアリング（OpenAI）
- ペーパートレード用分離 DB と検証レポート生成ツール

本リポジトリは実稼働（live）・ペーパートレード（paper_trading）・開発（development）を環境切替でサポートします。

---

## 主な機能

- Execution
  - 実売買（kabuステーション API）またはペーパートレード（MockBroker）を環境により切替
  - 注文管理、リスク管理（最大ポジション比率・利用率等）、約定の再調整（reconciler）
- Monitoring
  - CPU / メモリ / ディスク / プロセス状態の定期監視（SQLite に永続化）
  - 注文ログ、リスクログ、ダッシュボードの永続化
  - Kill Switch：ドローダウンや上限超過時にフラグファイルを書き ExecutionEngine を停止
  - アラート送信フック（LINE などを想定）
- Portfolio（純関数群）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター上限やレジーム乗数
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上で SQL と Python で実装）
  - Forward returns、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュース集約 → LLM によるセンチメントスコア化（ai_scores テーブルへ永続化）
  - マクロセンチメントと MA200 乖離を合成した市場レジーム判定（market_regime テーブル）
- Tools
  - Paper Trading 検証レポート生成ツール（成功率・レイテンシ・稼働率チェック）
  - .env 対話式ウィザード（config_setup） & 設定検証 CLI（validate_config）

---

## 前提条件

- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite（組み込み）
- kabuステーション API（本番実行時）への接続情報

必要パッケージはプロジェクト配布に requirements.txt があればそちらを使用してください。ない場合は手動インストール例:

pip install duckdb psutil openai pyyaml

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）
   python -m kabusys.config_setup

   ウィザードは J-Quants トークンや kabu API のパスワードなど必須項目の入力をサポートします。
   生成された .env は決して Git にコミットしないでください。

5. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告も失敗（exit 1）になります。

6. data/ および logs/ ディレクトリの作成
   多くのスクリプトが data/ や logs/ にパスを期待します。通常は自動作成されますがパーミッションに注意してください。

---

## 環境変数（代表的なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（デフォルト有り / 推奨設定あり）:
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- SQLITE_PATH — monitoring DB パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の DB（paper_trading 用）
- LOG_LEVEL — ログレベル（INFO 等）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を使う場合必須

運用に関するフラグ:
- KILL_FLAG_CLEAR_ON_START — (0/1) 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

（詳しいキーは src/kabusys/config.py を参照してください）

---

## 実行方法（主なコマンド）

すべてモジュールとして実行できます（プロジェクトルートから）。

- 監視ループを起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒単位、1秒以上）。
  - 終了方法: data/stop_requested.flag ファイルを作成するか Ctrl+C。

- ExecutionEngine（発注エンジン）を起動
  python -m kabusys.run_execution

  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード専用 DB（data/paper_trading.db など）へ記録します。
  - 実行中に data/stop_requested.flag を作成すると安全に停止を試みます。
  - 実行時に data/execution.pid が作成されます（設定でパス変更可）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション: --db PATH でペーパートレード DB を指定可能。

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

---

## ログ / データ / フラグファイル

- ログ:
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されます。
  - LOG_DIR 環境変数でログディレクトリを変更可能。

- データベース:
  - DuckDB: DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLite（監視）: SQLITE_PATH（例: data/monitoring.db）
  - SQLite（paper_trading）: PAPER_TRADING_SQLITE_PATH（例: data/paper_trading.db）

- フラグファイル:
  - 停止要求: data/stop_requested.flag — このファイルが存在するとループ系は停止します。
  - Kill Switch: data/kill.flag — KillSwitch が書き込むと ExecutionEngine 停止の合図となります（設定により自動クリアの有無あり）。
  - PID ファイル: data/execution.pid（ExecutionEngine が保持）

---

## 使い方のヒント / 運用上の注意

- KABUSYS_ENV を `live` に設定する前に validate_config で全設定を入念にチェックしてください。`live` ではアラート設定（LINE）の有無等も警告対象になります。
- openai を使う機能（news_nlp、regime_detector）は OPENAI_API_KEY が必要です。API 呼び出しの失敗は安全にゼロやデフォルト値にフォールバックする設計ですが、料金やレート制限に注意してください。
- ペーパートレード時は本番 DB と完全に分離されます（paper_trading 用 SQLite を使用）。
- ログディレクトリや data ディレクトリへの書き込み権限がないとファイル出力ハンドラが無効化され、コンソール出力のみで動作します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）を本番で有効にするのは危険です（誤って Kill Switch を無効化する可能性があります）。デフォルトは 0（クリアしない）を推奨。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主要なモジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数・設定管理（.env 自動読み込み含む）
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（本番 / ペーパー切替）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログの統一設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/  (発注周りの実装群)
    - (BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler, など)
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック（省略ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — フラグファイルによる強制停止ロジック
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py — アラート送信の管理（LINE 等の実装は別）
  - portfolio/
    - portfolio_builder.py — 候補選定・スコア順ソート
    - position_sizing.py — 発注株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value の計算（DuckDB）
    - feature_exploration.py — Forward returns / IC / 統計サマリ
  - ai/
    - news_nlp.py — raw_news を集約して OpenAI でスコア化、ai_scores へ書き込み
    - regime_detector.py — MA200 乖離 + マクロセンチメントによるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 追加情報 / 開発メモ

- DuckDB を利用して大規模な時系列データやファクター計算を効率的に行います。prices_daily / raw_financials などのテーブルを前提としています。
- AI 関連モジュールは API のエラーやパース失敗を安全に扱うよう設計されています（リトライ・部分失敗時の保護）。
- 多くの箇所で「フェイルセーフ（例: API失敗時にスコアを 0 にする）」や「冪等性（DB 書き込みやフラグ操作）」を考慮しています。

---

必要であれば、README をプロジェクトの配布形式（PyPI / Docker / systemd unit など）に合わせて起動・運用手順を追加します。どの形式での利用方法を優先して記載すればよいか教えてください。