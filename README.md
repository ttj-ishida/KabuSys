README / ドキュメント (日本語)
=============================

概要
----
KabuSys は日本株向けの自動売買フレームワーク（リサーチ、ポートフォリオ構築、発注実行、監視、AI ニュース解析など）をまとめたコードベースです。本リポジトリは、発注エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ファクター計算 / リサーチ、ポートフォリオ構築ロジック、AI ベースのニュースセンチメント評価などを含みます。

主要な設計方針（抜粋）
- 実運用とペーパートレードを切り替え可能（KABUSYS_ENV）。
- DB は DuckDB（分析用）と SQLite（監視・発注ログ）を使用。
- AI（OpenAI）を用いたニュース解析・レジーム判定は外部 API キー必須。失敗時はフェイルセーフで継続する設計。
- .env による設定管理、対話式ウィザード、事前検証ツールを提供。

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup による .env の作成/更新。
- 設定検証: python -m kabusys.validate_config で環境変数 / config/*.yaml を検査。
- 実行エンジン起動スクリプト: run_execution.py（本番 / ペーパートレード対応）。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）。
- 監視ループ起動スクリプト: run_monitoring.py（監視ログは monitoring DB に書き込み）。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。
- 監視機能:
  - SystemMonitor: CPU / メモリ / ディスク / プロセス死活 / データ鮮度の監視
  - TradeMonitor: 注文滞留（stale order）や約定価格異常の検出
  - RiskMonitor: ドローダウンやポジション上限の判定、ダッシュボードの更新
  - KillSwitch: リスク条件で data/kill.flag を書き込むことで Execution を停止
  - AlertManager（通知管理、アラート発行用フック）
- ポートフォリオ構築:
  - 候補選定、等配分・スコア配分、リスク調整（セクター制限・レジーム乗数）、ポジションサイズ算出（単元株丸め、利用可能現金に対するスケーリング）
- リサーチ / ファクター:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）連携:
  - news_nlp: ニュース記事をバッチで LLM に送信し、銘柄ごとの sentiment / ai_score を ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA200 乖離 + マクロニュースの LLM スコアで市場レジームを判定
- ツール:
  - paper_verification_report: ペーパートレード DB を解析して稼働率・約定率・レイテンシ等のレポートを生成

セットアップ手順
----------------
1. Python 環境を用意
   - 推奨: 仮想環境を作成して有効化（venv / virtualenv / conda）。
     例:
       python -m venv .venv
       source .venv/bin/activate

2. 依存パッケージをインストール
   - 必須（コード内参照）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config/*.yaml のパース検証を行う場合、オプション）
   - 例:
       pip install duckdb psutil openai PyYAML

   ※ requirements.txt はリポジトリに含まれていない場合があります。上記候補をインストールしてください。

3. .env を作成
   - 対話式ウィザード:
       python -m kabusys.config_setup
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI 機能を使う場合:
     - OPENAI_API_KEY を環境変数に設定するか、score_regime / score_news 呼び出しでキーを渡す。

4. 設定検証（推奨）
       python -m kabusys.validate_config
     - 警告も失敗扱いにする:
       python -m kabusys.validate_config --strict

5. データディレクトリの準備（必要に応じて）
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite（monitoring）: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - 実行中に自動作成される箇所もありますが、権限やパスは事前に確認してください。

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード: instant | partial | never | reject（デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒。run_monitoring で参照。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 実行時に kill.flag を自動クリアする (0/1)。本番では 0 推奨。
- PID_FILE_PATH / KILL_FLAG_PATH — PID ファイル / kill.flag のパスを上書き可能

使い方（コマンド例）
--------------------
- 環境設定ウィザード:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視ループ起動:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: run_monitoring は監視用の SQLite（monitoring DB）に本番 sqlite_path を使います（KABUSYS_ENV に関係なく）。

- 実行エンジン起動:
    python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に分離して記録します。
  - エンジンは data/stop_requested.flag や data/kill.flag を監視して停止します。PID ファイル（data/execution.pid など）を利用します。

- Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY が未設定だと ValueError を送出します。

停止 / Kill Switch
-----------------
- KillSwitch 機構により、監視側で条件を満たすと data/kill.flag が書き込まれ、ExecutionEngine に停止シグナルを送る設計です。
- 手動停止や自動停止のために以下のファイルを利用:
  - data/kill.flag — Kill Switch（Execution 停止指示）
  - data/stop_requested.flag — run_monitoring / run_execution 停止用フラグ（起動前・実行中に存在すると起動/継続を中止）
  - data/execution.pid — 実行エンジンの PID 管理

ディレクトリ構成（主要ファイル）
-------------------------------
以下はソースルート src/kabusys の主要なファイル・モジュールです（抜粋）。

- kabusys/
  - __init__.py
  - config.py                 — .env 自動読み込み / Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — 監視ループ起動スクリプト
  - run_execution.py          — 実行エンジン起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI 連携）
    - regime_detector.py       — 市場レジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py         — 通知管理（実装箇所あり）
  - execution/                 — 発注エンジン関連（order_manager 等）
    - (order_manager, order_repository, execution_engine, broker_factory, ...）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - data/                      — データ / パイプライン関連（DuckDB テーブル等）
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・運用の注意点
------------------
- 本番（KABUSYS_ENV=live）では設定と権限、LINE 通知（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を慎重に確認してください。validate_config はライブ環境用の警告を出します。
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- AI（OpenAI）依存機能は API 呼び出しのレートリミットや失敗に配慮して設計されていますが、API キー/料金に注意してください。
- DuckDB / SQLite のファイルパスや権限を適切に設定し、バックアップ・ログ管理を行ってください。
- process_priority.set_process_priority は OS 権限により失敗することがあります（警告ログのみ）。Linux / Windows の差分を吸収する実装です。

トラブルシュート
-----------------
- 設定検証でエラーが出る場合: .env の必須キー（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD）や KABUSYS_ENV の値を確認してください。
- OpenAI 関連でエラーが出る場合: OPENAI_API_KEY の設定、ネットワーク、openai パッケージの互換性を確認してください。
- DuckDB / sqlite の接続エラー: ファイルパスの親ディレクトリの存在・書き込み権限を確認してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ == "0.1.0"（ソース内定義）
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

最後に
------
この README はコードベースのエントリポイントと主要な実行フロー、および設定手順をまとめたものです。詳細実装や追加の設定項目は各モジュールの docstring / ソースコードを参照してください。必要であれば、特定機能（例: ExecutionEngine の設定項目、OrderRepository の DB スキーマ、AlertManager の通知プラグイン方法）について別途ドキュメントを作成します。