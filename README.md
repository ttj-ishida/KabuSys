KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買（研究・ポートフォリオ構築・実行・監視）を
目的としたPythonパッケージの一部です。本ドキュメントはコードベースから読み取れる
主要な機能・セットアップ・使い方・ディレクトリ構成をまとめた README です。

注: 実行や本番利用の前に必ず .env を作成し、設定検証（validate_config）を実行してください。
また、本プロジェクトは外部ライブラリ（duckdb, psutil, openai 等）に依存します。

プロジェクト概要
----------------
KabuSys は以下の主要コンポーネントから構成されます。

- ExecutionEngine: 発注ロジック・リスク管理・オーダー管理を統合して注文実行を行う（run_execution.py 起動）。
  - 本番環境とペーパートレード（mock）を切り替え可能。ペーパートレード時は専用 SQLite DB を使用して本番 DB と分離。
- Monitoring: システム健全性（CPU/メモリ/ディスク）、Execution の状態、リスク（ドローダウン、ポジション上限）などを定期監視（run_monitoring.py 起動）。
  - 異常検出時に kill.flag を書き込む Kill Switch 機能やアラート通知機能を持つ。
- Research / Portfolio: DuckDB を使ったファクター計算・特徴量探索・ポートフォリオ構築・ポジションサイジング等の純粋関数群。
- AI モジュール: OpenAI を使ったニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）。
- ユーティリティ: ログ設定、プロセス優先度設定、設定ファイル管理ウィザード、設定検証など。
- ツール: Paper Trading の検証レポート生成スクリプト等。

