README
=====

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
本リポジトリは取引の実行ロジック、モニタリング、ポートフォリオ構築、リサーチ（ファクター計算）、および AI を使ったニュース評価などを含むモジュール群から構成されています。  
各コンポーネントは明確に分離されており、ペーパートレードと本番（live）を環境変数で切り替えて運用できます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番・ペーパートレードを環境で切替え（KABUSYS_ENV）
  - Broker クライアントファクトリによる実・モックの切替え
  - リスク管理（最大ポジション比率、利用率、サーキットブレーカー等）
- Monitoring（監視）
  - システムリソース、プロセス稼働、データ鮮度、注文ログの監視
  - Kill Switch（ドローダウンやポジション上限で Execution を停止する機能）
  - 監視ログは SQLite（monitoring.db）に永続化
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額／スコア重み付け、ポジションサイズ計算（単元株対応）
  - セクター上限チェック、レジームに応じた乗数
- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー
- AI（ニュース NLP / レジーム判定）
  - OpenAI API を使ったニュースのセンチメント評価（ai_scores）
  - マクロニュースと ETF MA200 を合成して市場レジーム判定
- ツール
  - Paper Trading の検証レポート生成スクリプト
- 設定支援
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

前提条件
--------
- Python 3.10 以上（typing の新構文を使用）
- 推奨ライブラリ（主要なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証を行う場合に任意）
- SQLite（標準ライブラリで利用可）

インストール
------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml

   ※requirements.txt がある場合はそれを使用してください。

環境変数 / .env
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN （必須）
- KABU_API_PASSWORD   （必須）
- KABUSYS_ENV         : development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH         : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH         : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（paper_trading 用）
- LOG_LEVEL           : ログレベル（デフォルト: INFO）
- OPENAI_API_KEY      : OpenAI を使う機能で必要

サンプル .env（抜粋）
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

.env の生成（対話式ウィザード）
- python -m kabusys.config_setup
  - 対話形式で .env を作成／更新します。
- 作成後、設定を検証する:
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱い（exit 1）

実行方法
--------
主要なエントリポイントはモジュールとして実行できます。

1) ExecutionEngine を起動（発注エンジン）
- python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データベースは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に分離して記録します。
  - 起動時に data/stop_requested.flag が存在していると起動を中止します。
  - 実行中は data/execution.pid ファイルが使用されます。

2) Monitoring を起動（ポーリング監視）
- python -m kabusys.run_monitoring
  - モニタリングは常に本番の sqlite_path（SQLITE_PATH）を使用します（環境に依らず）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60秒）。
  - 停止は data/stop_requested.flag を作成することで行います（監視ループが検知して終了）。

3) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: env の PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

シャットダウン / Kill Switch
- モジュール間で停止フラグを使います:
  - data/stop_requested.flag : run_* スクリプトがこのファイルを検知すると安全に停止します。
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除できます（本番では 0 推奨）。

ログ
---
- ログは標準出力（stdout）とファイル出力に設定されます（kabusys.utils.logging_setup）。
- デフォルトのログディレクトリ: logs/
- app_name に基づき logs/<app_name>.log に日次ローテーションで出力（30日保持）
- LOG_DIR 環境変数でログ出力先を変更可能

開発・テストのヒント
-------------------
- 自動 .env 読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI を使う機能のテストは OpenAI クライアント呼び出しをモックする設計になっています（_call_openai_api を patch 可能）。
- psutil によるプロセス優先度設定は権限不足や未サポート環境で安全にフォールバックします。

ディレクトリ構成（主なファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings 管理（.env 自動ロード）
- config_setup.py               — .env 対話式作成ウィザード（python -m kabusys.config_setup）
- validate_config.py            — 設定検証 CLI（python -m kabusys.validate_config）
- run_execution.py              — ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
- run_monitoring.py             — Monitoring 起動スクリプト（python -m kabusys.run_monitoring）

サブパッケージ（抜粋）
- ai/
  - news_nlp.py                  — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py             — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py            — システム稼働・データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常検出（存在）
  - risk_monitor.py              — ドローダウン・ポジション数監視
  - kill_switch.py               — kill.flag 書き込みロジック
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - alert_manager.py             — 通知管理（LINE 等 実装想定）
- execution/
  - execution_engine.py          — 実行エンジン本体（EngineConfig, run_session 等）
  - broker_factory.py            — Broker クライアント生成（実/モック切替）
  - order_manager.py             — 発注管理
  - order_repository.py          — 注文永続化層（SQLite 想定）
  - reconciler.py                — 発注結果整合処理
  - risk_manager.py              — 実行時リスク管理
- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 注文株数計算（単元丸め、スケーリング）
  - risk_adjustment.py           — セクター上限・レジーム乗数
- research/
  - factor_research.py           — Momentum / Volatility / Value 等のファクター計算（DuckDB 使用）
  - feature_exploration.py       — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - logging_setup.py             — ロギング設定ユーティリティ
  - process_priority.py          — プロセス優先度・CPU affinity 設定ユーティリティ

注記
----
- DuckDB と SQLite を併用しており、DuckDB は主に履歴・分析用途（prices_daily, raw_financials 等）、SQLite は監視／実行ログ（trade_logs, positions, dashboard）に使われます。
- AI 関連機能を有効にするには OPENAI_API_KEY を設定してください。API 失敗時はフェイルセーフ（スコア0やスキップ）になる設計です。
- 本リポジトリの .env は絶対に機密情報を含めたままコミットしないでください（config_setup でも注意喚起があります）。

ライセンス / 貢献
----------------
（ここにライセンス情報や貢献方法を記載してください）

以上。必要であれば README にサンプル運用例や systemd / supervisor 用のユニットファイル、より詳細な設定項目の説明（各 config/*.yaml のフォーマット等）を追加できます。どの情報を補足しますか？