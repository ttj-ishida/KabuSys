# KabuSys

日本株向けの自動売買システム（プロジェクト骨格）。  
このリポジトリは以下の主要機能群を提供します: 注文実行エンジン、監視・アラート、ポートフォリオ構築、ファクター計算、ニュース NLP（OpenAI）連携など。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、日本株の自動売買を想定したコンポーネント群です。設計方針としては以下を重視しています。

- コンポーネント分離（Execution / Monitoring / Research / Portfolio / AI）
- 環境（本番 / ペーパートレード / 開発）の分離
- フェイルセーフ（外部 API 失敗時のフォールバック、Kill Switch）
- テストしやすい純粋関数群（Portfolio / Research 等は DB に依存しない）
- ロギングとローテーション（logs/*.log）

主要なランタイムモジュール:
- run_execution.py — 発注エンジン起動スクリプト（KABUSYS_ENV により実環境 or ペーパー）
- run_monitoring.py — 監視ループ起動スクリプト
- monitoring_engine.py — 個別 Monitor をまとめるエンジン（ポーリングロジック）
- tools/paper_verification_report.py — ペーパートレード検証レポート生成ツール

---

## 機能一覧

- Execution
  - ExecutionEngine（発注・注文管理・リスク管理・レコンシリエーション等）
  - Paper trading モード（MockBrokerClient を使用し、paper_trading DB に記録）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 発注ログ・滞留注文の検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション数上限監視
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: アラート送信（LINE 等を利用する設計、設定次第で有効）
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索（前方リターン計算、IC 計算、統計サマリ）
  - ポートフォリオ構築（候補選定、重み計算、株数決定、セクター制限等）
- AI
  - news_nlp: OpenAI を使ったニュースセンチメント解析（ai_scores へ保存）
  - regime_detector: MA + マクロニュースで市場レジーム判定（market_regime へ保存）
- ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話的作成
  - 設定検証 CLI（validate_config.py）
  - paper_trading 検証レポート生成ツール

---

## 前提 / 依存（主なパッケージ）

必須（少なくともこれらのインストールを想定）:
- Python 3.9+（typing 機能などを利用）
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- （オプション）PyYAML — validate_config の YAML 検証に利用

requirements.txt は本サンプルには含まれていないため、プロジェクト用途に合わせて作成してください。

---

## セットアップ手順

1. レポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML

4. .env を準備
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - 手動作成: プロジェクトルートに `.env` を置く（.env.example を参考に必要な環境変数を設定）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリ
   - デフォルトで data/ および logs/ にファイルを書きます。必要に応じて作成・権限を確認してください（setup_logging が起動時に自動作成を試みます）。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要な任意 / 設定:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db に記録される
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI を利用する機能（news_nlp / regime_detector 等）で使用
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0 推奨）

注意: 必須環境変数が未設定だと起動時にエラーになります。config_setup で .env を生成し、validate_config で事前チェックしてください。

---

## 実行方法

基本的にパッケージモジュールとして実行します。

- ExecutionEngine を起動（エンジン本体は ExecutionEngine を使用）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、専用 DB に記録します。
  - 実行前に kill.flag（data/kill.flag）を確認し、必要なら削除してください（設定で自動クリアも可能）。

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: 30）
  - python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path を使って監視ログを記録します（環境に依らず同一 DB を使用します）。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを明示できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

ログ:
- デフォルト出力先: stdout と logs/<app_name>.log（日次ローテーション、30日保管）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一

停止制御:
- プロセスを安全に停止させるには data/stop_requested.flag（run_* スクリプトが監視）または kill.flag を使用
  - run_monitoring/run_execution は stop flag を検出するとグレースフルに終了します

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数/.env の自動読み込みと Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM センチメント評価と ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - kill_switch.py, alert_manager.py（注: alert_manager の実装次第で通知先を設定）
- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数決定・資金配分ロジック
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ一元設定
  - process_priority.py — プロセス優先度設定ユーティリティ

データ・ログ（プロジェクトルート）
- data/
  - kabusys.duckdb (デフォルト)
  - monitoring.db (SQLite)
  - paper_trading.db (paper_trading 用)
  - execution.pid, stop_requested.flag, kill.flag などのフラグ/PIDファイル
- logs/
  - execution.log, monitoring.log 等（TimedRotatingFileHandler で日次ローテーション）

---

## 注意事項 / トラブルシューティング

- 必須環境変数未設定 → 起動に失敗します。まず config_setup で .env を整備し、validate_config を実行してください。
- OpenAI 機能を使う場合は OPENAI_API_KEY を設定してください。API エラー発生時は安全側フォールバック（スコア 0.0 等）を行う実装になっていますが、機能は限定的になります。
- PyYAML がないと validate_config は config/*.yaml の内容検証をスキップします（警告出力）。YAML 検証を有効にしたい場合は PyYAML をインストールしてください。
- run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で調整可能（デフォルト 60 秒）。0 以下の値は無効でデフォルトにフォールバックします。
- データベース（DuckDB / SQLite）はデフォルトで data/ 以下に作成されます。別パスを使用したい場合は環境変数で上書きしてください。
- Kill Switch: RiskMonitor がトリガー条件を満たすと data/kill.flag を作成します。ExecutionEngine は起動時や実行中にこれを検出して停止します。KILL_FLAG_CLEAR_ON_START に注意（本番で auto-clear は危険）。

---

以上がこのコードベースの概要と利用手順です。必要であれば README にサンプル .env のテンプレートや systemd/cron 用の起動例（service ファイルやログローテーション設定）を追記できます。どの情報を優先して追加しますか？