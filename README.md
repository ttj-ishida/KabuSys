KabuSys — 日本株自動売買システム (README)
=======================================

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買フレームワークです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視（Monitoring）やペーパートレード環境、さらにニュースを使った AI スコアリング等の機能を含みます。DuckDB / SQLite をデータ層に利用し、kabuステーション（あるいはモックブローカー）経由での発注を想定しています。

主な特徴
--------
- 戦略研究モジュール（ファクター計算、特徴量解析、IC 計算）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ）
- ExecutionEngine（発注ロジック、リスク管理、リコンサイル）
- Monitoring（システム・トレード状態の定期監視、Kill Switch）
- Paper Trading モード（本番 DB と完全分離、MockBroker）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア付与）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、レポート生成）
- 統一されたログ設定（コンソール + 日次ローテートファイル）

セットアップ手順
----------------
前提
- Python 3.10 以上（型アノテーションの | 記法を使用）
- Git リポジトリをクローン済みであること

手順概要
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

2. 必要パッケージをインストール
   - 必須: duckdb, psutil, openai
   - 推奨/状況依存: pyyaml（config の YAML 検証用）
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを利用してください:
     pip install -r requirements.txt）

3. .env の作成
   - 対話形式ウィザードを使う:
     python -m kabusys.config_setup
   - 生成後、設定内容を検証:
     python -m kabusys.validate_config
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV (development / paper_trading / live)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB。デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時）
     - LOG_LEVEL（デフォルト INFO）
     - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

4. ディレクトリの準備
   - data/ と logs/ は自動生成されますが、権限等の都合で事前に作成しておくと安心です。

使い方
------
起動スクリプト
- 監視プロセス（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位でオーバーライド（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（data/monitoring.db のデフォルト）を常に使用します（KABUSYS_ENV に依らず本番 DB を参照）

- 発注エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と完全分離）
  - 実行中は data/execution.pid が使われます。停止は data/stop_requested.flag により検知します。

CLI ユーティリティ
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
    - --strict をつけると警告も FAIL 扱い（exit code 1）
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

AI / ライブラリ機能（プログラム的呼び出し）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルへ書き込み
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジームを判定し market_regime テーブルへ書き込み

監視・停止関連
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution は起動中に検知して安全に停止します。
- Kill Switch:
  - RiskMonitor 等が判定した際に data/kill.flag を書き込むことで ExecutionEngine 停止をトリガできます。Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill.flag を自動クリアしますが、本番（live）では 0 を強く推奨します。

ログ
- ログは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- デフォルトで stdout（コンソール）と logs/<app_name>.log（日次ローテート、30日分保持）へ出力します。
- LOG_DIR を指定して保存先を変更できます。

重要な挙動（実装上の注意）
- Monitoring は常に Settings.sqlite_path（監視 DB）を使用します（環境に依存しない）。
- ExecutionEngine は paper_trading モードのとき別 DB を使用して本番と完全分離します。
- process_priority は起動直後に "high" に設定されることを試みます（権限により失敗する場合があります）。
- OpenAI を使う機能は OPENAI_API_KEY の設定が必要です。API 呼び出しにはリトライとフェイルセーフが実装されています（失敗時は安全側の既定値で続行する設計）。

ディレクトリ構成（抜粋）
----------------------
プロジェクトは src/kabusys 以下に配置されています。主要ファイルとディレクトリを抜粋で示します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視用テーブル）
    - system_monitor.py      — システム・データ鮮度監視
    - trade_monitor.py       — 発注ログ監視（ファイル参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるランナー
    - alert_manager.py       — （アラート送信機能：LINE 等をラップ）

  - execution/
    - execution_engine.py    — ExecutionEngine の本体
    - broker_factory.py      — ブローカークライアント生成（mock / real 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクターキャップ・レジーム調整
    - position_sizing.py     — 株数算出・aggregate cap など

  - research/
    - factor_research.py     — モメンタム、ボラティリティ、バリュー計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ

  - data/                    — 実行時の DB / フラグファイル等（data/monitoring.db 等）
  - logs/                    — ログ出力先（デフォルト）

追加情報 / トラブルシューティング
--------------------------------
- PyYAML がインストールされていないと config/*.yaml の内容検証はスキップされます（validate_config が警告を出します）。
- DuckDB / SQLite ファイルパスの親ディレクトリが存在しない場合は起動時に自動作成される場面がありますが、権限等で作成に失敗する可能性があるため事前に作成しておくと安全です。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にしておくこと、LINE 通知トークン等を正しく設定しておくことを推奨します。
- OpenAI の API 使用はコストが発生するため、テスト時は適切なキーやモックを使用してください。テスト用に _call_openai_api をモックする設計になっています。

ライセンス・バージョン
---------------------
パッケージのバージョンは kabusys.__version__（現状 0.1.0）で管理されています。ライセンス情報や詳細はリポジトリのルートにある LICENSE / pyproject.toml 等を参照してください。

最後に
-------
この README はソースコード（src/kabusys）を基に作成しています。実際の運用前に python -m kabusys.validate_config で設定検証を行い、テスト環境（paper_trading）で動作確認することを強く推奨します。必要があれば README に用いるサンプル .env や運用手順（systemd / supervisor 用ユニットファイル等）も追記できます。必要なら指示ください。