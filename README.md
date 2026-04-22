README
=====

概要
----
KabuSys は日本株の自動売買・リサーチ基盤向けの内部ライブラリ群です。  
システム監視、発注エンジン起動、ペーパートレード検証、ファクター計算、ニュースの NLP スコアリング、
ポートフォリオ構築ロジックなどを含むモジュール群がまとまっています。

主な特徴
--------
- ExecutionEngine / Broker 抽象化により実際発注とペーパートレードを分離
- 監視サブシステム（System / Trade / Risk）と Kill Switch による安全停止機構
- DuckDB を使った研究向けファクター計算・特徴量解析
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント・レジーム判定（AI モジュール）
- ペーパートレード検証レポート生成ツール
- 環境設定ウィザードと起動前検証 CLI を提供

セットアップ手順
----------------
1. Python 環境（3.9+ 推奨）を用意する。仮想環境を推奨します。
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 必要なパッケージをインストールします（最低限）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML の検証に使用、無くても動作する箇所あり）
   例（pip）:
     pip install duckdb psutil openai PyYAML

   ※ 実行環境に応じてその他の依存がある場合があります。requirements.txt があればそちらを使用してください。

3. プロジェクトルートに .env を作成します（環境変数設定）。
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
   - 必須環境変数（最低限設定するもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う環境変数（一部）
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか (0/1)
     - PAPER_FILL_MODE: paper_trading 時の仮想約定モード (instant|partial|never|reject)

4. 設定検証（起動前チェック）:
     python -m kabusys.validate_config
   --strict オプションで警告も FAIL 扱いにできます。

5. データディレクトリ等の作成（自動作成されることもありますが事前に用意しておくと安全です）
   - data/ （デフォルトで DB・PID・フラグファイルを置きます）
   - logs/ （ログ出力先）

使い方
------
主要な起動スクリプトとツール:

- 実行エンジン（ExecutionEngine）起動
  - 本番・ペーパートレード切替は KABUSYS_ENV を設定
    python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にトランザクションを記録します。
    - PID ファイル: data/execution.pid（設定で変更可）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。

- 監視ループ起動（SystemMonitor のポーリング）
    python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依存せず本番 DB を参照する設計）。

- 設定ウィザード（.env 作成）
    python -m kabusys.config_setup

- 設定検証 CLI
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
    python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラムから利用）
  - ニュースセンチメント:
      from kabusys.ai import score_news
      score_news(conn, target_date, api_key=...)
  - レジーム判定:
      from kabusys.ai.regime_detector import score_regime
      score_regime(conn, target_date, api_key=...)

運用上の注意
-------------
- KABUSYS_ENV=live 設定時は実際に発注が行われます。設定・鍵情報を十分に確認してください。
- kill.flag（デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送れます。KillSwitch/監視ロジックが自動で書き込むこともあります。
- stop フラグ: data/stop_requested.flag を置くと監視ループや実行スクリプトが安全に終了します。
- ログ: デフォルトは logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、30日保持）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理（.env 自動ロード含む）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

packages / サブモジュール:
- ai/
  - news_nlp.py              — ニュースを OpenAI でスコアリングして ai_scores に格納
  - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py       — システム状態 / データ鮮度チェック
  - trade_monitor.py        — （トレード監視ロジック）
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag の作成 / 管理
  - monitoring_engine.py    — Monitor の束ねとアラート連携
  - alert_manager.py        — （アラート送信ロジック; 実装に応じて LINE 通知等）
- execution/
  - execution_engine.py     — 実行エンジン本体（EngineConfig / run_session 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py    — 銘柄選定・スコア順
  - position_sizing.py      — 株数決定・上限・丸め
  - risk_adjustment.py      — セクター制限・レジーム乗数
- research/
  - factor_research.py      — Momentum / Volatility / Value などのファクター計算（DuckDB）
  - feature_exploration.py  — 将来リターン計算・IC / 統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成
- utils/
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

その他ファイル・パス（デフォルト）
- data/monitoring.db               — 監視 DB（SQLite、Settings.sqlite_path）
- data/paper_trading.db            — ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid               — ExecutionEngine の PID ファイル（デフォルト）
- data/kill.flag                   — Kill Switch フラグ
- data/stop_requested.flag         — 監視・実行ループ停止用フラグ
- logs/<app_name>.log              — ログファイル（デフォルト logs/ ディレクトリ）

開発者向けメモ
---------------
- DuckDB 接続を受け取り SQL + Python でファクター計算を行う設計です（研究用コードは本番 DB を直接参照することもあります。ルックアヘッドバイアスに注意）。
- AI モジュールは OpenAI クライアントに依存します。API 呼び出し部分は例外・レート制限に対してリトライ処理やフォールバックを行いますが、API キー管理は運用側で行ってください。
- モジュールは多くが副作用を避ける設計（外部 API 呼び出しや現在時刻の参照を明示的に引数化）を心がけています。テスト容易性を意識した実装です。

ライセンス・貢献
----------------
（この README に含める場合はプロジェクトのライセンス・貢献フローを追記してください）

以上。必要であれば README にサンプル .env テンプレートやよくあるトラブルシューティングを追加します。どの情報を優先して載せたいか教えてください。