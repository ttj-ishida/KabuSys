KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株向けの自動売買／リサーチ／監視ユーティリティ群を提供します。  
README は簡潔な概要、機能一覧、セットアップ手順、使い方（主要コマンド）およびディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は以下の機能を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）：実際の/ペーパートレード注文処理、ブローカークライアントを抽象化
- 監視（Monitoring）：システム稼働状況、注文ログ、リスク（ドローダウン・ポジション上限）を定期的にチェックし、Kill Switch を発動可能
- ポートフォリオ構築（Portfolio）：候補選定・重み計算・ポジションサイズ計算・セクター制限等の純粋関数群
- リサーチ（Research）：DuckDB 上でファクター計算・将来リターン・IC 等を計算するユーティリティ
- AI 補助（AI）：OpenAI を用いたニュースのセンチメント評価・市場レジーム判定
- 運用ツール：対話型 .env 作成ウィザード、設定検証、ペーパートレード検証レポート生成など
- ユーティリティ：ログ設定、プロセス優先度設定等の共通ユーティリティ

主な特徴 / 機能一覧
------------------
- 実行環境切替（KABUSYS_ENV）により development / paper_trading / live をサポート
  - paper_trading では MockBroker を用い、本番 DB と分離された data/paper_trading.db を使用
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による安全停止
- SQLite（監視ログ / 発注ログ）と DuckDB（分析・リサーチ）によるデータ永続化
- OpenAI（gpt-4o-mini を想定）を用いたニュース NLP（銘柄別スコア）および市場レジーム判定
- ポートフォリオ構築（候補選定、等配分・スコア配分、リスクベースのポジションサイズ計算）
- 実運用時のログ出力（stdout + 日次ローテートファイル logs/<app>.log、30日保持）
- 設定ウィザード（.env 作成支援）と設定検証 CLI（警告/エラー出力）
- ペーパートレード検証レポート生成ツール（稼働率・注文成功率・レイテンシ等を集計）

前提 / 必要ライブラリ
--------------------
代表的な依存（環境や利用機能により変動します）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（config/*.yaml の内容検証を行う場合に任意）

セットアップ手順
---------------
1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする（pyproject.toml または .git が存在する階層）。
2. 仮想環境作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール:
   - pip install duckdb psutil openai
   - （設定検証で YAML を使う場合）pip install PyYAML
4. Python パス設定:
   - 開発中は project root から直接実行するか、pip install -e .（パッケージ化されている場合）を行う
   - 例: python -m kabusys.config_setup など（project root から実行）

環境変数と .env
----------------
- 自動ロード: プロジェクトルートにある .env および .env.local は起動時に自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（例・デフォルト）
  - KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
  - KABU_API_PASSWORD: kabuステーション API（必須）
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 用)
  - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 時の約定挙動）
  - LOG_LEVEL: DEBUG/INFO/…
  - OPENAI_API_KEY: OpenAI を使う場合（AI機能）
  - KILL_FLAG_CLEAR_ON_START: 1 にすると起動時に kill.flag を自動削除（本番では 0 を推奨）
- .env を対話式で作る: python -m kabusys.config_setup

設定検証
--------
- 設定と主要ファイルを検証する:
  - python -m kabusys.validate_config
  - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

主要な使い方 / 実行コマンド
------------------------

（注）以下は project root から実行してください。パッケージがインストールされている場合はどのディレクトリからでも python -m kabusys.x が動きます。

- 監視ループを起動（SystemMonitor のポーリング）:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒を上書き（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

  停止:
  - プロセスは data/stop_requested.flag の存在を検知すると安全終了します（停止フラグファイルを作成することで停止させられます）。

- ExecutionEngine（注文実行）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 実行中に data/stop_requested.flag が作成されるとエンジンに停止要求が送られます。

- .env の対話式作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）になります

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（指定がなければ env PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI / レジーム判定・ニューススコア:
  - AI 機能（kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）を呼び出すには OPENAI_API_KEY を設定してください。これらは DuckDB 接続を受け取り DB 上のテーブルを読み書きします。

停止 / Kill Switch
-----------------
- ExecutionEngine に対する "即時停止" は kill.flag を書き込むことで実行できます。KillSwitch はリスク条件（ドローダウン超過など）でこの flag を作成します。
  - kill.flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は自動でクリアされます（本番では 0 を推奨）
- run_monitoring / run_execution は data/stop_requested.flag の存在を確認してループを終了します（プロセスを優雅に停止したい場合に使用）。

ログ
---
- ログは stdout と日次ローテートファイル（logs/<app_name>.log）へ出力されます。デフォルトで 30 日分保持。
- ログレベルは LOG_LEVEL または setup_logging の引数で制御できます。

注意点 / 運用上のヒント
---------------------
- production（KABUSYS_ENV=live）では kill.flag の自動クリアを無効にすること（KILL_FLAG_CLEAR_ON_START=0 推奨）や、LINE 通知の設定を忘れないこと。
- paper_trading は本番 DB と分離される設計です（PAPER_TRADING_SQLITE_PATH を利用）。
- AI 機能は OpenAI API に依存します。API の障害やレート制限を考慮した実装（リトライ・バックオフ）を行っていますが、キーの管理やコストには注意してください。
- DuckDB/SQLite のファイルパスは環境変数で指定できます。監視スクリプトは monitoring DB に対してマイグレーション処理（カラム追加）を行います。

ディレクトリ構成（抜粋）
--------------------
以下は src/kabusys 以下の主要なファイル/ディレクトリです（抜粋）。プロジェクトルートは src の上位ディレクトリです。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py            — .env 作成ウィザード（対話式）
  - validate_config.py         — 起動前の設定検証 CLI
  - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker）
  - utils/
    - logging_setup.py         — 統一的なログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB の初期化・読み書き層
    - system_monitor.py        — システム状態 / データ鮮度監視
    - trade_monitor.py         — (存在) 注文ログ監視（ファイル内に実装あり）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 Monitor を束ねる
    - alert_manager.py         — (存在) 通知管理（LINE 等）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（起動・セッション管理）
    - broker_factory.py        — ブローカークライアント生成
    - order_manager.py         — 注文管理
    - order_repository.py      — 発注履歴永続化
    - reconciler.py            — ブローカーと DB の整合性チェック
    - risk_manager.py          — 取引リスク管理
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・スケール調整
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py   — 将来リターン計算・IC 等
  - ai/
    - news_nlp.py              — ニュースを LLM でスコアリングして ai_scores に書込
    - regime_detector.py       — マクロ + ETF MA200 によるレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
  - data/                      — デフォルトの DB / フラグファイル格納先（./data/*.db, *.flag, execution.pid など）
  - logs/                      — ログ出力先（デフォルト）

付録：主要コマンド例
-------------------
- .env の作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視を起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジンを起動:
  - python -m kabusys.run_execution
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB を指定: --db path/to/paper_trading.db

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。各モジュールの詳細な設計や API（関数の引数／戻り値）については該当モジュールの docstring を参照してください。質問や補足が必要であれば教えてください。