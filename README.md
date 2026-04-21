KabuSys
=======

日本株向け自動売買システムの Python パッケージ。本リポジトリは取引実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）や AI ベースのニュースセンチメント評価などのコンポーネントを含むモジュール群で構成されています。

主な特長
-------
- ExecutionEngine：発注ロジック、注文管理、リスク管理、約定再整合を含む取引実行基盤
- Monitoring：システム状態／注文ログ／リスクを監視してアラート送出や Kill Switch を発動
- Portfolio construction：銘柄選定、重み計算、ポジションサイジング（純粋関数実装）
- Research：DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ツール
- AI モジュール：ニュース NLP による銘柄センチメント評価、レジーム判定（OpenAI を利用）
- 開発支援スクリプト：.env 用ウィザード、設定検証ツール、Paper Trading 検証レポート生成

機能一覧
-------
- 起動スクリプト
  - python -m kabusys.run_execution : ExecutionEngine を起動（KABUSYS_ENV により paper/live 振る舞い切替）
  - python -m kabusys.run_monitoring : SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 環境設定 / 検証
  - python -m kabusys.config_setup : .env 作成・更新の対話ウィザード
  - python -m kabusys.validate_config : .env と config/*.yaml の事前検証（--strict あり）
- ツール
  - python -m kabusys.tools.paper_verification_report : Paper Trading DB を基に検証レポートを出力
- Portfolio コンポーネント（純関数）
  - 銘柄候補選定、等配分／スコア配分、セクター制約、レジーム乗数、ポジションサイズ計算
- Research
  - DuckDB 接続を受けてモメンタム・ボラティリティ・バリュー等を計算
  - 将来リターン・IC（Information Coefficient）・統計サマリ
- AI
  - News NLP（OpenAI）で記事を集約・センチメントを算出し ai_scores に書き込み
  - Regime Detector：ETF の MA 乖離 + マクロニュースで市場レジーム判定
- ログ & プロセス管理
  - 共通のログ初期化ユーティリティ（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- 永続化
  - SQLite（監視用）と DuckDB（分析用）を使用
  - monitoring_db モジュールでテーブル作成・永続化操作を提供

セットアップ手順
--------------
1. Python 環境を用意
   - Python 3.9+ を推奨
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要パッケージをインストール
   - 本コードで想定される主要依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル YAML 検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートで .env を用意
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは .env.example（存在する場合）を参考に作成
   - 自動ロード:
     - config モジュールはプロジェクトルートに .env / .env.local を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）

4. データディレクトリ作成（必要に応じて）
   - デフォルト DB/ファイル:
     - data/kabusys.duckdb（DuckDB）
     - data/monitoring.db（SQLite 監視 DB）
     - data/paper_trading.db（Paper Trading 用 SQLite）
     - logs/（ログ）
   - これらは環境変数で上書き可能（下記参照）

主要な環境変数
---------------
- KABUSYS_ENV: 実行環境
  - development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: monitoring SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

使い方（主なコマンド）
---------------------
- .env の作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 本番 / ペーパーの切替は KABUSYS_ENV 環境変数で指定
  - 例（ローカル起動、ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - ExecutionEngine は paper_trading の場合 MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）

- 監視ループ起動
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は常に本番 sqlite_path を参照（環境にかかわらず）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（スクリプト経由またはプログラムから利用）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - news_nlp.score_news / regime_detector.score_regime を使用して ai_scores / market_regime テーブルに書き込み

運用上のファイル / フラグ
-------------------------
- data/stop_requested.flag : run_monitoring / run_execution の停止検出用フラグ（存在するとプロセスは停止動作）
- data/kill.flag : KillSwitch が書き込む停止フラグ（ExecutionEngine 停止シグナル）
- data/execution.pid : ExecutionEngine の PID ファイル（プロセス管理用）
- logs/<app_name>.log : 日次ローテートで出力されるログ

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 配下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト

  - execution/                 — 発注関連（Engine, BrokerFactory, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル作成・CRUD ヘルパ）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視（コード参照）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — Kill Switch 制御
    - monitoring_engine.py    — 各 Monitor を束ねる
    - alert_manager.py        — （アラート送信：LINE 等の実装）
  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 発注株数計算、aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI 呼び出し、結果整形）
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - utils/
    - logging_setup.py        — ルートロガー初期化（stdout + ローテートファイル）
    - process_priority.py     — プロセス優先度・CPU affinity ユーティリティ

補足・注意点
------------
- .env は機微情報を含むため絶対に Git にコミットしないでください（config_setup の出力にも警告コメントあり）。
- OpenAI を使う処理は API キーが必要です。利用時はコスト・レート制限に注意してください（リトライ・バックオフ実装あり）。
- DuckDB / SQLite ファイルはデフォルトで data/ に置かれます。運用時は適切な永続ストレージ（バックアップ）を用意してください。
- monitoring の DB 操作は冪等性（マイグレーション含む）を考慮していますが、プロダクション移行時は事前にバックアップを行ってください。
- run_execution の本番起動時は KABUSYS_ENV=live に設定してください。live ではペーパートレード DB とは分離されます。

ライセンス・バージョン
-----------------------
- パッケージバージョン: __version__ = "0.1.0"（kabusys.__init__）
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

これで基本的な README が整いました。追加で
- requirements.txt / poetry/pyproject.toml の整備
- デプロイ/サービス化（systemd / Docker / Kubernetes）手順
- CI 用のテスト・Lint 指針
が必要であれば、その内容に合わせて README を拡張します。どの情報を追加しますか？