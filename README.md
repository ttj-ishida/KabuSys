KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」のコア実装（分析・ポートフォリオ構築・発注制御・監視・AI 補助など）をまとめた Python パッケージです。本 README ではプロジェクト概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

プロジェクト概要
-------------
KabuSys は以下の主要機能を持つ自動売買フレームワークです。

- DuckDB / SQLite を用いた時系列データ保管と分析
- ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- ExecutionEngine（発注ロジック、ブローカー抽象化、リスク管理）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- ペーパートレード用の分離 DB と検証レポート生成
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード・検証 CLI）

主な機能一覧
-------------
- 設定管理（kabusys.config）
  - .env 自動ロード、必須環境変数チェック、Settings クラス経由のアクセス
- 設定ウィザード（kabusys.config_setup）
  - 対話式で .env を生成・更新
- 設定検証 CLI（kabusys.validate_config）
  - .env と config/*.yaml の妥当性チェック（--strict あり）
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading DB に記録
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 監視サブシステム（kabusys.monitoring）
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等配分/スコア配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算
- 研究／ファクター計算（kabusys.research）
  - モメンタム / ボラティリティ / バリュー計算、将来リターン、IC 計算、統計サマリー
- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア化（ai_scores テーブルに書き込み）
  - regime_detector: ETF 指標 + マクロニュースの LLM 判定を合成して市場レジームをスコア化・書き込み
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定付きレポートを生成

セットアップ手順
----------------
前提
- Python 3.9+
- 必要な Python パッケージ（プロジェクトの requirements.txt があれば参照）
  - 基本: duckdb, psutil
  - AI 機能: openai
  - 検証ツール: PyYAML（存在しなければ YAML 検証はスキップされる）
- SQLite は標準ライブラリで利用可能

一般的な手順
1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML など（必要に応じて）
4. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB; デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、paper_trading 時に使用）
     - OPENAI_API_KEY（AI機能利用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知に利用、任意）

設定検証
- .env と config/*.yaml の整合性をチェック:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

使い方（主要コマンド）
--------------------
基本的にパッケージをモジュール実行します。プロジェクトルート（pyproject.toml がある場所）で実行してください。

1. ExecutionEngine（発注エンジン）起動
   - 本番または開発環境で: KABUSYS_ENV を適切に設定してから起動
   - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
   - 実行中に停止させたい場合は data/stop_requested.flag（または Kill Switch で生成される data/kill.flag）を作成すると停止シグナルとして検知します。

2. Monitoring（監視）起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
     - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は本番 sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず本番監視 DB を使用）。

3. 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config [--strict]

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH もしくは data/paper_trading.db

6. AI / 研究機能（プログラム API）
   - news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と対象日を渡すと ai_scores テーブルへ書き込む
   - regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB 接続と対象日を渡すと market_regime テーブルへ書き込む
   - これらはライブラリ関数として呼び出して利用する想定です。OpenAI API を利用する場合は OPENAI_API_KEY の設定が必要です。

運用関連（フラグ・PID・ログ）
- stop フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring が監視している停止フラグ（プロジェクトルートの data/ 配下）
- kill フラグ:
  - data/kill.flag — KillSwitch により書き込まれる実行停止指示ファイル（ExecutionEngine 側で参照）
- PID ファイル:
  - data/execution.pid（Settings.pid_file_path デフォルト）など、プロセス識別用に使用
- ログ:
  - デフォルトは logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、30 日保管）
  - setup_logging を通じて統一管理（コンソールは stdout 出力）

注意事項 / ベストプラクティス
- .env は絶対にリポジトリへコミットしないでください。
- KABUSYS_ENV=live を使うと本番動作（実発注）になります。十分に検証してから使用してください。
- PAPER_FILL_MODE などのペーパートレード設定で発注挙動（即時約定/部分約定/未約定/拒否）を制御できます。
- OpenAI を利用する機能は API レスポンスの不確実性に対応する仕組み（リトライ、フォールバック）を持ちますが、API キーや料金、レイテンシに注意してください。
- validate_config を運用開始前に実行し、設定漏れや YAML ファイルの構文エラーを確認してください。

ディレクトリ構成
----------------
以下は主要パッケージ・モジュールの概観（src/kabusys 配下）です。実際のファイルはリポジトリを参照してください。

- kabusys/
  - __init__.py
  - config.py                — 環境変数読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注履歴・滞留注文監視（実装あり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch（flag 書き込み / 判定）
    - monitoring_engine.py   — 複数モニタを束ねるポーリング機構
    - alert_manager.py       — （通知管理; 実装により LINE 等へ通知）
  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig / run_session など）
    - broker_factory.py      — ブローカクライアント生成（実ブローカ or Mock）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化層
    - reconciler.py          — ブローカ状態/リポジトリ整合処理
    - risk_manager.py        — 発注前リスクチェック
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - position_sizing.py     — 株数決定・丸め・aggregate cap
  - research/
    - factor_research.py     — モメンタム/バリュー/ボラティリティ計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・スコア書込み）
    - regime_detector.py     — レジーム判定（ETF MA + マクロニュース + LLM）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

付録：便利な環境変数（一部）
- KABUSYS_ENV (development|paper_trading|live) — 実行モード
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（整数）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必要）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

最後に
--------
この README はコードベースから読み取れる設計意図・動作方針をまとめたものです。詳細実装や追加のユーティリティ、運用手順は各モジュールの docstring（ソース内コメント）や config/*.yaml、運用マニュアル等を参照してください。質問や特定機能のドキュメント化が必要であれば教えてください。