主な機能一覧
-------------
- 環境設定ウィザード（kabusys.config_setup）: 対話式に .env を生成・更新
- 設定検証 CLI（kabusys.validate_config）: .env や config/*.yaml 等を起動前に検証
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading と live を切り替え
  - paper_trading では MockBrokerClient を使用し data/paper_trading.db に記録
  - Execution 用の PID ファイル管理・停止フラグ（data/stop_requested.flag）対応
  - 実行時にプロセス優先度を上げる（utils.process_priority）
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリング
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視結果やログは SQLite（monitoring.db）に永続化（monitoring_db.init_monitoring_db がテーブル作成）
  - stop_requested.flag によりループ停止
- Kill Switch（monitoring.kill_switch）
  - ドローダウンやポジション上限超過時に data/kill.flag を書き込み Execution を安全に停止
- AI ニューススコアリング（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini を想定）を用いた銘柄単位のセンチメント計算、ai_scores テーブルへ書込
  - バッチ処理・リトライ・レスポンス検証・スコアクリップ等の堅牢化
- レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュース LLM 出力を合成して 'bull'/'neutral'/'bear' を決定
  - market_regime テーブルへ冪等書き込み
- Research（kabusys.research）
  - momentum / volatility / value などのファクター計算（DuckDB 使用）
  - 将来リターン計算、IC（Information Coefficient）や統計要約
- Portfolio（kabusys.portfolio）
  - 候補選定、等配分・スコア重み配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（lot 単位丸め・aggregate cap）
- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 用の検証レポート出力（稼働率、注文成功率、レイテンシなどの評価と PASS/FAIL 判定）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ...（この README では取得方法は省略）

2. Python 環境
   - 本コードは Python 3.10+ を想定しています（型ヒントで | を使用）。
   - 仮想環境を作成して有効化する例:
     - python -m venv .venv
     - source .venv/bin/activate  # Linux/macOS
     - .venv\Scripts\activate     # Windows

3. 依存ライブラリのインストール
   - 必須パッケージの例（環境に応じて適宜インストールしてください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイルの検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がプロジェクトに含まれていればそれを使用してください:
     - pip install -r requirements.txt

4. .env の作成
   - 対話式ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV (development | paper_trading | live)
     - OPENAI_API_KEY (AI 機能を使う場合)
   - その他: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_LEVEL, LOG_DIR, PAPER_FILL_MODE, KILL_FLAG_CLEAR_ON_START 等

5. 設定の検証
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付与

6. データディレクトリ
   - デフォルトで data/ 以下に DB やフラグファイルが置かれます。必要に応じて .env でパスを変更してください。
   - logs/ ディレクトリには app ごとのログファイル（例: logs/execution.log, logs/monitoring.log）を出力します。

基本的な使い方
--------------

- Execution を起動（例: 本番または paper_trading を .env で切替）
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると安全に停止します（停止フラグは起動前にチェックされます）。
  - PID ファイル: data/execution.pid（デフォルト）を使用

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL を設定してポーリング間隔を秒単位で変更（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番 sqlite_path（.env の SQLITE_PATH）を使用します（監視は環境に依存しない）

- .env 作成（ウィザード）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告でも exit(1)（CI 等で利用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可 / 環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能
  - OpenAI API を使う機能（news_nlp, regime_detector）は OPENAI_API_KEY を環境変数または関数引数で渡す必要があります。
  - API 呼び出しは冪等性・リトライ・レスポンス検証が組み込まれていますが、API 使用時はコスト・レート制限に注意してください。

- ログ
  - setup_logging により stdout と logs/<app_name>.log へ出力されます。
  - ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用。

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ保存ディレクトリ
- KILL_FLAG_CLEAR_ON_START: 本番での自動クリア禁止推奨（0/1）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

データ/フラグファイル
--------------------
- data/kill.flag: Kill Switch が発動した際に作成されるフラグ。Execution が起動時にチェックする。
- data/stop_requested.flag: run_* スクリプトを外部から優雅に停止したい場合に置くと各ループが終了する（run_monitoring/run_execution で使用）。
- data/execution.pid: Execution 用 PID ファイル（デフォルト）
- data/monitoring.db: 監視用 SQLite（デフォルト）
- data/paper_trading.db: paper_trading 用 SQLite（分離）

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要ファイルと説明です（抜粋）。

- src/kabusys/
  - __init__.py  — パッケージ定義（__version__ など）
  - config.py    — .env 読込・Settings クラス（全設定の集中管理）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト

  - utils/
    - logging_setup.py — ログ初期化ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py — プロセス優先度 / CPU affinity 設定

  - monitoring/
    - monitoring_db.py — SQLite 用永続化層（テーブル作成・CRUD ヘルパ）
    - system_monitor.py — CPU/MEM/DISK・データ鮮度・Execution プロセス監視
    - trade_monitor.py  — （省略）発注ログ監視（ファイル上に存在）
    - risk_monitor.py   — ドローダウン・ポジション上限監視
    - kill_switch.py    — kill.flag 書込ロジック
    - monitoring_engine.py — 各 Monitor を束ねてポーリング
    - alert_manager.py  — （省略）通知管理（LINE 等）

  - execution/
    - execution_engine.py — エンジン本体（run_session 等）
    - broker_factory.py    — BrokerClient の生成（本番/Mock 分岐）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注・リスク関連

  - portfolio/
    - portfolio_builder.py — 候補選定・スコアソート
    - position_sizing.py   — 株数決定・aggregate cap・単元丸め
    - risk_adjustment.py   — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — momentum/volatility/value 等の DuckDB ベース計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
    - __init__.py

  - ai/
    - news_nlp.py        — ニュースセンチメント（OpenAI 呼出・レスポンス検証・DB 書込）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース LLM）
    - __init__.py

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

補足・運用上の注意
-----------------
- 本番運用時は KABUSYS_ENV=live を慎重に扱ってください。validate_config は live 時に追加の警告を出します。
- kill.flag / stop_requested.flag / PID ファイルは運用スクリプト間での簡易シグナル行為に使われます。CI/運用スクリプトからこれらを操作することで安全に停止できます。
- AI（OpenAI）呼び出しはコストとレート制限に注意してください。API キーの管理は厳重に行ってください。
- DuckDB/SQLite のファイルパスは .env で管理できます。監視 DB は monitoring が本番パスを参照する点に注意してください（monitoring は環境にかかわらず本番 sqlite_path を使う設計になっています）。
- ログは stdout とファイルの両方に出力されます。ログローテーションは daily、30 日保持です。

トラブルシューティング
---------------------
- .env が読み込まれない／自動ロードを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します（テスト用）。
- DuckDB や OpenAI SDK が見つからない場合は pip install で必要パッケージを追加してください。
- 実行中に監視が例外を捕まえた場合はログ（stdout または logs/）を確認してください。MonitoringEngine や SystemMonitor は例外時も継続するよう設計されていますが、根本原因はログから確認できます。

ライセンス・貢献
----------------
この README ではライセンスや貢献手順は含めていません。プロジェクトルートの LICENSE / CONTRIBUTING ファイルがある場合はそちらを参照してください。

以上。必要があれば各モジュールの詳細ドキュメント（関数一覧や引数仕様、例）を別途生成します。どの箇所のドキュメントが欲しいか教えてください。