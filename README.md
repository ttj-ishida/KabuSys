KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買（シグナル生成・ポートフォリオ構築・発注・監視・研究）を想定した内部ライブラリ群と起動スクリプトをまとめたものです。ここにあるコードはシステムのコア機能（リサーチ、ポートフォリオ構築、発注エンジン、監視、AI を用いたニュース解析など）を提供します。

以下はこのコードベースの README（日本語）です。

プロジェクト概要
----------------
- KabuSys は日本株を対象とした自動売買システムのコンポーネント群です。
- 主な機能はシグナル（ファクター）計算、ポートフォリオ構築、ポジションサイズ決定、発注エンジン（ExecutionEngine 想定）、監視（Monitoring）、Paper Trading 検証レポート生成、AI を使ったニュース評価・レジーム判定など。
- 設定は .env（または環境変数）で管理し、SQLite / DuckDB をローカル DB として使用します。
- 実行スクリプトはモジュールとして提供され、python -m kabusys.<module> で起動できます。

主な機能一覧
-------------
- 環境設定・検証
  - config_setup.py: 対話式で .env を作成・更新するウィザード
  - validate_config.py: .env と config/*.yaml の基本チェック（--strict あり）
- 起動スクリプト
  - run_execution.py: ExecutionEngine（発注エンジン）起動スクリプト（Paper Trading は専用 DB に分離）
  - run_monitoring.py: SystemMonitor をポーリングする監視ループ起動スクリプト
- 監視（monitoring）
  - monitoring_db.py: 監視用 SQLite テーブル初期化 & 永続化 API
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py: 各種監視ロジックとアラート連携
  - kill_switch.py: 条件により data/kill.flag を書き込み ExecutionEngine を停止する仕組み
- 発注周り（execution）
  - ExecutionEngine / OrderManager / RiskManager / Reconciler 等（エンジン本体は別ファイルで実装）
  - BrokerClientFactory による実際の / モックブローカー選択（KABUSYS_ENV による分離）
- ポートフォリオ構築（portfolio）
  - portfolio_builder: 候補選定 & 重み計算（等配分・スコア加重）
  - position_sizing: 発注株数決定（リスクベースや等分配）
  - risk_adjustment: セクター制限・レジーム乗数の適用
- リサーチ（research）
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
  - feature_exploration: 将来リターン計算、IC（情報係数）等の統計ツール
- AI 支援（ai）
  - news_nlp.py: OpenAI を用いたニュースの銘柄別センチメント評価（ai_scores 書き込み）
  - regime_detector.py: ETF の MA やマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等の集計）

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を準備
   - 仮想環境の作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 主に外部依存は以下（プロジェクトに requirements.txt があればそちらを使用してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config の YAML チェックに使用される。必須ではない）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動し .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example（存在する場合）を参考に .env を手動作成
   - .env に最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live） — デフォルト development
     - OPENAI_API_KEY（AI 機能を使う場合）
     - その他: DUCKDB_PATH, SQLITE_PATH など（デフォルトが設定済み）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 本番前は --strict モードで警告も FAIL 扱いにする:
     - python -m kabusys.validate_config --strict

5. データディレクトリとログディレクトリ
   - デフォルトの DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/<app_name>.log（setup_logging による日次ローテーション）
   - 必要に応じて .env で上書きしてください。

使い方（主要なコマンド）
-----------------------

1. 環境ウィザード
   - python -m kabusys.config_setup
     - .env を対話式に作成・更新します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告でも exit 1 になります。

3. ExecutionEngine の起動
   - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB に記録されます（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在すると起動を拒否します。
     - 実行中は data/execution.pid に PID を書き込み、停止時に削除されます。
     - kill.flag による停止（Kill Switch）が有効です（monitoring が条件評価して書き込む）。

4. Monitoring の起動
   - python -m kabusys.run_monitoring
   - 特記事項:
     - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
       - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - 監視は Settings から指定された sqlite_path（監視 DB）と duckdb_path を使用します。
     - data/stop_requested.flag が存在すると監視ループを終了します。
     - 監視は SystemMonitor / TradeMonitor / RiskMonitor を呼び、KillSwitch の判定や AlertManager 通知を行います。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

6. AI 関連（ニューススコア・レジーム判定）
   - news_nlp.score_news / regime_detector.score_regime を直接呼び出して利用可能（DuckDB 接続を渡す）
   - これらは OpenAI API キー（OPENAI_API_KEY）を使用します。API キー未設定時は例外になります。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境。development|paper_trading|live（デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の fill モード（instant | partial | never | reject）

停止・Kill Switch
-----------------
- KillSwitch（監視コンポーネント）が条件（例: 大きなドローダウン、ポジション上限超過）を検出すると data/kill.flag を作成します。ExecutionEngine はこの旗を検知して安全に停止します。
- 管理者が即時停止したい場合は data/stop_requested.flag を作成すると run_monitoring/run_execution のループが終了します（運用上のフラグファイル）。これらは data/ に置かれます。

ログ
----
- setup_logging により、コンソール（stdout）と logs/<app_name>.log（日次ローテーション、30 日保持）に出力します。
- ログディレクトリが作成できない場合はファイル出力はスキップされ、コンソールのみになります。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下のおおまかな構成と各ファイルの概要です（抜粋）。

- src/kabusys/
  - __init__.py        — パッケージ定義、__version__
  - config.py          — 環境変数読み込み・Settings クラス（.env 自動ロード機能）
  - config_setup.py    — .env を対話式に作るウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py   — ExecutionEngine 起動スクリプト
  - run_monitoring.py  — SystemMonitor ポーリング起動スクリプト

  - execution/         — 発注エンジン関連（BrokerFactory, Engine, OrderManager, RiskManager など）
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite の初期化・永続化 API
    - system_monitor.py     — CPU/MEM/DISK・データ鮮度・プロセス監視
    - trade_monitor.py      — 発注ログの監視（滞留注文・約定異常など）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag の作成・管理
    - monitoring_engine.py  — 各 Monitor を束ねてポーリングするエンジン
    - alert_manager.py      — (アラート通知の実装想定)
  - portfolio/
    - portfolio_builder.py  — 候補選定・スコア順ソート
    - position_sizing.py    — 発注株数計算・aggregate cap のスケーリング
    - risk_adjustment.py    — セクター制限・レジーム乗数
  - research/
    - factor_research.py    — 各種ファクター計算（DuckDB）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py           — OpenAI を使ったニュースの銘柄別スコアリング
    - regime_detector.py    — マクロ＋ETF MA による市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
    - ... その他ユーティリティ

設計上の注意点・運用メモ
-----------------------
- .env は絶対にリポジトリにコミットしないでください（機密情報を含みます）。
- KABUSYS_ENV=live の場合は取り扱いに十分注意してください。validate_config は本番向けのガード（LINE 通知設定や kill_flag_clear_on_start の確認）を行います。
- AI (OpenAI) の呼び出しは外部 API を利用するため、呼び出し失敗時にシステムが安全に続行する（フェイルセーフ）設計になっていますが、API キーとコスト制御は必須です。
- DuckDB / SQLite のファイルパスは .env で変更できます。運用でのバックアップや永続化ポリシーを検討してください。
- run_monitoring / run_execution の停止は stop_requested.flag と kill.flag を通じて行われます。運用スクリプトや CI/CD でフラグ取り扱いを管理してください。
- プロセス優先度や CPU affinity は utils/process_priority.py で抽象化されています。プラットフォーム差異（Windows / POSIX）を吸収しますが、権限がない環境では警告を出してスキップします。

よく使うコマンドまとめ
--------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

付記（依存関係）
----------------
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, os, time, math など
- 外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（任意：validate_config の YAML 検査）
- 実行環境によってはネットワークや API キーの設定が必要です（kabuステーション API、J-Quants、OpenAI など）。

ライセンス・貢献
----------------
- この README ではライセンス設定は記載しません。実際のリポジトリでは LICENSE を追加してください。
- 貢献やバグ報告は Pull Request / Issue を通じて行ってください。

---

必要であれば README に以下の追加情報を追記できます（希望があれば教えてください）:
- 具体的な requirements.txt（バージョン指定）
- systemd / supervisor 用のサービスユニット例
- データベーススキーマやサンプルデータの導入手順
- API（関数）リファレンス（モジュール別の詳しい説明）