# KabuSys

日本株自動売買システムのコアライブラリ / 起動スクリプト群の README（日本語）

このリポジトリは、アルゴリズム売買の実行エンジン、監視、ファクター計算、ポートフォリオ構築、AI を使ったニュース評価などを含むモジュール群です。README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を説明します。

※ 本ドキュメントは src/kabusys 以下のコードベースに基づいています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤ライブラリです。主なコンポーネントは次の通りです。

- ExecutionEngine：ブローカークライアントと連携して注文を生成・管理する実行エンジン
- Monitoring：実行プロセスやシステム指標、注文ログ、リスク指標を監視し、条件に応じて Kill Switch（停止フラグ）を発動
- Portfolio：候補選定、重み計算、ポジションサイズ算出、セクターキャップ等のポートフォリオ構築ロジック
- Research：DuckDB を用いたファクター計算・将来リターン・IC 計算などの研究ツール
- AI：OpenAI を使ったニュースセンチメント評価・市場レジーム判定（OpenAI API 必須）
- Tools：ペーパートレード検証レポート等のユーティリティスクリプト
- Utils：ログ設定、プロセス優先度設定、設定読み込みユーティリティ等

設計上の特徴：
- DuckDB / SQLite をローカル DB として利用（データ分析 / 永続化）
- 環境変数または .env による設定管理
- ペーパートレード（隔離された DB）に対応
- LLM を用いる機能は API キーが無い場合はフェイルセーフでスキップまたはエラーを明示

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV により paper_trading の場合は MockBroker を使用）
  - run_monitoring.py：SystemMonitor をポーリング起動（MONITOR_POLL_INTERVAL で間隔指定可能）
- 監視
  - system_monitor：CPU / メモリ / ディスク利用率、Execution プロセス健全性、データ鮮度チェック
  - trade_monitor：発注ログの滞留・約定異常などを検出（ファイル内に実装あり）
  - risk_monitor：ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - kill_switch：条件に応じて data/kill.flag を書き込み、Execution の停止をシグナリング
  - monitoring_engine：上記を束ねてポーリング・アラート通知
- ポートフォリオ構築
  - 候補選定、等配分・スコア加重、リスクベースのポジションサイズ算出、セクターキャップ、レジーム乗数
- Research（DuckDB）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC 計算、統計サマリー
- AI（OpenAI）
  - news_nlp：raw_news を LLM に送り銘柄ごとのセンチメントを ai_scores に書込
  - regime_detector：ETF ma200 とマクロニュースを合成して日次レジーム判定を行い DB に書込
