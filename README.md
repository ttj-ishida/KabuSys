README — KabuSys
=================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージです。  
主要コンポーネントとして、注文実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を用いたニュースセンチメント評価などを含みます。

主な特徴
--------
- ExecutionEngine: 実口座／ペーパートレード両対応（KABUSYS_ENV により切替）
  - paper_trading では MockBrokerClient を用い、data/paper_trading.db に記録（本番 DB と分離）
- Monitoring: システム状態・発注状態・リスク（ドローダウン等）を定期監視し、kill.flag による停止指示やアラート送信を実施
- Portfolio モジュール: 候補選定、重み付け、ロット丸め、セクター制約・レジーム乗数の適用
- Research モジュール: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量解析ユーティリティ
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定（フェイルセーフ・バッチ処理・リトライあり）
- ユーティリティ:
  - 対話式 .env 初期化ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成ツール

前提条件
--------
- Python 3.10+
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の内容検証を行う場合）
- システムによっては psutil による優先度変更に管理者権限が必要

インストール（開発環境セットアップ例）
-------------------------------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合は pip install -r requirements.txt を推奨）

4. ディレクトリ作成（必要に応じて）
   - mkdir -p data logs

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨／任意:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
  - live: 本番動作
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB（monitoring.db）。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — AI モジュール利用時に必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリアは危険（0 推奨）

自動 .env ロード
- パッケージロード時にプロジェクトルート（.git または pyproject.toml を探索）で .env/.env.local を自動読み込みします。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

セットアップ手順（推奨ワークフロー）
---------------------------------
1. .env を対話式に作る（推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って必須値を設定してください（.env は Git にコミットしないでください）。

2. 設定を検証
   - python -m kabusys.validate_config
   - 警告も厳密に扱う場合: python -m kabusys.validate_config --strict

3. 必要な DB/ディレクトリを確認・作成
   - data/ と logs/ の作成を確認（logging は logs/<app>.log に出力）

起動方法（主要スクリプト）
-------------------------
- 実行エンジン（Execution）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用し PAPER_TRADING_SQLITE_PATH に記録
    - 起動時に data/stop_requested.flag があると起動せず終了
    - 実行中に stop flag を検知するとエンジンを停止
    - execution.pid に PID を書き込む（設定により場所は変更可）

- 監視プロセス（Monitoring）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを永続化
    - data/stop_requested.flag の存在でループを抜けて終了

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB 指定可能（コマンドラインを優先）

- AI 関連（モジュール API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルに書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書込

停止・Kill Switch
-----------------
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が条件を満たすと kill.flag を書き込み、ExecutionEngine 側はこれを検知して安全に停止します。
  - KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動クリアされるが本番では危険です（0 推奨）。
- stop_requested.flag:
  - run_monitoring.py / run_execution.py が監視している停止フラグ（data/stop_requested.flag）。存在するとループを抜けて終了します。

ログ
----
- ログはデフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリを作成しておく）。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます。

依存ライブラリ（主なもの）
-------------------------
- duckdb
- psutil
- openai
- PyYAML（optional: validate_config が config/*.yaml を検証する場合）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョンなど）
- config.py — 環境変数 / 設定管理（.env の自動読み込み、Settings クラス）
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor 起動スクリプト

src/kabusys/ai/
- news_nlp.py — ニュースを OpenAI でセンチメント化して ai_scores に書き込む
- regime_detector.py — マクロ + ETF MA で市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマ初期化・永続化層（MonitoringDB）
- system_monitor.py — システム状態・データ鮮度チェック
- trade_monitor.py — （発注・約定の監視ロジック: ファイル中で参照あり）
- risk_monitor.py — ドローダウン・ポジション上限の監視
- kill_switch.py — kill.flag 書込みロジック
- monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
- alert_manager.py — （アラート送信を管理する想定モジュール）

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・スコア順ソート・等分/スコア重み計算
- position_sizing.py — 発注株数決定・単元丸め・投下資金スケーリング
- risk_adjustment.py — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py — モメンタム/バリュー/ボラティリティ等の DuckDB ベース計算
- feature_exploration.py — 将来リターン計算、IC（スピアマン）等の解析ユーティリティ

src/kabusys/utils/
- logging_setup.py — 共通ログ設定ユーティリティ
- process_priority.py — psutil を用いたプロセス優先度 / CPU affinity 設定ユーティリティ

その他
-----
- monitoring_db.init_monitoring_db は冪等でテーブル作成と必要なマイグレーション（列追加）を行います。
- AI モジュールは OpenAI API の失敗を許容するフェイルセーフ設計（リトライ、部分書き込み制御）になっています。
- duckdb 接続を受け取って計算する設計のため、本番 DB に対して読み取り専用で動作することを想定しています。

よくある運用上の注意
-------------------
- 本番（KABUSYS_ENV=live）では必須の環境変数が正しく設定されているか validate_config で必ずチェックしてください。
- Kill Switch 設定（KILL_FLAG_CLEAR_ON_START）を本番で 1 にすることは推奨されません。
- psutil による優先度変更や CPU affinity の設定は OS 権限により失敗することがあります（警告ログのみ出ます）。
- .env は機密情報を含むため絶対にリポジトリに含めないでください。

サポート / 拡張
----------------
- 新しいブローカ実装は BrokerClientFactory 経由で差し替え可能（run_execution 参照）。
- 研究用クエリは DuckDB 上で完結するため、データ投入さえできれば容易に検証可能です。
- 追加の監視ルールやアラートチャネルは AlertManager を拡張して対応してください。

ライセンス
----------
- 本 README ではライセンス情報を含めていません。実プロジェクトの LICENSE を参照してください。