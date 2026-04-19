README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
このリポジトリには次のような機能が含まれます:

- 発注エンジン（ExecutionEngine）の起動スクリプト
- 監視（Monitoring）ループと監視用 DB 層
- Paper Trading 用検証レポート生成ツール
- ファクター計算・特徴量分析（DuckDB を利用）
- ニュース NLP を使った銘柄ごとのセンチメント算出（OpenAI）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- 簡易 CLI ツール：.env ウィザード / 設定検証

主要な設計方針（一部）
- DuckDB / SQLite をローカル DB として使用（分析用と監視用で分離）
- 環境変数および .env で設定を管理（Settings クラス）
- 実行環境フラグ KABUSYS_ENV により挙動を分離（development / paper_trading / live）
- OpenAI 呼び出しはリトライやバリデーションを行いフェイルセーフで動作

機能一覧
--------
- run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
- run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔制御）
- config_setup.py: .env を対話式に作成・更新するウィザード
- validate_config.py: 環境変数・config/*.yaml の検証 CLI（--strict オプションあり）
- tools/paper_verification_report.py: Paper Trading の検証レポート生成
- portfolio/*: 候補選定・重み計算・リスク調整・ポジションサイジングの純粋関数群
- research/*: ファクター計算（momentum/value/volatility）や特徴量解析ユーティリティ
- ai/news_nlp.py / ai/regime_detector.py: ニュース NLP による銘柄スコア・市場レジーム判定
- monitoring/*: 監視 DB（SQLite）と各種モニタ（SystemMonitor / TradeMonitor / RiskMonitor）、Kill Switch、アラート連携用のまとめ

セットアップ手順
----------------
以下はローカル環境で動かすための一般的な手順例です。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必要な主要ライブラリ: duckdb, psutil, openai, PyYAML（YAML 検証用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env の準備
   - 対話式ウィザードを実行して .env を作成できます:
     - python -m kabusys.config_setup
   - 必須環境変数（最低限設定が必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋とデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: OpenAI を利用する機能で必要
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — run_monitoring で利用

5. データディレクトリ
   - data/ ディレクトリに DB ファイルやフラグファイルが作成されます（logs/ にログ）。
   - run スクリプトは data/stop_requested.flag や data/kill.flag、data/execution.pid 等を使用します。

使い方
------

一般的なエントリポイント（モジュールとして実行）:

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - 本番/開発/ペーパー切り替えは KABUSYS_ENV で制御
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されるとエンジンを停止します
  - Paper Trading（KABUSYS_ENV=paper_trading）の場合:
    - MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
    - PAPER_FILL_MODE 環境変数で約定モードを指定できます（instant|partial|never|reject）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に使用（環境に依らず監視 DB を共通で参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定できます

注意事項 / 運用上のポイント
- Kill Switch:
  - KillSwitch は監視結果に応じて data/kill.flag を書き込み、ExecutionEngine に停止要求を送ります。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- ロギング:
  - logs/ に日次ローテーションでログを出力します（logs/<app_name>.log）。
  - setup_logging() により StreamHandler (stdout) と TimedRotatingFileHandler を設定します。

- OpenAI の利用:
  - ai/news_nlp.py や ai/regime_detector.py は OpenAI API を呼び出します。環境変数 OPENAI_API_KEY を設定してください。
  - 呼び出しはリトライやレスポンス検証を行いますが、API キー未設定時はエラーになります。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db() はテーブルの作成および一部カラムの追加（マイグレーション）を行います（冪等）。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- OPENAI_API_KEY (AI 機能で必要)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒)
- PAPER_FILL_MODE (paper_trading 時の約定挙動: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (0/1)

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・Settings 管理（.env 自動ロード含む）
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- ai/
  - news_nlp.py            — ニュースを OpenAI でスコアリングして ai_scores へ書き込み
  - regime_detector.py     — マクロ + MA から市場レジーム判定

- monitoring/
  - monitoring_db.py       — SQLite ベースの監視ログ永続化層
  - system_monitor.py      — システム状態 / データ鮮度監視
  - trade_monitor.py       — 発注ログ監視（stale / anomaly 検出）  ← 実装ファイル参照
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — flag ファイル操作による停止制御
  - monitoring_engine.py   — 各 Monitor をまとめる

- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 発注株数計算・集計キャップ処理
  - risk_adjustment.py     — セクター上限・レジーム乗数

- research/
  - factor_research.py     — momentum / value / volatility のファクター計算
  - feature_exploration.py — forward returns, IC, 統計サマリ等

- monitoring/ (上に同じ)
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート

- utils/
  - logging_setup.py       — ログ設定ユーティリティ（Stream + 日次ファイル）
  - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ

付録: よくある実行コマンド例
--------------------------
- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

サポート / 拡張
----------------
- DuckDB にロードする market/price/financials テーブル定義やデータロードは外部スクリプトを想定しています（prices_daily / raw_financials / raw_news などを前提）。
- 発注ブローカ実装（BrokerClientFactory）や ExecutionEngine の詳細は別モジュールに分かれており、本 README はリポジトリ内の主要ユーティリティと実行方法をまとめたものです。
- テスト時には OpenAI 呼び出し等をモック化することを想定しています（各モジュールはテスト時に差し替え可能な設計）。

問題・バグ報告
--------------
バグや改善提案は issue を立ててください。実行時のログ（logs/ の該当ファイル）と .env の主要設定（シークレットを除く）を添付すると診断が早くなります。