- ユーティリティ
  - config_setup.py：.env を対話的に作成するウィザード
  - validate_config.py：環境変数・config/*.yaml の事前検証
  - tools/paper_verification_report.py：ペーパートレード DB から検証レポートを生成

---

## セットアップ手順

前提：Python 3.9+（実行環境に依存）。必要な Python パッケージをインストールしてください。

推奨パッケージ（コード内で使用）：
- duckdb
- psutil
- openai
- PyYAML（config.yaml の検証を行う場合）

例（pip）:
- pip install duckdb psutil openai pyyaml

1. リポジトリをクローン / 配布パッケージを展開
2. .env を作成
   - 対話式で作成する（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成
   - 自動読み込みの仕組み:
     - パッケージロード時にプロジェクトルート（.git または pyproject.toml 任意検出）から .env, .env.local を読み込みます
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
3. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - その他（必要に応じて）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番アラート送信時）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア 0=クリアしない。production では 0 推奨）
4. DB 初期化
   - run_execution.py / run_monitoring.py は起動時に monitoring DB のテーブル作成（init_monitoring_db）を行います
   - DuckDB のスキーマや config/*.yaml は別途スクリプト（scripts/generate_config.py 等）で生成する想定

---

## 使い方（よく使うコマンド）

基本的にプロジェクトルートで実行します。

1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする（厳格モード）:
     - python -m kabusys.validate_config --strict

3. Execution エンジンを起動
   - python -m kabusys.run_execution
   - 備考:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
     - 起動時に data/execution.pid に PID を書きます（設定により異なる）
     - 停止は監視が書き込む data/kill.flag またはプロセスに対する SIGINT 等

4. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - デフォルト: 60 秒
   - 停止フラグ:
     - data/stop_requested.flag を作成すると監視ループは終了します（run_monitoring/run_execution 両方でチェック）

5. Paper Trading の検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
   - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

6. AI 機能の実行（ライブラリ関数）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - conn: DuckDB 接続
     - api_key: None の場合 OPENAI_API_KEY 環境変数を参照
   - regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意: OpenAI API キー設定が必要。失敗時はフェイルセーフまたは例外が投げられる箇所があります（ドキュメント参照）

ログ:
- 共通のログ設定を用意： kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します
- デフォルト出力先:
  - コンソール（stdout）
  - logs/<app_name>.log（デイリーローテーション、30 日保持）
- ログディレクトリは LOG_DIR 環境変数、またはデフォルト logs/

停止 / Kill Switch:
- 実行ループは監視やフラグファイルで制御します
  - data/stop_requested.flag: 主に開発用の即時終了フラグ（run_execution/run_monitoring がチェック）
  - data/kill.flag: KillSwitch が条件を満たした際に作成され、ExecutionEngine に停止シグナルを送る
- Execution の PID ファイル: data/execution.pid（設定で変更可）

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabu ステーション API）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト development
  - is_paper 判定により Execution が専用 DB を使う
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — monitoring 用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL — ログレベル（デフォルト INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、production では 0 推奨）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読込を無効化

※ .env の対話式セットアップで多くのキーは設定できます（python -m kabusys.config_setup）。

---

## DB / スキーマ関連

- monitoring_db.init_monitoring_db(conn) が起動時に監視 DB（SQLite）のテーブルを作成します（冪等）
  - system_status, trade_logs, positions, risk_logs, dashboard など
  - マイグレーション処理（カラム追加）も軽微にサポート
- DuckDB は分析用に prices_daily / raw_financials / raw_news / ai_scores / market_regime 等を前提とした設計
  - データの取り込み・マスター生成は別スクリプト（このリポジトリ外または scripts ディレクトリ）で実施する想定

---

## トラブルシューティング / 注意点

- 必須環境変数が不足していると validate_config.py や Settings プロパティで例外が発生します。まず validate_config を実行して確認してください。
- OpenAI を使う機能は API キーが無ければ動作しません。AI 機能呼び出し時に ValueError が投げられます。
- run_monitoring は MONITOR_POLL_INTERVAL が不正な値（0 や負値、非数）の場合デフォルト 60 秒にフォールバックします。
- ログディレクトリ作成に失敗した場合でもコンソール出力は行われます（ファイル出力はスキップ）。
- プロセス優先度設定（set_process_priority）は権限やプラットフォームによって失敗することがあり、その場合は警告ログに留まります。
- データ鮮度チェックなど一部のロジックは DuckDB のテーブル存在や内容に依存します。使う前に該当テーブルとデータを用意してください。

---

## ディレクトリ構成（src/kabusys ベース）

以下は主要なファイル / モジュール（抜粋）と簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（__version__ など）
  - config.py — 環境変数読み込み・Settings クラス（.env 自動ロード機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + ma200 を合成して market_regime を書き込む
  - monitoring/
    - monitoring_db.py — SQLite による永続化層（テーブル作成 / CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留 / 約定異常検出等）
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag の作成・管理
    - monitoring_engine.py — 各監視を束ねる実行ループ
    - alert_manager.py — （アラート送信用の抽象化）
  - execution/
    - execution_engine.py — 実行エンジン本体（セッション管理等）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value ファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

（実際のリポジトリにはさらに補助スクリプトやモジュールが含まれている可能性があります）

---

## 開発メモ / 提案

- 本番環境（KABUSYS_ENV=live）では kill.flag や KILL_FLAG_CLEAR_ON_START の設定に注意してください（自動クリアは危険）。
- AI 呼び出しはレート制限やエラーに備えてリトライとフェイルセーフを実装していますが、API コストや応答時間を考慮してバッチサイズや頻度を調整してください。
- DuckDB のスキーマや price データの整備は研究機能の精度に直結します。データ整備パイプラインを別途用意してください。

---

必要な追加情報（例：環境変数の .env.example、依存パッケージ一覧、起動用 systemd/cron ユニットのサンプルなど）があれば、追って README を拡張します。必要ならテンプレートや例ファイルも作成しますのでお知らせください。