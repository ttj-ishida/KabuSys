README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの一部を実装した Python パッケージです。
このリポジトリには以下を含みます。

- 実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）コンポーネント（システム状態、注文ログ、リスク監視、Kill Switch）
- ポートフォリオ構築・ポジションサイジング関数群（純粋関数）
- リサーチ／ファクター計算（DuckDB を用いた計算）
- ニュース NLP やレジーム判定（OpenAI API を使用するモジュール）
- 環境設定ウィザード、設定検証、紙上検証レポート生成ツール

主な設計方針：
- DuckDB / SQLite をデータレイヤに利用（分析用 DB と監視／発注ログを分離）
- 実行環境（本番 / ペーパー / 開発）を明示し、Paper Trading は本番 DB と分離
- LLM 呼び出しは失敗に頑健（リトライ・フェイルセーフ）

機能一覧
--------
主要な機能（抜粋）:

- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB に記録
  - 停止フラグ検知（data/stop_requested.flag）で安全に停止
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status 等を SQLite に永続化
  - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き可
- Monitoring サブモジュール
  - system_monitor: CPU・メモリ・ディスク・プロセス生存・データ鮮度のチェック
  - trade_monitor: 発注ログの監視（滞留注文・約定異常などの検出）※実装参照
  - risk_monitor: ドローダウン・ポジション上限チェック、ダッシュボード更新
  - kill_switch: 条件により data/kill.flag を書き込み ExecutionEngine に停止指示
  - monitoring_db: 必要なテーブルを作成するマイグレーションロジックを含む永続化層
- Portfolio モジュール
  - 候補選定、等金額／スコア加重、セクター上限適用、レジーム乗数、ポジション数計算（単元丸め、aggregate cap 対応）
- Research モジュール
  - ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン、IC 計算、統計サマリ
  - DuckDB を用いた SQL+Python 実装
- AI モジュール
  - news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini 等）でセンチメントを算出・ai_scores に書き込み
  - regime_detector: ETF の MA200 とマクロセンチメントを合成して market_regime に書き込み
  - API 呼び出しはリトライ・JSON 検証を行う
- ユーティリティ
  - config_setup: 対話式に .env を生成・更新
  - validate_config: .env / config/*.yaml の事前検証
  - tools.paper_verification_report: Paper Trading の検証レポート生成（SQLite を参照）

セットアップ手順
--------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージをインストールします（必要なパッケージは pyproject.toml / requirements.txt を参照）。
   例:
     pip install -r requirements.txt
   ※ DuckDB、psutil、openai、PyYAML（設定検証で使用）などが必要です。

3. .env ファイルを作成します（対話式ウィザード推奨）。
   - 対話式で作成:
       python -m kabusys.config_setup
   - 生成後、設定を検証:
       python -m kabusys.validate_config
     --strict を付けると警告も失敗扱いになります。

4. データディレクトリ（デフォルトでは data/）とログディレクトリ（logs/）を用意します。通常は自動作成されますが権限等の都合で事前作成する場合:
     mkdir -p data logs

重要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（news/regime 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログレベル・ログ保存先
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを抑止

使い方
------
各主要機能はモジュール実行形式で起動できます（パッケージを PYTHONPATH に置いた前提）。

- 環境ウィザード（.env 作成）
    python -m kabusys.config_setup

- 設定検証（.env / config チェック）
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
    python -m kabusys.run_execution
  動作:
  - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH に記録し、本番 DB と分離する
  - data/stop_requested.flag が存在する場合は起動を行わない
  - 実行中に data/stop_requested.flag が作成されると Engine.stop() を呼んで停止する

- 監視ループ起動（SystemMonitor）
    python -m kabusys.run_monitoring
  オプション:
  - 環境変数 MONITOR_POLL_INTERVAL を設定するとポーリング間隔を上書き（秒）
  動作:
  - 監視は常に（KABUSYS_ENV に依らず）本番 sqlite_path を使用してログを書き込む
  - data/stop_requested.flag を検出すると監視ループを終了する

- Paper Trading 検証レポート
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
    --db を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を参照

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  これらを呼ぶには OPENAI_API_KEY の設定が必要です（引数で渡すことも可）。

停止方法（Kill / Stop）
- 実行中の ExecutionEngine を安全に停止したい場合は monitoring の KillSwitch による停止（kill.flag）が使われます。
  - KillSwitch は条件（ドローダウン・ポジション上限等）を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時・定期的にこのフラグを確認して安全停止します。
- 管理的にすぐ停止したい場合は data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検出して終了します。

主要ファイルとディレクトリ構成
---------------------------
以下は主要なファイル・ディレクトリの抜粋（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動ロードと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化層
    - system_monitor.py      — システム監視（CPU/メモリ/ディスク/データ鮮度）
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - trade_monitor.py       — 注文ログ監視（存在）
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — 通知管理（LINE 等、実装参照）
  - execution/               — ExecutionEngine 周り（broker, order_manager 等）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み算出
    - position_sizing.py     — 株数算出・aggregate cap
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — IC / 将来リターン / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLU/スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/                    — （実行時に利用するファイル、デフォルト）
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (default: data/paper_trading.db)
    - stop_requested.flag
    - kill.flag
    - execution.pid
  - logs/                    — ログ出力先（デフォルト logs/<app_name>.log）

データベース & マイグレーション
------------------------------
- monitoring_db.init_monitoring_db(conn) が必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等的に作成します。
- 起動スクリプトは起動時にこの初期化を行うため、通常ユーザー側で手動作成は不要です。
- Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用の SQLite を使用し、本番 monitoring.db と分離します。

ロギング
-------
- setup_logging(app_name="...") を使い、stdout の StreamHandler および日次ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
- LOG_DIR / LOG_LEVEL 環境変数で出力先・レベルを変更可。ログはデフォルトで 30 日保持されます。

注意事項 / ベストプラクティス
----------------------------
- .env は絶対に Git にコミットしないでください（config_setup のヘッダにも明記）。
- KABUSYS_ENV=live の場合は特に注意して設定を確認してください（validate_config で警告が出ます）。
- OpenAI API キーを使う機能はコスト・レートリミットに注意してください。retry ロジックはありますが、利用制限は考慮してください。
- Paper Trading を使って必ず動作確認を行い、本番（live）移行時は .env の値・Kill Switch の設定を慎重に検討してください。

貢献 / 拡張のヒント
--------------------
- portfolio／research／ai モジュールは純粋関数として設計されている箇所が多いため、ユニットテストを書きやすく拡張しやすい構成です。
- 実働 環境ではプロセス優先度や CPU affinity の設定（utils/process_priority.py）を活用することでレイテンシ改善に寄与する場合があります。
- OpenAI 呼び出し部分はインターセプトしてモック化しやすいよう設計されています（テストでの patch 推奨）。

ライセンス等
-----------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE / pyproject.toml を参照してください。

以上がこのコードベースの概要と基本的な利用方法です。必要であれば起動手順の具体例（systemd サービス定義、Dockerfile、CI 用スクリプト等）を追加で作成します。どの情報を優先して追加しましょうか？