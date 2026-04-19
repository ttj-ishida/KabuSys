README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤のコアライブラリ群です。本リポジトリには以下の機能群が含まれます：

- 注文実行エンジン（ExecutionEngine）とブローカ接続の抽象化（本番 / ペーパートレード切替）
- 監視（Monitoring）：システム状態、発注ログ、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクターキャップ、レジーム調整）
- リサーチ（ファクター計算、特徴量探索、将来リターン / IC 計算）
- AI 系ユーティリティ（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

主な特徴
--------
- 環境変数 / .env による柔軟な設定管理（config.Settings）
- 実行環境切替（development / paper_trading / live）。paper_trading は本番 DB から完全に分離された専用 SQLite を使用
- 監視ループと Kill Switch（stop/kill フラグファイルによる運用停止）
- DuckDB を用いたリサーチ向け高速集計 / ファクター計算
- OpenAI を使ったニュースセンチメント（gpt-4o-mini）と市場レジーム検出（リトライ・バリデーション等の堅牢化）
- ログはコンソール + 日次ローテーションファイル出力（logs/）で統一管理

必要条件（主要）
----------------
- Python 3.10+
- ライブラリ（例: pip install で導入）
  - duckdb
  - openai
  - psutil
  - pyyaml（config ファイル検証時に必要、任意）
- SQLite（標準ライブラリで利用）
- ネットワーク接続（外部 API 利用時）

（requirements.txt がない場合は上記パッケージをインストールしてください。）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai psutil pyyaml

4. 初期設定（.env）の作成
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参照）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い: python -m kabusys.validate_config --strict

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / 任意:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 環境用）
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番アラート送信用（任意）

.env の自動ロード
- パッケージ起動時、プロジェクトルートに .env / .env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要スクリプトの使い方
--------------------

1) ExecutionEngine（発注エンジン）起動
- スクリプト: src/kabusys/run_execution.py
- 実行例:
  - python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 実行中は data/execution.pid に PID を書き込む設計（Engine に渡されます）。
  - 停止は data/stop_requested.flag を作成する、あるいは Kill Switch（data/kill.flag）で行います。

2) Monitoring（監視）起動
- スクリプト: src/kabusys/run_monitoring.py
- 実行例:
  - python -m kabusys.run_monitoring
- 動作:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能。デフォルトは 60 秒。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを永続化します（monitoring DB の分離に注意）。
  - 停止は data/stop_requested.flag の検出で行います。

3) 設定検証 CLI
- python -m kabusys.validate_config
- --strict を付けると警告で exit(1) になります。

4) .env ウィザード
- python -m kabusys.config_setup
- 対話形式で .env を生成・更新します。

5) Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db PATH で別 DB を指定可能
- 出力: 稼働率、注文成功率、送信率、レイテンシ等を集計して PASS/FAIL を判定します。
- 閾値はソース内で定義（稼働率 99% など）。

AI / リサーチ機能
-----------------
- ニュースセンチメント: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を渡すと ai_scores テーブルへ書き込みます。
  - OpenAI API キーを引数または環境変数 OPENAI_API_KEY にセットしてください。
- レジームスコア: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュースセンチメントを組み合わせて market_regime テーブルへ書き込みます。

運用 / 停止フロー
----------------
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution が監視しており、存在するとループを終了します（管理者が手動で作成）。
  - data/kill.flag: KillSwitch が書き込むファイルで、ExecutionEngine に停止シグナルを送るために使用されます（本番での緊急停止）。
- KillSwitch の評価は RiskMonitor 等の監視結果に基づき行われます（ドローダウンやポジション上限等）。

ログ
----
- ログはデフォルトで logs/ ディレクトリに出力されます（ログファイル名は app_name に基づき e.g. logs/execution.log）。
- setup_logging() はコンソール（stdout）と TimedRotatingFileHandler（日次ローテーション、30世代）を設定します。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御可能。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数/.env の読み込みと Settings クラス
- config_setup.py
  - .env 対話式ウィザード
- validate_config.py
  - 起動前検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor 起動スクリプト

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity 設定

- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 発注ログ監視（滞留注文/約定異常検出）
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag 操作
  - monitoring_engine.py — 各 Monitor をまとめる（ポーリング管理）
  - alert_manager.py — （アラート送信用、コード参照）

- execution/
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager
  - （発注ロジックとブローカ抽象化）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・制約確認
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — モメンタム・バリュー・ボラティリティ等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ等

- ai/
  - news_nlp.py — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py — レジーム判定（OpenAI と市場指標の合成）

- tools/
  - paper_verification_report.py — Paper Trading レポート生成

注意事項 / 運用上のヒント
------------------------
- 本番運用時（KABUSYS_ENV=live）は特に環境変数（LINE 通知設定など）を確認してください。validate_config がガードチェックを行います。
- kill_flag の自動クリア（KILL_FLAG_CLEAR_ON_START）は本番で 1 にするのは危険です（推奨は 0）。
- Monitoring は設定により本番の sqlite_path を参照する仕様です。混同しないよう注意してください。
- OpenAI の呼び出しはレート制限や失敗に備えたリトライ・フェイルセーフロジックがありますが、API キーやコスト管理（バッチサイズ等）は運用側で制御してください。

貢献 / 開発
-----------
- コードは関心事分離（DB 層、監視ロジック、AI 呼び出しなど）を意識して設計されています。ユニットテストやモックによる API 呼び出しの差し替えがしやすい構成です。
- テスト / CI の追加、ドキュメント拡充、config/*.yaml のテンプレート生成スクリプト改善などの貢献を歓迎します。

ライセンス
----------
- リポジトリに含まれるライセンスファイルを参照してください。（本 README には明記していません）

お問い合わせ
------------
- 問題や改善提案は issue を作成してください。README にない運用フローの質問も歓迎します。