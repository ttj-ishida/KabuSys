KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。  
トレード実行、監視、ポートフォリオ構築、ファクター計算、ニュースNLP（OpenAI）等のモジュールを含みます。

要点
- Python パッケージ名: kabusys
- 主な実行スクリプト（モジュールとして起動）
  - 実行エンジン: python -m kabusys.run_execution
  - 監視ループ:   python -m kabusys.run_monitoring
  - .env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

プロジェクト概要
----------------
KabuSys は以下の機能を持つモジュール群で構成される自動売買フレームワークです（主要設計方針の一部）:

- ExecutionEngine（発注ロジック）: ブローカークライアントを抽象化し、本番／ペーパートレードを切替可能。
- Monitoring（監視）: システム稼働状況・データ鮮度・注文状況・リスク（ドローダウン・ポジション上限）をポーリングしてログ・アラート・Kill Switch を管理。
- Portfolio（銘柄選定・配分・ポジションサイジング）: 等重・スコア重み・リスクベース発注量計算、セクターキャップ、レジーム乗数。
- Research（ファクター計算・特徴量解析）: momentum/value/volatility 等のファクターを DuckDB 上で計算。IC 等の評価ツールあり。
- AI（ニュースNLP / レジーム判定）: OpenAI を利用したニュースのセンチメント評価・市場レジーム判定（API キー必須）。
- Utilities（ロギング、プロセス優先度設定、設定読み込み等）: 起動時のログ設定、プロセス優先度/CPU affinity、.env ロード。

主な機能一覧
-------------
- 実行環境切替: KABUSYS_ENV=(development|paper_trading|live)
  - paper_trading 時は MockBrokerClient を使用し、paper_db を分離して記録。
- 監視・アラート:
  - system_status / trade_logs / risk_logs / dashboard 等を SQLite で永続化。
  - Kill Switch（条件により data/kill.flag を書き込み ExecutionEngine に停止シグナル）。
- ポートフォリオ構築:
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ計算、単元株丸め。
- 研究ツール:
  - DuckDB を使ったファクター計算（momentum, volatility, value 等）と IC / 統計サマリ。
- ニュース解析（OpenAI）:
  - raw_news を集約して LLM に投げ、銘柄別スコアを ai_scores に書き込み。バッチ・リトライ・バリデーションを実装。
- 運用ユーティリティ:
  - .env 対話ウィザード、設定検証 CLI、ログ設定（stdout + 日次ローテート）等。

セットアップ手順
----------------

1. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 必要最低限:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - PyYAML （config/*.yaml の構文チェックを行う場合に推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt は本コードベースに含まれていないため、環境に合わせてインストールしてください）

3. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動で .env を作成。最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - LOG_LEVEL（オプション、デフォルト: INFO）
   - .env は決してリポジトリにコミットしないでください（config_setup も警告を出します）。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に FAIL 扱いしたい場合:
     - python -m kabusys.validate_config --strict

使い方
------

基本コマンド例

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは paper_trading DB（PAPER_TRADING_SQLITE_PATH）へ書き込みされ、本番 SQLite と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動を行いません。
    - 実行エンジンは data/execution.pid（デフォルト）に PID を書きます。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30  （秒）
    - デフォルト: 60 秒
  - 監視は Settings に定義された sqlite_path を常に使用（監視は本番 DB を参照）。
  - 停止方法:
    - data/stop_requested.flag を作成するとループが検知して終了します。
    - Kill Switch は risk 条件等によって data/kill.flag を書き込み、ExecutionEngine に停止を促します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト data/paper_trading.db）

- .env の対話式セットアップ
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict フラグで警告もエラー扱いにできます。

運用に関するポイント
- ログ
  - setup_logging により stdout と logs/<app_name>.log（日次ローテーション、30日分保持）に出力されます。
  - ログディレクトリは環境変数 LOG_DIR またはデフォルト logs/。
- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼ぶため psutil による優先度設定を試みます（権限不足の場合は警告でスキップ）。
- Kill Switch / Stop flag
  - RiskMonitor 等が条件を満たすと KillSwitch が data/kill.flag に理由を書き込みます。ExecutionEngine は kill.flag の存在を見て適切に停止できます（設定に依存）。
  - 手動での停止には data/stop_requested.flag を作成してください（run_* スクリプトがこのファイルを参照して終了します）。
- Paper Trading
  - KABUSYS_ENV=paper_trading を指定すると BrokerClientFactory が MockBrokerClient を生成し、発注はペーパートレード用 DB に記録されます。本番 DB と完全分離されます。

ディレクトリ構成
----------------

主要なファイル/ディレクトリ（src/kabusys 配下）:

- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト
- config.py                 — 環境変数/設定読み込みロジック（.env 自動ロード含む）
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証 CLI
- __init__.py               — パッケージ定義（__version__ など）

サブパッケージ（概要）:
- ai/
  - news_nlp.py             — ニュースを OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py      — マクロ + ETF MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py        — SQLite テーブル初期化・永続化層
  - system_monitor.py       — システム状況・データ鮮度チェック
  - trade_monitor.py        — （注文滞留・約定異常チェックなどを想定）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書き込みユーティリティ
  - monitoring_engine.py    — 各 Monitor を束ねるエンジン
  - alert_manager.py        —（アラート送信管理: LINE 等を想定）
- portfolio/
  - portfolio_builder.py    — 候補選定、重み計算
  - position_sizing.py      — 発注株数計算（単元丸め・スケールダウン等）
  - risk_adjustment.py      — セクターキャップ、レジーム乗数
- research/
  - factor_research.py      — momentum/volatility/value などの計算（DuckDB）
  - feature_exploration.py  — 将来リターン、IC、統計サマリ
- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
- utils/
  - logging_setup.py        — 共通ログ設定（stdout + 日次ローテート）
  - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルのみ抜粋。詳細は src/kabusys 以下の各モジュールを参照してください）

環境変数一覧（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN         — J-Quants API トークン（必須）
- KABU_API_PASSWORD             — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL             — kabu API のベース URL（デフォルト localhost:18080）
- OPENAI_API_KEY                — OpenAI API キー（AI 機能で必須）
- KABUSYS_ENV                   — execution モード: development / paper_trading / live（default: development）
- DUCKDB_PATH                   — DuckDB ファイル（default: data/kabusys.duckdb）
- SQLITE_PATH                   — 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH     — paper_trading 用 SQLite（default: data/paper_trading.db）
- LOG_LEVEL                     — ログレベル（default: INFO）
- MONITOR_POLL_INTERVAL         — 監視のポーリング間隔（秒、run_monitoring の場合。default: 60）
- PAPER_FILL_MODE               — paper_trading の fill 挙動。instant / partial / never / reject

開発・拡張メモ
----------------
- DuckDB 接続を渡してデータ分析・ファクター計算を行う設計です。prices_daily / raw_financials / raw_news 等のテーブルを前提とします。
- OpenAI を使うモジュールは API 呼び出し部分を抽象化しており、テスト時はモックで差し替え可能です。
- monitoring_db.init_monitoring_db() は既存 DB を破壊しない（冪等）ように実装され、必要なマイグレーションも含みます。

トラブルシューティング
---------------------
- ログディレクトリ作成に失敗する場合はコンソール出力のみになります（権限等を確認）。
- psutil による優先度設定で権限エラーが出る場合は警告が出てスキップされます（通常の動作には影響しません）。
- OpenAI 関連は API キーが未設定だとエラー/例外が発生します。AI 機能を使う場合は OPENAI_API_KEY を設定してください。

ライセンス / 注意事項
--------------------
- .env 等の秘密情報は決してリポジトリにコミットしないでください。
- live モードでの運用は実際の発注を伴います。十分なテストと監査を行ってから利用してください。

以上。詳細な関数仕様や設計方針については各モジュールの docstring を参照してください。README の補足や追記を希望する項目があれば教えてください。