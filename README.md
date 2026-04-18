README
=====

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。本リポジトリは以下を含む主要コンポーネント群を提供します。

- ExecutionEngine（発注 / 注文管理 / リスク管理）
- Monitoring（システム稼働監視・アラート・Kill Switch）
- Portfolio Construction（候補選定・重み付け・ポジションサイジング）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメント評価・市場レジーム判定）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート）

本 README はコードベースの使い方・セットアップ手順・ディレクトリ構成をまとめたものです。

主な機能
--------
- 発注エンジン（ExecutionEngine）
  - ブローカークライアント抽象化（実環境とペーパートレードを切替可能）
  - 注文リポジトリ / オーダーマネージャ / リコンシリエーション / リスク管理
- 監視（Monitoring）
  - CPU / メモリ / ディスク使用率監視
  - Execution プロセス死活監視、データ鮮度チェック
  - Trade / Risk の監視と kill.flag による自動停止トリガー
  - ログの永続化（SQLite）とダッシュボードの upsert
- ポートフォリオ構築（純粋関数）
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め・aggregate cap）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン・IC 計算・特徴量サマリ
- AI（OpenAI）
  - ニュース記事を LLM で評価して銘柄ごとのスコアを保存
  - マクロニュース + ETF MA200 乖離で市場レジーム判定
- ツール
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成ツール

セットアップ手順
----------------

前提
- Python 3.10+（型表記に合わせるため推奨）
- システムに sqlite3, duckdb を使える環境

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な外部ライブラリ（主要なもの）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config/*.yaml のパース検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （本リポジトリに requirements.txt があればそれを使用してください。）

4. 環境変数設定（.env）
   - 対話ウィザードを使って .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記「重要な環境変数」を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けるとワーニングも失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. DB 初期化
   - 各起動スクリプトは起動時に必要なテーブルを（冪等に）作成します。
   - DuckDB / SQLite のデータファイルはデフォルトで data/ 配下に作成されます。

重要な環境変数（代表）
---------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: Execution は MockBroker を使用し paper_db に記録
  - live: 実発注モード
- OPENAI_API_KEY — OpenAI（ニュース/レジーム判定）に必要
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト instant）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス（Settings で参照）

使い方（実行例）
----------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBroker が使用され、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に書き込まれます。
    - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします。
    - 停止は stop_requested.flag を作成することでスムーズに停止できます（run_execution がフラグを検知して engine.stop() を呼びます）。

- Monitoring 起動（常駐監視）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL によりポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず production の sqlite_path を使って監視ログを保存します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

ログ
----
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging を各スクリプトが呼び出します。
- デフォルトでは stdout に出力され、ファイルは logs/<app_name>.log に日次ローテーションで保存されます（保持 30 日）。
- LOG_DIR 環境変数で変更できます。

停止／Kill Switch
-----------------
- 手動停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。
- Kill Switch:
  - リスク条件（ドローダウン超過、ポジション上限超過など）を満たすと monitoring が data/kill.flag を書き込み、ExecutionEngine に停止指示を送れる設計です。
  - Settings.KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

ライブラリとしての利用
---------------------
コードベースはライブラリ的にも利用可能です。主要な API:

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

- 研究／ファクター
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

- AI（ニュース）
  - from kabusys.ai import score_news

- 監視 DB 操作
  - from kabusys.monitoring.monitoring_db import MonitoringDB

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話ウィザード CLI
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュースセンチメント評価
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
    - system_monitor.py
    - trade_monitor.py       — （ファイル内で定義、存在）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （アラート送信の抽象化）
  - execution/
    - execution_engine.py
    - broker_factory.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/ (DB/logging/kill switch modules are under this package)

バージョン
---------
- パッケージバージョンは src/kabusys/__init__.py の __version__ で管理（例: "0.1.0"）。

補足・注意点
-----------
- 本番環境（KABUSYS_ENV=live）では設定を慎重に行ってください。validate_config は live 時の追加ワーニングを出します。
- OpenAI を利用する機能は API キーが必要です。API 呼び出し失敗時はフェイルセーフで動作を継続する設計ですが、重要な判定には影響します。
- .env ファイルは機密情報を含むため決してリポジトリにコミットしないでください。
- DuckDB / SQLite のスキーマ変更は init_monitoring_db 等にマイグレーションロジックが含まれていますが、バックアップを推奨します。

問題報告・貢献
--------------
Issue や Pull Request はリポジトリのホスティング先にお願いします。設計上の質問や再現手順がある場合は具体例（ログ・環境変数・実行コマンド）を添えてください。

以上。必要であれば README に記載する .env のテンプレート例や起動スクリプトの詳細なログ出力例などを追加します。どの情報を追加しましょうか？