KabuSys — 日本株自動売買システム
======================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）／注文管理／リスク管理
- 監視（System / Trade / Risk）とアラート／Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・株数算出）
- 研究用モジュール（ファクター計算・IC解析など）
- ニュース NLP を用いたスコアリング・レジーム判定（OpenAI 経由）
- ペーパートレード向け分離 DB、レポート生成ツール
- 共通ユーティリティ（ロギング設定・プロセス優先度設定 等）

特徴
----
- 環境変数/.env による設定管理（config_setup.py によるウィザードあり）
- 実運用（live）とペーパートレード（paper_trading）を明確に分離
  - paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db に記録
- DuckDB を分析向けに、SQLite を監視・注文ログなどの永続化に使用
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価・レジーム判定（API キー必須）
- Kill Switch（data/kill.flag）による安全停止、外部停止フラグ（data/stop_requested.flag）による運用制御
- 日次ローテートのログ出力（logs/ 以下）とコンソール出力を統一的に管理

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows では .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な必須パッケージ（例）
     - pip install duckdb psutil openai PyYAML

   （実行環境によっては追加パッケージが必要です）

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabu API パスワード、DB パス等を入力します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの準備
   - data/ や logs/ は自動作成されますが、必要であれば手動で作成してください。

主要な環境変数（主なもの）
--------------------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）
- PAPER_FILL_MODE: ペーパートレードでのフィルモード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で読み込む。デフォルト 60 秒）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env を作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - KABUSYS_ENV=live python -m kabusys.run_execution
    - 本番では本番の DB（SQLITE_PATH）を使います。

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト間隔は 60 秒。環境変数で上書き可。
    - 監視は Settings.sqlite_path（本番 sqlite_path）を常に使用します。
    - 停止: data/stop_requested.flag を作成すると監視ループは終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコア／レジーム判定）
  - プログラムから kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数、または関数引数で渡す）

停止と Kill Switch
-----------------
- 停止フラグ: data/stop_requested.flag
  - run_execution や run_monitoring はこのファイルの存在を監視しており、存在する場合に終了処理を行います（運用上の素早い停止用）。

- Kill Switch: data/kill.flag
  - Monitoring の KillSwitch はリスク閾値（ドローダウンやポジション上限）を満たした場合に data/kill.flag を作成します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動的にクリアされる挙動があります（本番では 0 推奨）。

ロギング
--------
- ログはログディレクトリ（デフォルト logs/）に app_name ごとのファイル（例: logs/execution.log, logs/monitoring.log）を日次ローテーションで出力します。
- コンソールは stdout に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging を全起動スクリプトから呼び出しています。

データベースと永続化
-------------------
- DuckDB: analytics 用（prices_daily, raw_financials, raw_news, ai_scores 等）
  - デフォルトパス: data/kabusys.duckdb

- SQLite:
  - 監視・注文・ポジション等は SQLite（monitoring DB）に保存
    - デフォルト: data/monitoring.db
  - ペーパートレードは本番 DB と分離して data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使用

- 初回起動時は必要なテーブルを自動作成する init_monitoring_db があり、マイグレーション（列追加）も簡易対応済みです。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings 管理
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring ポーリング起動スクリプト

- ai/
  - news_nlp.py                 — ニュース NLP（OpenAI）で ai_scores を生成
  - regime_detector.py          — レジーム判定（ma200 + macro sentiment）
- monitoring/
  - monitoring_db.py            — SQLite 用永続化層（テーブル作成・読み書き）
  - system_monitor.py           — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py            — 注文の滞留・約定異常監視（※実装参照）
  - risk_monitor.py             — ドローダウン・ポジション上限の監視
  - kill_switch.py              — Kill Switch 実装（flag ファイル書き込み）
  - monitoring_engine.py        — 各モニタを組み合わせたループ
  - alert_manager.py            —（アラート送信層：LINE 等）※実装参照

- execution/
  - execution_engine.py         — 実行エンジン本体
  - order_manager.py            — 注文管理
  - order_repository.py         — DB による注文ログ保存
  - broker_factory.py           — BrokerClient の生成（Mock / 実 API 切替）
  - reconciler.py               — 差分修復ロジック
  - risk_manager.py             — 発注前リスクチェック

- portfolio/
  - portfolio_builder.py        — 候補選定・重み付け
  - position_sizing.py          — 発注株数の算出（lot 単位丸め・スケーリング）
  - risk_adjustment.py          — セクター制限・レジーム乗数

- research/
  - factor_research.py          — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py      — 将来リターン・IC・統計解析

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

- utils/
  - logging_setup.py            — ログ設定ユーティリティ
  - process_priority.py         — プロセス優先度 / CPU affinity ユーティリティ

運用上の注意
------------
- .env（機密情報）は絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくことを推奨します。
- OpenAI API を利用する機能は API 費用が発生します。API 呼び出し回数やバッチ処理を適切に制御してください。
- 監視は常に Settings.sqlite_path（本番用）を参照します。ペーパートレード時でも monitoring の DB は本番パスを使用する設計に注意してください（設計上の意図に基づく挙動）。

開発者向けヒント
----------------
- 単体関数群（portfolio/*.py, research/*.py）は副作用がなくテストしやすい純粋関数として設計されています。ユニットテストの対象に適しています。
- OpenAI 呼び出しはモック化しやすいように内部呼び出し関数を分離しています（テストではパッチして応答を制御してください）。
- ロギングは全体で統一されているため、setup_logging を起動スクリプトで最初に呼ぶことを推奨します。

ライセンス・バージョン
--------------------
- 現在のパッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

本 README はコードベースの主要点をまとめたもので、詳細は各モジュールの docstring / コメントを参照してください。追加で README に含めたい内容（例: 実行例のログ出力例、より詳細な env.example、CI 設定など）があれば指示してください。