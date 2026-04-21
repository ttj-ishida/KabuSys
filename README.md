README
======

プロジェクト概要
----------------
KabuSys は日本株の自動売買・調査・監視を目的とした軽量なフレームワークです。このリポジトリには以下の主要機能を持つコンポーネントが含まれます。

- 発注実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/liveの切替対応）
- 監視モジュール（System / Trade / Risk）のポーリングとアラート連携、Kill Switch
- ポートフォリオ構築（候補選定・配分・ポジションサイジング・セクター制約）
- リサーチモジュール（ファクター計算、特徴量探索、将来リターン、IC計算）
- AI 支援モジュール（ニュースの NLP スコアリング、レジーム検出：OpenAI API 利用）
- ユーティリティ（設定読み込み、ログ設定、プロセス優先度設定 等）
- 運用支援ツール（.env ウィザード、設定検証、ペーパー検証レポート作成）

機能一覧
--------
主な機能（抜粋）:

- 実行（run_execution.py）
  - KABUSYS_ENV に応じて paper_trading（モックブローカー） / live（実ブローカー）を切替
  - paper_trading の場合、data/paper_trading.db を使用して本番 DB と分離
  - プロセス優先度設定、PID ファイル管理、停止フラグ監視

- 監視（run_monitoring.py / monitoring パッケージ）
  - 定期ポーリングでシステム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ等を記録
  - RiskMonitor によるドローダウン・ポジション上限検出
  - KillSwitch による処理停止（data/kill.flag 書込み）
  - アラート発行（AlertManager 経由：実装によりLINE等に通知）

- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定（スコア降順）
  - 等金額・スコア加重配分
  - リスクベースなポジションサイズ計算（単元株丸め、aggregate cap調整）
  - セクター集中制限・レジーム乗数反映

- リサーチ（research パッケージ）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily 等を参照）
  - 将来リターン計算、IC（スピアマン順位相関）計算、統計サマリ

- AI 関連（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースセンチメント集約 → ai_scores テーブルへ書込み
  - regime_detector: ETF (1321) の MA とマクロニュースで市場レジーム判定（market_regime に保存）
  - OpenAI 呼び出しは安全なリトライ・バリデーションあり

- 運用ツール
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

セットアップ手順
----------------

1. 前提
   - Python 3.9+（プロジェクトの要件に合わせて調整）
   - 必要 Python パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証を行う場合）
   - SQLite は標準ライブラリで利用可能

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザード実行:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成しプロジェクトルートに配置
   - 自動読み込み: Settings モジュールはデフォルトでプロジェクトルートの .env を読み込みます。
     - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告を FAIL として扱うには --strict を付与

6. データディレクトリ
   - デフォルトで data/、logs/ を使用します。必要であれば環境変数でパスを上書きしてください。

使い方
------

基本的な実行例（プロジェクトルートで実行）:

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録します（本番 DB と分離）
    - 起動前に data/stop_requested.flag が存在すると起動を中止します
    - PID ファイルは data/execution.pid（Settings.pid_file_path）に作成されます

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照します（Settings.sqlite_path）。Paper 環境でも監視 DB は本番 DB を使用

- 停止方法
  - 実行を停止するには:
    - 実行中プロセスに KeyboardInterrupt（Ctrl-C）
    - data/stop_requested.flag を作成すると、run_monitoring/run_execution は検知して順次終了します
  - Kill Switch:
    - monitoring 内の条件（ドローダウン等）で KillSwitch がトリガーされると data/kill.flag を書き込み、Execution を停止させます
    - KillSwitch は冪等に振る舞います（既に存在する場合は上書きしない）

- ペーパー検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）

- AI スコアリング / レジーム判定（ライブラリ関数として利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - api_key が None の場合 OPENAI_API_KEY 環境変数を参照
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OpenAI API キーが必要（環境変数 OPENAI_API_KEY）

設定（主な環境変数）
-------------------

必須（少なくとも実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード

主要オプション（デフォルトあり）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — モックブローカーの約定モード（instant|partial|never|reject）

注意点:
- .env ファイルはリポジトリにコミットしないでください（config_setup のヘッダにも明記）
- Settings クラスは .env を自動読み込みします（プロジェクトルートから探索）。自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ログ
----
- ログは stdout と logs/<app_name>.log（TimedRotatingFileHandler 日次ローテーション、30 日保持）に出力されます
- app_name は起動スクリプトで設定（例: "execution", "monitoring"）
- ログ出力ディレクトリは環境変数 LOG_DIR で上書き可能

ディレクトリ構成
----------------

以下は主要ファイル/パッケージの抜粋構成（src/kabusys 以下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数／設定取得ロジック（Settings クラス）
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

    - monitoring/
      - monitoring_db.py        — SQLite 永続化層（system_status / trade_logs / ...）
      - system_monitor.py       — システム状態 / データ鮮度チェック
      - trade_monitor.py        — （発注ログ監視等）※実装ファイルはプロジェクト内にある想定
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — kill.flag 書込みユーティリティ
      - monitoring_engine.py    — 各モニタを束ねる実行ループ

    - execution/
      - execution_engine.py     — ExecutionEngine（本体; 参照あり）
      - broker_factory.py       — BrokerClientFactory（モック／実ブローカー切替）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py

    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py

    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py

    - ai/
      - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py      — 市場レジーム判定（OpenAI）
      - __init__.py

    - tools/
      - paper_verification_report.py
      - __init__.py

    - monitoring/ (DB 層、リスク監視等は上記)
    - data/                     — 実行時に使用する DB / フラグ / PID 等（デフォルト）
    - logs/                     — ログ出力先（デフォルト）

付記（運用・開発メモ）
--------------------
- 各種 DB（DuckDB/SQLite）はデフォルトで data/ 以下に保存されます。運用環境では永続ディレクトリをマウント/指定してください。
- run_execution は起動時に Kill Flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を持ちます。Live 環境ではデフォルトでクリアしない設定を推奨します。
- OpenAI を使う機能は API 呼び出しに失敗した場合フォールバック（0 相当）や部分失敗保護を行う設計です。API キーやコストには注意してください。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリに追加してください（ここには含まれていません）。

---

以上が本リポジトリの概要と基本的な使い方です。必要に応じて README に実行例、docker-compose 設定、詳しい API ドキュメントなどを追加できます。ご希望があれば追記します。