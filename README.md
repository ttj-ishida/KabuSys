KabuSys
=======

日本株自動売買システムの一部（コアユーティリティ・監視・実行エントリ・ポートフォリオ構築・リサーチ・AI スコアリング等）を収めたコードベースです。  
この README はリポジトリに含まれる主要スクリプト／モジュールの概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買プラットフォームのコンポーネント群です。本リポジトリは次の主要機能を含みます。

- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - 実際のブローカークライアントまたは Paper Trading（モック）を用いた注文送信
  - リスク管理・注文管理・リコンシリエーション等の統合
- Monitoring（監視）コンポーネント（run_monitoring.py / monitoring/*）
  - システムヘルス（CPU/メモリ/ディスク）、プロセス生存確認、注文・リスクの監視
  - Kill Switch（条件が揃えば Execution を停止させるフラグファイルの書き込み）
- Portfolio 建設ロジック（portfolio/*）
  - 候補選定、重み計算、ポジションサイズ決定、セクター制限・レジーム調整
- Research（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）と特徴量探索ユーティリティ
- AI モジュール（ai/*）
  - ニュースに基づくセンチメントスコアリング（OpenAI API を利用）
  - 市場レジーム判定（MA と LLM の融合）
- ユーティリティ（utils/*）
  - ロギング設定、プロセス優先度設定、設定読み込み等
- ツール（tools/*）
  - Paper Trading の検証レポート生成スクリプトなど
- 設定ツール・検証ツール
  - 対話式 .env 生成ウィザード（config_setup.py）
  - 起動前チェック（validate_config.py）

主な機能一覧
-------------
- 設定管理：
  - .env の自動読み込み（プロジェクトルートを自動検出）、対話形式で .env を作成可能
- Execution：
  - 本番（live） / ペーパートレード（paper_trading）を切り替え可能
  - Paper モードでは MockBrokerClient を使用し、paper_trading.db に記録（本番 DB と分離）
- 監視：
  - system_status / trade_logs / risk_logs / dashboard / positions を SQLite に保存
  - ポーリング監視ループ、Kill Switch による安全停止
- ポートフォリオ構築：
  - 候補選定、等配分・スコア配分、リスクベースのポジションサイズ決定
  - セクターキャップやレジーム乗数の適用
- 研究・分析：
  - DuckDB を用いたファクター計算、forward returns、IC 計算、統計サマリ
- AI（LLM）連携：
  - OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価、レジーム判定
  - API 呼び出しはリトライ／バックオフを備えた堅牢実装
- 運用支援：
  - ログのタイムベースローテーション（logs/*.log）
  - プロセス優先度・CPU affinity の簡易設定

セットアップ手順
----------------

1. Python 環境を準備
   - 推奨: Python 3.10+
   - 仮想環境の作成・有効化（例）:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存（例）:
     - pip install duckdb psutil openai PyYAML
     - sqlite3 は標準ライブラリに含まれます

3. .env の準備
   - 対話式ウィザードで作成（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参考に .env を手動作成
   - 自動ロードについて:
     - kabusys.config は実行時にプロジェクトルートの .env / .env.local を読み込みます。
     - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL 扱い）:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成
   - デフォルトで使用するパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag / ログ: data/*.pid, data/kill.flag, data/stop_requested.flag, logs/
   - 必要なら手動で作成: mkdir -p data logs

環境変数の主な一覧
-------------------
（必須）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）

（推奨／任意）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールを使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知に使用（任意）
- PAPER_FILL_MODE — paper_trading 時のフィルモード（instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（主要スクリプト）
-----------------------

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings に従って SQLite（monitoring.db）と DuckDB に接続
    - SystemMonitor を初期化してポーリングループを開始
    - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書き（デフォルト 60）
    - data/stop_requested.flag を検知するとループ終了

- 実行（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading.db に記録
    - 実行中は data/execution.pid に PID を書き、data/stop_requested.flag により停止可能
    - 実行開始前に data/stop_requested.flag が既に存在する場合は起動しない

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD, --db PATH
  - 簡易合格基準（uptime, fill_rate, send_rate, latency P95）に基づく判定を行う

- AI / レジーム判定 / スコアリング（プログラム的利用）
  - kabusys.ai.score_news（news_nlp）
  - kabusys.ai.regime_detector.score_regime
  - これらは DuckDB 接続と target_date、OpenAI API キーを受け取り DB に書き込みます

運用上の注意
-------------
- Kill Switch / Stop フラグ
  - KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（Monitoring が評価して書き込む）。
  - run_monitoring / run_execution は data/stop_requested.flag を参照して起動／ループの停止を制御します。
- .env ファイルは機密情報を含むため絶対に Git へコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知等の設定を必ず確認してください（validate_config の live ガード参照）。
- OpenAI API を使用する機能は API コストと rate limit に注意してください。SDK／API のバージョン差分に備えたリトライ実装がありますが、運用時は適切なキーとレート管理が必要です。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR 環境変数で変更可。

ディレクトリ構成（主なファイル）
--------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数と Settings クラス、.env 自動ロードロジック
- config_setup.py — .env 作成ウィザード（対話式）
- validate_config.py — 起動前の設定検証 CLI

- run_monitoring.py — Monitoring ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

- utils/
  - logging_setup.py — 共通ログ設定（Stream + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / DB 操作ラッパー
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文系の監視（滞留注文、約定異常等） ※詳細ファイルあり
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の生成 / 管理
  - monitoring_engine.py — 各監視を束ねるエンジン
  - alert_manager.py — 通知送信（LINE 等） ※実装あり

- execution/
  - execution_engine.py — 実行エンジン本体（セッション管理）
  - broker_factory.py — BrokerClient の生成（実ブローカー or Mock）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注・リスク関連

- portfolio/
  - portfolio_builder.py — 候補選定 / 重み計算
  - position_sizing.py — 株数計算・上限・丸め
  - risk_adjustment.py — セクターキャップ / レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 連携）
  - regime_detector.py — 市場レジーム判定（MA + LLM）

- data/ （実行時に生成される想定）
  - monitoring.db (SQLITE_PATH デフォルト)
  - kabusys.duckdb (DUCKDB_PATH デフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid, stop_requested.flag, kill.flag など

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成

補足（設計上のポイント）
-----------------------
- DB：
  - 監視ログ等は SQLite（軽量）で永続化、分析やファクター計算は DuckDB を利用する設計
- セーフガード：
  - Paper Trading と live を明確に分離（DB・ブローカーの分離）
  - Kill Switch・リスク監視で異常時に自動停止可能
- LLM 呼び出し：
  - JSON Mode を使い厳密な出力を期待、リトライやレスポンス検証して堅牢性を確保

必要に応じて README を拡張してください（例: requirements.txt の正確なパッケージ一覧、実行例ログ、CI 手順、デプロイ方法など）。もし特定のファイルやモジュールについて詳細説明（API 仕様・引数・戻り値等）を README に追記したい場合は、どの部分を優先するか教えてください。