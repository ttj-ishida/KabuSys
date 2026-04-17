README.md
===========

プロジェクト概要
--------------
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのシステムです。本リポジトリには以下の要素が含まれます。

- 発注実行エンジン（ExecutionEngine）とその依存コンポーネント
- 監視サブシステム（System / Trade / Risk モニタ、Kill Switch、アラート管理）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数算出・リスク調整）
- 研究用モジュール（ファクター計算・特徴量解析）
- AI（LLM）を用いたニュースセンチメント / レジーム判定機能
- ペーパートレード検証レポート生成ツール

本プロジェクトは設計上、実環境（live）・ペーパートレード（paper_trading）・開発（development）を区別し、ペーパートレード時は本番 DB と分離して動作するようになっています。

主な機能一覧
------------
- ExecutionEngine 起動・注文管理（Broker クライアント抽象化、OrderRepository, OrderManager, RiskManager など）
- MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を束ねて定期チェック、Kill Switch 評価、アラート送出
- SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度の監視
- TradeMonitor：滞留注文（stale orders）や約定価格の異常検出
- RiskMonitor：ドローダウンやポジション上限チェック、ダッシュボード更新
- KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine を停止させる
- Portfolio モジュール：候補選定（スコア・等分配）、ポジションサイズ計算、セクターキャップ・レジーム乗数
- Research モジュール：モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・統計サマリ
- AI モジュール：
  - news_nlp: OpenAI を使ったニュースセンチメント集約・ai_scores への書込み
  - regime_detector: ETF MA とマクロニュースの LLM 評価を合わせて市場レジーム判定
- ツール:
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（paper_verification_report）

動作に関する注意点
- Monitoring（監視）は実行環境に関わらず production の sqlite_path を使用します（監視ログは本番 DB を参照）。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と完全に分離します。
- プロセス優先度は起動時に "high" に設定されます（psutil を使用）。権限不足等で設定できない場合は警告だけ出します。

必要条件（主な外部ライブラリ）
-----------------------------
- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML：config/*.yaml の内容検証に使用
- その他：標準ライブラリ

※ requirements.txt がない場合は上のパッケージを pip で個別にインストールしてください。

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）  
     必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD

主要な環境変数（抜粋）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 動作環境
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
    - paper_trading の場合、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録

- DB パス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）

- OpenAI
  - OPENAI_API_KEY: news_nlp / regime_detector が参照する API キー

- その他
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch のフラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
  - PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

例（.env の一部）
------------------
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml を検証）
  - python -m kabusys.validate_config
  - 警告も失敗にする場合: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合は data/paper_trading.db を使い MockBrokerClient を利用
    - 起動時に data/stop_requested.flag が存在すると起動を行わず終了
    - 実行中に data/stop_requested.flag が作成されると安全に停止

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に監視用の sqlite_path（Settings.sqlite_path）を使用する

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 機能（プログラムから呼び出す場合）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection（DuckDBPyConnection）
    - target_date: date 型（スコア付与対象日）
    - api_key: None の場合は OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に DuckDB 接続と日付、OpenAI API キーを渡す

停止・Kill フラグ
-----------------
- run_execution / ExecutionEngine の停止は主に以下の方法で行います:
  - data/kill.flag を作成すると KillSwitch が検出して ExecutionEngine に停止を指示します（kill.flag の内容は理由テキスト）。
  - run_execution / run_monitoring の停止（ループ終了）は data/stop_requested.flag を作成すると検出して終了します。
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動で削除します（本番では危険なため 0 推奨）。

監視・ログ関連
--------------
- monitoring_db.init_monitoring_db により必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）が作成されます（冪等）。
- MonitoringDB クラスを通じて監視ログやリスクイベント、ダッシュボード集計を永続化します。
- SystemMonitor はデータ鮮度判定に DuckDB 上の prices_daily を参照します（get_last_price_date を利用）。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数/Settings
- config_setup.py               — .env 対話ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP（OpenAI）スコアリング
  - regime_detector.py           — 市場レジーム判定（MA + LLM）

- monitoring/
  - monitoring_db.py             — SQLite 永続層（監視用）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py             — （実装：アラート送信ロジックをカプセル化）

- execution/
  - （ExecutionEngine 関連コンポーネント: broker_factory, execution_engine, order_manager, order_repository, reconciler, risk_manager, order_record 等）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- monitoring tools / scripts
  - tools/
    - paper_verification_report.py

- utils/
  - process_priority.py          — プロセス優先度・CPU affinity ユーティリティ
  - __init__.py

注意・運用上のヒント
--------------------
- 本番運用する場合は KABUSYS_ENV=live とし、LINE 通知周り（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の設定を慎重に確認してください。
- .env は絶対にバージョン管理に含めないでください（secret トークンが含まれます）。
- OpenAI API を使う機能は API 利用料・レート制限に注意してください。news_nlp/regime_detector はリトライやフォールバック（失敗時 0.0）実装済みですが、API キーの管理は慎重に行ってください。
- DuckDB / SQLite ファイルはデフォルトで data/ 以下に作られます。バックアップや容量監視を検討してください。

貢献・開発
----------
- まずは config_setup で .env を作成し、validate_config で検証してください。
- ローカルでのペーパートレード検証は KABUSYS_ENV=paper_trading を使うと安全に試せます（本番 DB とは分離されます）。
- テストや CI を追加する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env ロードを抑制できます。

ライセンス
---------
（リポジトリに合わせて適切なライセンス表記を追加してください）

以上が README の要点です。追加で API の詳細仕様や ExecutionEngine の内部設計（構成図、シーケンス図など）を README に含めたい場合は指示してください。