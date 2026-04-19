README
======

概要
----
KabuSys は日本株自動売買（およびその開発支援）を目的とした Python パッケージです。
主要機能は次の通りです。

- 注文実行エンジン（ExecutionEngine）: 本番/ペーパートレード両対応
- 監視サブシステム（Monitoring）: システム状態・注文・リスク監視、Kill Switch
- ポートフォリオ構築ロジック: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- リサーチツール: ファクター計算、特徴量解析
- AI 支援モジュール: ニュースセンチメント（OpenAI 経由）、市場レジーム判定
- 運用ユーティリティ: .env ウィザード・設定検証・ペーパートレード検証レポート

主な設計方針
- 本番とペーパートレードはデータベースやブローカークライアントで分離
- ルックアヘッドバイアスを避ける（日次処理で datetime.today() を参照しない設計）
- フェイルセーフ: 外部 API 失敗時は安全なフォールバックで処理を継続

機能一覧
--------
- config_setup: 対話式に .env を生成 / 更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env と config/*.yaml の基本検証（python -m kabusys.validate_config）
- run_execution: ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV により paper_trading 時は MockBrokerClient を使用し data/paper_trading.db に記録
- run_monitoring: SystemMonitor ポーリング起動（python -m kabusys.run_monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔上書き可（デフォルト 60 秒）
- monitoring: System/Trade/Risk モニタ、KillSwitch、AlertManager 連携
- portfolio: 候補選定 / 重み計算 / ポジションサイズ計算 / セクター制限 / レジーム乗数
- research: ファクター計算（momentum/value/volatility）、IC/統計サマリーなど
- ai:
  - news_nlp.score_news: OpenAI を使ったニュースセンチメント集約・ai_scores へ保存
  - regime_detector.score_regime: MA + マクロニュース（LLM）で市場レジーム判定
- tools.paper_verification_report: ペーパートレードの検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.9+（プロジェクトで必要なバージョンに合わせてください）
- system 依存: sqlite3 は標準、DuckDB、psutil、openai などの Python パッケージが必要

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（requirements.txt がある場合はそれを利用）
   例（必要に応じて適宜追加してください）:
   - pip install duckdb psutil openai pyyaml

3. 初期環境変数ファイル（.env）を作成
   - python -m kabusys.config_setup
     対話式にキーを入力して .env を生成できます。

4. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit code 1）になります。

5. 必要ディレクトリの作成
   - data/ （SQLite/ロック/flag を置く）
   - logs/ （ログファイル）

主要な環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 任意 / 推奨
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレードでの約定挙動（instant/partial/never/reject、デフォルト: instant）
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI モジュールを使う場合）
  - LOG_LEVEL / LOG_DIR — ログ出力設定
  - KILL_FLAG_CLEAR_ON_START — 実行時に kill.flag を自動クリアするか（開発用）

使い方
------
1) 設定の作成・検証
- .env を作成
  - python -m kabusys.config_setup
- 検証
  - python -m kabusys.validate_config
  - 例: python -m kabusys.validate_config --strict

2) ExecutionEngine 起動（取引セッション）
- 本番またはペーパートレードを設定して起動
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - デフォルトでは paper_trading 時は設定された paper_sqlite_path（data/paper_trading.db）を使用します。
- 停止方法:
  - run_execution はデーモンスレッドで実行後ループしつつ data/stop_requested.flag の存在を監視します。
  - 手動停止（即時）: data/stop_requested.flag を作成するとスクリプトが検知して停止します。
  - 監視サブシステムからの停止: monitoring が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ書き込み、ExecutionEngine 側がこれを検出して停止します。

3) Monitoring 起動
- python -m kabusys.run_monitoring
- ポーリング間隔は環境変数で調整可能
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は常に「本番の sqlite_path」を参照して監視ログを永続化します（KABUSYS_ENV に依存せず）。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  - --db で DB パスを指定（優先）
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能

5) AI モジュール（ニューススコア・レジーム判定）
- OpenAI API キーが必須（環境変数 OPENAI_API_KEY または関数引数）
- news_nlp.score_news / regime_detector.score_regime を DuckDB 接続と target_date を渡して呼び出す
  - 例（スクリプトやスケジューラ内で）:
    - from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key=None)

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルトログディレクトリ: logs/
- ログファイル名はアプリ名プレフィックス（例: execution.log / monitoring.log）
- LOG_LEVEL, LOG_DIR 環境変数で調整可能

ディレクトリ構成（抜粋）
---------------------
リポジトリの主要ファイル・ディレクトリ（src/kabusys 以下を中心に示す）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite の永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
    - system_monitor.py       — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py        — （注文滞留や約定異常の検出）※実装参照
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 複数モニタを束ねるエンジン
    - kill_switch.py          — kill.flag の書き込み/管理
    - alert_manager.py        — （通知送信）※実装参照
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py              — DuckDB / prices データ操作（使用例）
    - stats.py                 — zscore_normalize 等ユーティリティ
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - logs/                     — ログ出力（実行時に作成）
  - data/                     — DB / flag / pid ファイル（実行時に作成）

補足 / 運用上の注意
------------------
- .env は機密情報を含むため絶対に Git にコミットしないでください（config_setup の注釈にも明記）。
- 本番環境（KABUSYS_ENV=live）では設定を慎重に確認してください（validate_config が注意喚起します）。
- OpenAI を使う処理は API コールに失敗した場合にフォールバックして動作するよう設計されていますが、API キーの使用料やレート制限に注意してください。
- run_monitoring / run_execution は stop フラグ（data/stop_requested.flag）や kill.flag により外部から安全に停止できます。デプロイ時はこれらのファイルの管理方法を確立してください。

さらに詳しい情報
----------------
コード内の docstring や各モジュールのコメントに設計思想・仕様が詳述されています。
実装を拡張する際は該当ファイルのトップコメント（特に AI 系・ポートフォリオ設計の注記）を参照してください。

---
この README はリポジトリ内のソースコードを元に自動生成的にまとめた概要です。具体的な導入手順や追加依存はプロジェクトの requirements や運用ドキュメントに従ってください。