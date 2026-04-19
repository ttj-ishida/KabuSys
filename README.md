README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング用の小規模フレームワークです。本リポジトリは次の機能群を持ちます:

- ExecutionEngine：発注・リスク・オーダー管理（本番 / ペーパートレード対応）
- Monitoring：システム稼働状態・注文ログ・リスク監視・Kill Switch
- Portfolio 構築ユーティリティ（候補選定・重み付け・ポジションサイジング）
- Research：ファクター計算・特徴量探索（DuckDB ベース）
- AI モジュール：ニュースセンチメントや市場レジーム判定（OpenAI）
- ツール群：ペーパートレード検証レポート生成、設定ウィザード、設定検証 CLI 等

主な設計方針:
- 環境変数で設定を制御し .env をサポート（自動ロード機能あり）
- DuckDB / SQLite をデータストアとして使用（分析用と監視用を分離）
- 本番とペーパートレードを明確に分離（DB 等）
- ログはコンソール + 日次ローテーションファイルで出力

機能一覧
-------
- 実行（Execution）
  - BrokerClientFactory によるブローカー切替（実口座 / モック）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine
  - PID ファイル、停止フラグによる制御

- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 注文滞留・約定異常など（trade_logs を集計）
  - RiskMonitor: ドローダウン・ポジション数制限の監視、ダッシュボード更新
  - KillSwitch: しきい値超過時に data/kill.flag を生成して ExecutionEngine を停止
  - MonitoringEngine: これらをまとめて定周期ポーリング（run_monitoring.py）

- ポートフォリオ構築
  - 候補選定（スコア降順）
  - 等金額・スコア加重重み計算
  - セクターキャップの適用、レジーム乗数
  - ポジションサイズ（リスクベース / equal / score）

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン、IC、統計サマリ（外部依存を最小化）

- AI（OpenAI 統合）
  - news_nlp.score_news: ニュースをまとめて LLM に投げ、銘柄ごとのスコアを ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF とマクロニュースを合成して市場レジーム判定 & 書き込み
  - 再試行・バックオフ・レスポンスバリデーションを実装

- ツール
  - config_setup: 対話式 .env 生成
  - validate_config: 起動前チェック（必須環境変数・ファイル・YAML 構文等）
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
--------------
前提:
- Python 3.9+（実装による）
- 必要な依存パッケージをインストール（例: duckdb, psutil, openai, PyYAML が必要な機能あり）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 依存関係をインストール
   - pip install -r requirements.txt
     （requirements.txt がない場合は少なくとも duckdb, psutil, openai, PyYAML を入れてください）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - KABUSYS_ENV: execution 環境 (development | paper_trading | live)
     - OPENAI_API_KEY: OpenAI を利用する場合は必須
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード時 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
     - KILL_FLAG_CLEAR_ON_START（本番で危険な値: 1 = 起動時に kill.flag を自動クリア）

4. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict を付けて警告もエラー扱いにできます

使い方
-----
- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 動作中に data/stop_requested.flag を作成すると起動済みスレッドに停止シグナルが送られます
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- Monitoring（ポーリング監視）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境にかかわらず本番監視 DB を利用）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いに

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュールの利用（プログラムから）
  - ニューススコア付与:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を省略すると OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ログ
  - setup_logging 関数により console と logs/<app_name>.log（日次ローテーション）へ出力
  - LOG_DIR 環境変数でログ保存先を変更可能

停止・Kill Switch / フラグ
-----------------------
- KillSwitch はリスク条件（ドローダウン超過・ポジション上限超過等）を検出すると data/kill.flag を書き込み、ExecutionEngine 側で停止を促します
- run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag を監視してループを終了します
- KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に kill.flag を自動でクリアします（本番では危険）

ディレクトリ構成（抜粋）
-----------------------
リポジトリの主要なファイル構成（src/kabusys 以下を中心に抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動ロード / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前チェック CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト

  - execution/                 — 発注関連（Engine / OrderManager / BrokerFactory 等）
    - (各実装ファイル)

  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化 + DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

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
    - news_nlp.py               — ニュースセンチメント（OpenAI 呼び出し）
    - regime_detector.py        — 市場レジーム判定（OpenAI）
    - __init__.py

  - monitoring/                 — 監視関連（上記）
  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py          — ログ初期化ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定
    - __init__.py

- data/                        — 実行時に利用する DB / フラグ / PID（通常はリポジトリルート）
  - monitoring.db (SQLite)
  - paper_trading.db (SQLite)
  - kabusys.duckdb
  - kill.flag
  - stop_requested.flag
  - execution.pid

補足 / 注意事項
---------------
- 環境切替:
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定します。live は本番挙動（実際に発注）です。
- DB の分離:
  - Monitoring は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - Execution は KABUSYS_ENV が paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
- OpenAI 利用:
  - OPENAI_API_KEY の設定が必要です。API 呼び出しは retry/backoff を含みますが、API が使えない場合はフォールバック挙動（例: score_regime は macro_sentiment = 0）を取ります。
- ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続します。
- セキュリティ:
  - .env は Git にコミットしないでください（config_setup でも注意喚起あり）。
  - KABU_API_PASSWORD 等の機密値は .env に格納し、適切に管理してください。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献ガイドラインを記載してください）

以上。README に追加したい具体的なコマンドや環境例（.env のサンプル等）があれば教えてください。必要に応じて README を拡張します。