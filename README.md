KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株自動売買に必要な以下の機能群を備えた小規模なフレームワーク／実装例です。

- 発注エンジン（ExecutionEngine） — 実運用／ペーパートレードに対応
- 監視（Monitoring） — システム状態・注文状態・リスク監視、Kill Switch
- ポートフォリオ構築（選定・配分・ポジションサイズ）ユーティリティ
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュースセンチメント、レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

本リポジトリは「本番」「ペーパートレード」「開発」を環境変数で切り替え可能で、データ永続化には SQLite（監視・発注ログ等）と DuckDB（分析用）を使用します。

主な機能
--------
- Execution
  - 実際のブローカークライアント（kabuステーション）接続またはペーパートレード用の MockBrokerClient を利用
  - RiskManager / Reconciler / OrderManager を組み合わせた実行セッション
  - 起動時に PID ファイルを作成、停止はフラグファイルで制御
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス生存確認 / データ鮮度
  - TradeMonitor：滞留注文・約定異常検出（trade_logs 参照）
  - RiskMonitor：ドローダウン・ポジション上限検知、risk_logs / dashboard 更新
  - KillSwitch：重大リスク発生時に data/kill.flag を書き込み ExecutionEngine を停止
  - アラート送信フック（AlertManager）を通じて外部通知を出せる設計
- Portfolio（純関数）
  - 候補選定、等金額・スコア重み付け、セクター制限、レジーム乗数、ポジションサイズ計算
- Research
  - DuckDB を使ったファクター計算（モメンタム・バリュー・ボラティリティ等）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- AI
  - ニュースセンチメント（OpenAI）を銘柄別に集約・スコア化して ai_scores に書込
  - マクロニュース + ETF MA を用いた市場レジーム判定と保存
- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ペーパートレード検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.9+（ソースの type hints に依存）
- 必要なライブラリ（例）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（validate_config の YAML 検証を有効にする場合）
- Git リポジトリのルートがプロジェクトルート検出に使用されます（.git または pyproject.toml がある場所）。

クイックセットアップ
1. リポジトリをクローンして作業ディレクトリをルートに移動
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール（例）
   - pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式ウィザードを使う: python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API を使う機能で必要
- DUCKDB_PATH — 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KILL_FLAG_CLEAR_ON_START — 本番で kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — monitoring 起動スクリプトのポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（テスト用）

よく使うデフォルトパス
- data/monitoring.db (SQLITE_PATH)
- data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- data/kabusys.duckdb (DUCKDB_PATH)
- data/execution.pid (PID_FILE_PATH のデフォルト)
- data/kill.flag (KillSwitch が書き込むファイル)
- data/stop_requested.flag (run_* スクリプトの停止フラグ)
- logs/ (LOG_DIR のデフォルト)

使い方（主要コマンド）
--------------------
基本的にはモジュールを直接実行します（パッケージとして -m 実行）。

1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. ExecutionEngine 起動（本番 or paper_trading いずれも Settings.KABUSYS_ENV に依存）
   - python -m kabusys.run_execution
   - 起動時に Settings が参照され、paper_trading の場合は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に書き込みます。
   - 停止は data/stop_requested.flag を作るか、KillSwitch による data/kill.flag により行われます。

4. Monitoring 起動（常駐ポーリング）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き可能
   - Monitoring は常に本番 sqlite_path（SQLITE_PATH）を参照して監視テーブルを操作します。

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

停止／Kill 手順
- 実行スクリプト（run_execution / run_monitoring）はプロジェクトルート下の data/stop_requested.flag の存在をチェックして安全停止します。手動で停止したい場合はこのファイルを作成してください。
- リスク重大時に Monitoring の KillSwitch が data/kill.flag を書き込み、ExecutionEngine がそれを検知して停止します（KillSwitch は冪等設計）。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では推奨されません。

ロギング
-------
- 共通のユーティリティ kabusys.utils.logging_setup.setup_logging を使ってログを統一しています。
- デフォルトでコンソール（stdout）と logs/<app_name>.log 日次ローテート（30 日分保持）に出力します。
- LOG_DIR 環境変数または引数でログディレクトリを上書きできます。

開発者向けのポイント
--------------------
- 環境変数の自動読み込み
  - プロジェクトルートにある .env, .env.local を自動で読み込みます（OS 環境変数が優先）。
  - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 設定は kabusys.config.Settings 経由で安全に取得できます（必須キー未設定時は例外）。
- DB スキーマは monitoring/monitoring_db.init_monitoring_db で冪等に作成・マイグレーションされます。
- AI 関連（news_nlp / regime_detector）は OpenAI API を利用します。API 呼び出しは堅牢にリトライやフォールバックを行う設計です。
- プロセス優先度や CPU affinity は kabusys.utils.process_priority 経由で設定され、run_* スクリプト内で起動直後に高優先度へセットしています（失敗時はログに警告）。

プロジェクト構成
---------------
以下は主要ファイル／ディレクトリの抜粋（src/kabusys 以下）です。実際には pyproject.toml 等がルートに存在する想定です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（自動 .env 読込, Settings クラス）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログセットアップ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — ExecutionEngine 本体・OrderManager 等（詳細モジュール）
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化層
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

依存関係（主なもの）
------------------
- duckdb — 分析用 DB 接続
- psutil — システムメトリクス取得 / プロセス制御
- openai — AI（ニューススコア / レジーム判定）利用時
- PyYAML — validate_config の YAML 検証に任意で使用

トラブルシューティング
----------------------
- .env が読み込まれない／意図した値が反映されない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - プロジェクトルート（.git / pyproject.toml）が正しく検出されているか確認
- monitoring が起動しても DB のテーブルがない
  - init_monitoring_db は自動でテーブル作成を行います。権限やファイルパス（SQLITE_PATH）を確認してください。
- AI 機能が失敗する（OpenAI）
  - OPENAI_API_KEY の有無、ネットワーク、利用制限（レート制限）を確認。処理はリトライ・フォールバック設計ですが、キーがないと動作しません。

ライセンス & バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートに含めてください（本 README には含めていません）。

最後に
-----
この README はコードベースの主要な使い方・設定箇所をまとめたものです。実際の運用や本番投入の際は config/*.yaml（存在する場合）や settings の各閾値、KillSwitch / RiskManager のしきい値設定および LINE などの通知設定を慎重に確認してください。