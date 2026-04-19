README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python 製の小規模フレームワークです。  
このコードベースは以下の主要領域を含みます:

- 注文実行エンジン（ExecutionEngine）とブローカークライアントの抽象化（paper/live の切替対応）
- 監視モジュール（System / Trade / Risk）と Kill Switch（条件に応じたエンジン停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・セクター制限）
- リサーチ（ファクター計算、将来リターン、IC 計算、特徴量解析）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定（OpenAI API））
- ツール（ペーパートレード検証レポート生成など）
- 小物ユーティリティ（ログ設定、プロセス優先度設定、環境変数ロード等）

主な機能一覧
--------------
- Execution の起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading DB（data/paper_trading.db）へ記録して本番 DB と完全分離。
  - 起動時にプロセス優先度を "high" に設定、停止フラグにより安全に停止可能。
- Monitoring の起動スクリプト（run_monitoring.py）
  - システム監視ポーリングループ。環境変数 MONITOR_POLL_INTERVAL で間隔を変更可能（デフォルト 60 秒）。
  - SQLite（監視ログ）と DuckDB（分析用）へ接続。
- 設定ウィザード（config_setup.py）
  - 対話式で .env を作成・更新。
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本的な検証を実行（--strict で警告も失敗扱いに）。
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL を判定。
- 監視サブシステム
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard のテーブル定義と永続化ロジック
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager（アラート処理は AlertManager 経由）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重、リスクベースのサイズ算出、セクターキャップ、レジーム乗数
- リサーチ（kabusys.research）
  - モメンタム、ボラティリティ、バリューのファクター算出、将来リターン、IC、統計サマリ
- AI（kabusys.ai）
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む（OpenAI API 使用）
  - regime_detector: MA とマクロニュースセンチメントを合成して market_regime を算出

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈や構文で 3.10+ を想定）
- SQLite は標準ライブラリで利用可能
- DuckDB, psutil, openai 等は pip インストールが必要

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 依存パッケージをインストール
   - 必須（主な例）:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証など）:
     - PyYAML
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を実行してください）

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（下に最小例を示します）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env や config/*.yaml を修正

6. データディレクトリの準備（logs, data 等）
   - デフォルトは data/ と logs/ を使用します。必要に応じて作成:
     - mkdir -p data logs

基本的な .env の例
------------------
（config_setup を使うことを推奨しますが、手動で作る場合の最小例）

JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
# OpenAI を使う場合
OPENAI_API_KEY=sk-xxxx

使い方（主要コマンド）
--------------------

- Execution（エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - Settings.env によって paper_trading / live / development を切り替え
    - paper_trading の場合は paper 用 SQLite（PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）を使用
    - 起動時に data/stop_requested.flag が立っていると起動せず終了します
    - 停止は data/stop_requested.flag を作成（監視 / 外部からの停止指示）することで安全に行えます

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使います（環境にかかわらず）
  - 停止は data/stop_requested.flag を作成

- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD, --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルトを上書き）

- AI 関連（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数呼び出しで api_key を渡す）
  - 例（モジュール関数の直接呼び出し）:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

停止・フラグ運用
----------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py はこのファイルを検知するとループを抜けて終了します。外部からの安全な停止に使用。
- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込むファイル。ExecutionEngine に対する停止シグナルとして用いられます。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアします（本番では推奨しません）。

ログ
----
- 共通のログ設定ユーティリティである kabusys.utils.logging_setup.setup_logging を使用します。
- デフォルトは logs/ ディレクトリに日次ローテートでログファイルを保存し、同時に stdout にも出力します。
- LOG_LEVEL 環境変数でログレベルを制御可能（例: DEBUG / INFO / WARNING / ERROR / CRITICAL）

注意事項 / 運用上のポイント
--------------------------
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれか。live は本番なので慎重に。
- Paper trading は本番 DB と分離され、data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）を使うように設計されています。
- OpenAI を使う機能は API 呼び出しに失敗してもフェイルセーフ（多くの場面で 0.0 をフォールバック）で継続するようになっていますが、API キーの管理とコストは注意してください。
- DuckDB を分析用に用いており、大量データの高速集計に適しています。
- 一部機能（config/*.yaml の検証）は PyYAML が無い場合はスキップされます。事前にpipでインストールすることを推奨します。

ディレクトリ構成
-----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポートツール
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化 + 永続化層
    - monitoring_engine.py   — Monitors を束ねるループ
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - kill_switch.py         — kill.flag の作成・管理
    - ...（trade_monitor, alert_manager 等 想定）
  - execution/               — ExecutionEngine 関連（ブローカー・注文管理・リスク等）
  - portfolio/               — ポートフォリオ構築（builder / position_sizing / risk_adjustment）
  - research/                — ファクター計算・特徴量探索（DuckDB ベース）
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）での銘柄センチメント算出
    - regime_detector.py     — マーケットレジーム判定（MA + マクロニュース）
  - data/                    — データ IO / pipeline（DuckDB テーブル等。prices_daily 等を想定）
  - ... その他モジュール

付録：よく使うコマンドまとめ
----------------------------
- .env の作成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
-----------------
バグ報告や機能追加の提案は issue を立ててください。開発に参加する場合はまず config_setup / validate_config で環境を整え、ローカルで Execution（paper_trading）と Monitoring を動かして動作確認してください。

以上。必要であれば README にサンプル .env.example、requirements.txt、起動・デバッグ手順（デバッガー attach やログの詳細設定）を追加できます。どの情報を追加したいか教えてください。