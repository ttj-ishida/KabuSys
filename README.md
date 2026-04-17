# KabuSys

日本株向けの自動売買システム（ライブラリ兼実行スクリプト群）

このリポジトリは、戦略計算・ポートフォリオ構築・発注エンジン・監視・レポーティング・AI（ニュースセンチメント／レジーム判定）などを含む自動売買プラットフォームのコア実装です。

---

目次
- プロジェクト概要
- 機能一覧
- 必要要件
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要項目）
- 停止・Kill スイッチ
- ライブラリ（プログラム）呼び出し例
- ディレクトリ構成

---

プロジェクト概要
- 戦略用のファクター計算、特徴量探索（research）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 発注・ExecutionEngine（本番 / ペーパートレード切替サポート）
- 監視（System / Trade / Risk）およびアラート（LINE）
- ニュースの LLM を用いたセンチメントスコアリング、レジーム判定（OpenAI）
- Paper Trading 向けの検証レポート生成ツール

機能一覧（抜粋）
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用しデータを paper_trading.db に保存
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
- 監視ログの永続化（SQLite）と簡易 DB マイグレーション（monitoring_db.py）
- Trade / Risk / System の各種チェックとアラート送信（LINE）
- ニュース NLP による銘柄別スコアリング（OpenAI API を使用）
- 市場レジーム判定（ETF MA + マクロニュースの LLM 評価の組合せ）
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
- ポートフォリオ構築関数群（等配分・スコア加重・セクター上限・リスクベース等）

必要要件（主要パッケージ）
- Python 3.9+（ソース基準）
- duckdb
- psutil
- openai
- requests
- PyYAML（設定ファイル検証は任意。無い場合は YAML 検証をスキップ）

（推奨）requirements.txt を用意している場合は次のようにインストールしてください:
pip install -r requirements.txt

セットアップ手順
1. リポジトリをクローン / 展開
2. Python 環境を用意し依存パッケージをインストール
   - pip install duckdb psutil openai requests pyyaml
3. 初期環境変数ファイル (.env) を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - ウィザードで作成された .env を保存してください（.env は絶対にコミットしないでください）
4. 設定の検証（必須項目等のチェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     python -m kabusys.validate_config --strict
5. データディレクトリ（data/）の確認
   - デフォルトで使用される DB 等:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - 実行時に親ディレクトリが存在しなければ自動作成されることがありますが、権限や設置場所を確認してください。

主要な使い方（コマンド例）
- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視ループ起動（SystemMonitor ポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - run_monitoring は Settings に依存して本番 sqlite_path を使います（監視は本番 DB を参照）

- ExecutionEngine 起動（発注エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは専用 paper DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用
  - 起動前に data/kill.flag の自動クリア設定がある場合は注意（KILL_FLAG_CLEAR_ON_START）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB を指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注はモック。DBは paper_trading.db
  - live: 本番（実際に発注）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定動作（instant|partial|never|reject。デフォルト "instant"）
- OPENAI_API_KEY — OpenAI 呼び出しに必要（ニュース NLP / レジーム判定）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら通知はスキップ）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）; run_monitoring/run_monitoring の起動時に参照
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（1/0, 本番では 0 推奨）

停止 / Kill スイッチ
- run_execution.py / run_monitoring.py はプロジェクト直下 data/stop_requested.flag の存在をチェックして安全に停止します（スクリプト内の STOP_FLAG）。
- 監視側の KillSwitch は data/kill.flag を書き込むことで ExecutionEngine の停止トリガーとします（KillSwitch は条件を満たすとファイルを書き込みます）。
- 実行中のプロセスは pid ファイル（例: data/execution.pid）で管理され、SystemMonitor は stale PID を検出すると削除します。

ライブラリ（プログラム）呼び出し例（Python）
- ニューススコアリング（AI）
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="...")

- レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")

- ポートフォリオ構築関数
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

注意事項・運用上のヒント
- .env は機密情報を含むため絶対に Git 等にコミットしないでください。
- OpenAI の使用は API キーと料金に注意してください（大量バッチでコストが発生します）。
- 本番（KABUSYS_ENV=live）での起動前に validate_config を実行して全設定を確認してください。
- run_execution は paper_trading のとき DB を分離するのでテストに便利です。
- Monitoring のログ・テーブルは init_monitoring_db で自動的に作成・必要なカラム追加（マイグレーション）を行います。

ディレクトリ構成（src/kabusys/ の主要ファイル）
- __init__.py — パッケージ定義
- config.py — 環境変数 / Settings 管理、自動 .env 読み込みロジック
- config_setup.py — .env を対話的に作成するウィザード
- validate_config.py — 起動前チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（概要）
- ai/
  - news_nlp.py — ニュースの LLM センチメント化（ai_scores テーブル書き込み）
  - regime_detector.py — 市場レジーム判定（ma200 + LLM）
- monitoring/
  - monitoring_db.py — SQLite のテーブル作成 / 永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/実行プロセス監視
  - trade_monitor.py — 注文滞留・約定異常のチェック
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag の生成 / 管理
  - alert_manager.py — LINE 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
- execution/ (発注系コンポーネント)
  - order_manager, order_repository, execution_engine, reconciler, broker_factory 等（発注・リスク・照合ロジック）
- portfolio/
  - portfolio_builder.py — 候補選定、重み計算
  - position_sizing.py — 株数算出、単元丸め、投下資金スケーリング
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

— 以上 —

問題が発生したり追加で README に載せたい情報（例: サンプル .env、requirements.txt、起動システムdユニットの例）があれば教えてください。必要に応じて README を拡張してデプロイ手順や運用手順（systemd / supervisor 等）を追記します。