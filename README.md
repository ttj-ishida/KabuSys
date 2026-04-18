# KabuSys

日本株向け自動売買システム（ライブラリ＆起動スクリプト群）

このリポジトリは、シグナル生成〜ポートフォリオ構築〜発注（ExecutionEngine）〜監視（Monitoring）〜研究用ユーティリティ／AI連携までを含む総合的な自動売買システムの一部です。モジュール設計は単体テストやローカル開発、ペーパートレード、本番運用を想定しており、SQLite / DuckDB をデータ永続化に使用します。

---

## 概要

主なコンポーネント

- ExecutionEngine（発注エンジン）
  - 実際のブローカーとやりとりするブローカークライアントを注入して動作
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、本番 DB と分離された `data/paper_trading.db` に記録
- Monitoring（監視サブシステム）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - KillSwitch によるフラグファイル方式で ExecutionEngine を停止可能
- Portfolio（銘柄選定・配分・サイズ決定）
  - 等配分・スコア配分・リスクベースの単元株数計算等の純粋関数群
- Research（ファクター計算・特徴量探索）
  - DuckDB を用いたファクター計算、IC 算出など
- AI（ニュース NLP / レジーム検出）
  - OpenAI を用いたニュースセンチメント、マクロセンチメントに基づくレジーム判定
- ユーティリティ群
  - 設定読み込み、対話式 .env 生成ウィザード、設定検証 CLI、ログ設定、プロセス優先度設定 等
- ツール
  - ペーパートレード検証レポート生成スクリプトなど

---

## 機能一覧

- 実行環境分離
  - development / paper_trading / live をサポート（`KABUSYS_ENV`）
  - paper_trading は本番 DB と完全分離（専用 SQLite）
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - リスク監視（ドローダウン・ポジション上限）とダッシュボード永続化
  - Kill Switch（`data/kill.flag`）で ExecutionEngine を安全に停止
- 発注エンジン（ExecutionEngine）
  - ブローカー抽象化（実口座 / Mock 切替）
  - リスク管理（rate limit、最大建玉比率、CB 等）
- ポートフォリオ構築
  - 候補選定、重み計算（等比・スコア比）、ポジションサイズ計算（単元丸め・aggregate cap）
  - セクター制限・レジーム乗数の適用
- 研究・分析
  - DuckDB を使ったファクター計算（momentum/value/volatility など）
  - forward returns、IC、統計サマリ等
- AI 連携
  - OpenAI（gpt-4o-mini 等）でニュースセンチメントやレジーム評価
  - バッチ・リトライ・レスポンス検証を実装
- 開発支援ツール
  - 対話式 .env 作成（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - ペーパートレード検証レポート（`tools.paper_verification_report`）
- ロギング
  - コンソール（stdout） + 日次ローテーションファイル（`logs/<app>.log`）を統一的に設定

---

## 必要条件（推奨）

- Python 3.10+（typing に Union 型の代替などを利用）
- 必要パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
  - PyYAML（設定検証で YAML 内容を検証したい場合）
- SQLite3（Python 標準ライブラリで利用可）

依存関係はプロジェクトの requirements.txt を用意している場合はそちらを使用してください（本リポジトリのコードから推測した主要パッケージは上記）。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install PyYAML
   - 必要に応じて他パッケージを追加
4. 初期設定（.env）
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成
5. 設定検証（必須）
   - python -m kabusys.validate_config
   - 問題がある場合は指示に従って .env や config/*.yaml を修正
6. 必要ディレクトリの作成（通常は起動時に自動作成されますが手動でも可）
   - data/（DB・フラグファイル）
   - logs/（ログ出力）
7. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数 OPENAI_API_KEY を設定

注意: Monitoring 起動時に監視用 SQLite DB の初期化（テーブル作成）は自動で行われます。

---

## 主な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API パスワード）
- KABUSYS_ENV — 実行環境（default: development）
  - 有効値: development, paper_trading, live
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite（monitoring）ファイルパス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL — ログレベル（default: INFO）
- LOG_DIR — ログディレクトリ（default: logs）
- PID_FILE_PATH — ExecutionEngine の pid ファイル（default: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグパス（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（"1" で有効、default: "0"）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE — paper_trading の MockBroker の約定挙動（default: "instant"）
  - 有効値: "instant" | "partial" | "never" | "reject"
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（任意）

（詳細は `src/kabusys/config.py` と `src/kabusys/config_setup.py` を参照してください）

---

## 使い方（起動・主要コマンド）

- 環境構築（推奨）
  1. python -m kabusys.config_setup
  2. python -m kabusys.validate_config

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して `PAPER_TRADING_SQLITE_PATH` に記録
    - 起動前に `data/stop_requested.flag` が存在すると起動しません
    - 実行中に `data/stop_requested.flag` を作るとエンジンに停止シグナルを送ります

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 動作:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
    - Monitoring は環境にかかわらず本番の `SQLITE_PATH` を使用して監視テーブルを維持します
    - 監視は SystemMonitor・TradeMonitor・RiskMonitor を実行し、KillSwitch 評価やアラート送信を行います

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict（警告を FAIL 扱いにして exit(1)）

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- ログ
  - デフォルト: logs/<app_name>.log（`kabusys.utils.logging_setup.setup_logging` により設定）
  - stdout にも出力（cron 等で stdout をファイルにリダイレクトする運用に配慮）

---

## 停止・Kill Switch の運用

- 停止リクエスト（プロセス外からの即時停止）
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して停止します
- Kill Switch（リスクトリガーによる Engine 停止）
  - 条件（例）: ドローダウン超過 / ポジション数上限超過
  - 発動時、`data/kill.flag` が書き込まれ、ExecutionEngine 起動時に検出されると起動を中止、実行中は停止を要求します
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で `kill.flag` を削除します（本番では推奨しません）

---

## ディレクトリ構成（主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env 読み込み・Settings 定義
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/ — 発注関連（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 発注ログ・滞留注文監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグ書き込みによる停止シグナル
    - alert_manager.py — アラート配信（LINE など、実装に依存）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — momentum / value / volatility 計算
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/ (実行時に使用されるディレクトリ)
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用、env により変動）
    - kill.flag / stop_requested.flag / execution.pid など

---

## 開発・運用上の注意点

- 本番運用時（KABUSYS_ENV=live）の設定は厳重に確認してください（LINE 通知等の設定も必要）
- Kill Switch や kill.flag の誤クリアは致命的な運用ミスにつながるため、`KILL_FLAG_CLEAR_ON_START=1` の設定は本番では避けることを推奨します
- Monitoring は `SQLITE_PATH` を使用してログを記録します。Monitoring はどの環境でも同一の監視 DB を使う設計です（設計上の意図）
- AI 機能を利用する際は OpenAI の利用制限やコスト、レスポンスの妥当性を考慮してください。レスポンスは厳密な JSON で返すようプロンプトで制約していますが、パース失敗や例外処理は実装されています
- DuckDB のバージョン依存（executemany の挙動など）に注意。コード中に互換性対応のコメントがあります

---

## よく使うコマンド一覧

- .env 作成ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper trading レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Python REPL からモジュールを呼び出す（例: portfolio 機能）
  - python -c "from kabusys.portfolio import select_candidates; print(select_candidates([]))"

---

必要に応じて README をさらに展開（API の詳細、ExecutionEngine の設定例、監視ルールのチューニング方法、データベーススキーマの説明など）できます。どの項目を詳しく記載するか指定してください。