# KabuSys

日本株自動売買システムのコアライブラリ群（README）。  
この README はリポジトリ内のスクリプト・モジュールに基づいて日本語で要約しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。  
主な目的は以下です。
- データパイプライン / ファクター計算（research）
- ポートフォリオ構築・サイズ決定（portfolio）
- 発注・注文管理・リスク管理（execution）
- システム稼働監視・アラート・Kill Switch（monitoring）
- ニュース NLP による AI スコアリング（ai）
- 運用・検証用ユーティリティ（tools）

設計方針として、DB（DuckDB/SQLite）をデータストアに利用し、実際の発注は環境によって本番/ペーパートレードを切り替えられるようになっています。

---

## 機能一覧

- 環境設定ウィザード（.env の対話式生成）: python -m kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の検証）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番/ペーパー分離）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、paper_trading.db に記録
- SystemMonitor ポーリング（system 状態記録、プロセス監視）: python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL により上書き可能（デフォルト 60 秒）
- MonitoringEngine（各種モニタを束ねてポーリング・アラート/kill 評価）
- RiskMonitor / TradeMonitor / SystemMonitor（ドローダウン・滞留注文・データ鮮度等の監視）
- MonitoringDB（SQLite）による監視ログ永続化
- Portfolio construction（候補選定・重み計算・ポジションサイズ計算、セクター制約等）
- Research（DuckDB を使ったファクター計算、IC 計算、特徴量探索）
- AI モジュール：
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores に書き込み）
  - regime_detector: ETF + マクロニュースで市場レジーム判定
- Tools:
  - paper_verification_report: ペーパートレード DB から検証レポート出力

---

## 必要条件 / 依存パッケージ（代表）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の検証を行う場合、なくても動作するが警告になる）
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

インストール例（pip）:
pip install duckdb psutil openai pyyaml

※プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン / checkout
2. Python 仮想環境を作成して依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt （存在する場合）
   - または上記の個別パッケージを pip install
3. .env を作成
   - 対話式ウィザードを使う:
     python -m kabusys.config_setup
   - もしくは手動で .env を作成し下記必須項目を設定
4. 設定の検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで exit(1)
5. 必要なディレクトリを作成（通常は自動作成されます）
   - data/ （SQLite / PID / フラグファイル保存）
   - logs/ （ログ出力）

---

## 重要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

運用 / オプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
  - paper_trading の場合は MockBroker を使い、専用 SQLite（PAPER_TRADING_SQLITE_PATH）にデータ記録
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）
- MONITOR_POLL_INTERVAL — SystemMonitor のポーリング間隔（秒、デフォルト 60）

.env にはこれらを設定しておくことを推奨します。.env は決して Git にコミットしないでください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine の起動（本番 / ペーパー切替は KABUSYS_ENV で制御）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution
  - 備考: paper_trading では paper_trading.db を使用し、本番 DB とは分離されます。
  - 停止は data/stop_requested.flag を作成すると検知して終了します（run_execution が参照）。

- SystemMonitor（監視ループ）の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  # 30秒間隔に上書き
  - 停止は data/stop_requested.flag を作成すると検知して終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OPENAI_API_KEY を参照します。API キーは引数で上書き可能。

- 設定・DB の初期化
  - 実行スクリプト（run_execution/run_monitoring）は起動時に監視テーブルの初期化（init_monitoring_db）を行います。

---

## 運用上の注意 / トラブルシューティング

- プロセス優先度設定:
  - 起動時に set_process_priority("high") を試みます。権限がない場合は警告ログを出してスキップします（psutil に依存）。
- ログ:
  - logs/<app_name>.log に日次ローテートで出力（TimedRotatingFileHandler）。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- kill.flag / stop フラグ:
  - kill.flag (Settings.kill_flag_path / デフォルト data/kill.flag) は ExecutionEngine を強制停止させるためのフラグです。KillSwitch が条件成立時に書き込みます。
  - stop_requested.flag は run_* スクリプトが監視している停止フラグ（data/stop_requested.flag）。手動でこのファイルを作るとスクリプトが終了します。
- Paper Trading DB:
  - paper_trading 環境は本番 DB と完全分離されるよう設計されています。実運用では KABUSYS_ENV を正しく設定すること。
- AI 呼び出し:
  - OpenAI API はレート制限やエラー発生があるためリトライとフェイルセーフを実装しています。API キーが未設定だと例外になります。
- duckdb / sqlite ファイル:
  - デフォルトパスは data/kabusys.duckdb、data/monitoring.db 等です。config により上書き可能。親ディレクトリがなければ自動作成されることが想定されていますが、パーミッションに注意してください。
- validate_config:
  - PyYAML 未インストール時は config/*.yaml の検証がスキップされます（警告）。

---

## ディレクトリ構成（src/kabusys を基準に主要ファイルを抜粋）

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings（自動 .env ロード含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores へ書き込み
    - regime_detector.py — 市場レジーム判定（ETF + マクロニュース + LLM）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化レイヤ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — （注文監視、コードベースに存在）
    - kill_switch.py — kill.flag 書き込みロジック
    - alert_manager.py — （アラート送信ロジック、コードベースに存在）
  - execution/
    - execution_engine.py — 発注エンジン本体（起動・セッション管理）
    - broker_factory.py — ブローカクライアント生成（Mock / 実実装切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスクロジック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数決定ロジック
    - risk_adjustment.py — セクター制約・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility ファクター計算
    - feature_exploration.py — IC / 前方リターン / 統計サマリ
  - utils/
    - logging_setup.py — 統一的なログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
  - data/ (実運用で生成される)
    - monitoring.db（default SQLite）
    - paper_trading.db（ペーパートレード時）
    - stop_requested.flag, kill.flag, execution.pid など運用フラグ

（実際のツリーはリポジトリのファイル一覧を参照してください）

---

## 開発者向けメモ

- 単体関数群（portfolio/*.py, research/*.py, monitoring/*.py）は外部副作用を抑え、テストしやすい純粋関数や明確なインタフェースを提供する設計です。DuckDB 接続や sqlite3.Connection を引数で受け取るため、テスト時に簡易 DB を注入できます。
- AI 呼び出し部はテストでモック化できるよう内部呼び出しを分離しています（_call_openai_api を patch 可能）。
- 一部の DB 書き込みは冪等性を考慮して設計されており、起動順や部分失敗時の安全性が考えられています。

---

必要であれば README にサンプル .env テンプレートや運用手順（systemd / cron 登録例、ログローテーションの監視、バックアップ方針など）を追加します。どの情報を追加したいか教えてください。