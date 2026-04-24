README
=====

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムのコアライブラリです。  
注文実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI を用いたニュースセンチメント・レジーム判定などのコンポーネントを含むモジュール群で構成されています。  
設計方針として、以下を重視しています。
- 本番／ペーパートレードの分離（paper_trading モード）
- DuckDB + SQLite による分析・ログ永続化
- OpenAI を用いたニュース NLP（オプション）
- .env ベースの設定と対話式ウィザード / 検証ツール

主な機能
--------
- ExecutionEngine：発注ロジック、リスク管理、注文管理、リコンシリエーション
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し paper_trading DB に記録
- Monitoring：システム稼働状況・データ鮮度・注文状態・リスク監視、Kill Switch（停止フラグ）発動
- ポートフォリオ構成：候補選定、等金額 / スコア重み、リスクに基づく単位数算出
- リサーチ：モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算、統計サマリー
- AI：ニュース記事のセンチメントスコア算出（OpenAI）および市場レジーム判定
- ツール：ペーパートレード検証レポート生成、設定ウィザード、設定検証 CLI
- ログ設定ユーティリティ：コンソール + 日次ローテートファイル出力
- プロセス優先度・CPU affinity 設定補助（psutil ベース）

動作要件（概要）
----------------
- Python 3.10+
- 主要依存ライブラリ（少なくとも開発には必要）:
  - duckdb
  - psutil
  - openai (AI機能を使う場合)
  - PyYAML（config 検証で YAML 内容をチェックしたい場合）
- OS: Linux / macOS / Windows（プロセス優先度設定や CPU affinity はプラットフォーム差異あり）

セットアップ手順
----------------
1. リポジトリを取得
   - git clone ...（プロジェクトルートに移動）

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （すべての機能を使わない場合は openai / PyYAML は任意）

4. 初期設定（.env 作成）
   - 対話式ウィザードを利用（推奨）
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成
   - 作成後、設定検証を実行
     - python -m kabusys.validate_config
     - 警告も FAIL にしたい場合は --strict を付ける

主な環境変数（代表例）
---------------------
（.env に設定する代表的なキーとデフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBrokerClient を利用し data/paper_trading.db を使用
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能を使う場合必須
- MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring.py で使用, デフォルト 60）

使い方
------
1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - 終了後、python -m kabusys.validate_config で検証

2. 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 説明:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
     - 監視は環境にかかわらず本番 sqlite_path を使用してログを記録
     - 停止はプロジェクトルート/data/stop_requested.flag ファイル作成で行う（存在確認してループを抜ける）

3. 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離
     - 実行中は data/execution.pid に PID を書きます
     - 停止指示は data/stop_requested.flag を作成することで受け付けます
     - Kill Switch（監視側）が発動すると data/kill.flag が作成され ExecutionEngine を停止させるトリガーになります
     - 設定 KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に既存 kill.flag を自動でクリア（本番では推奨されません）

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション: --db で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5. AI 機能
   - ニューススコアリング: kabusys.ai.score_news を呼び出し（API キーは OPENAI_API_KEY または引数で指定）
   - レジーム判定: kabusys.ai.regime_detector.score_regime（同様に API キーが必要）
   - 注意: OpenAI 呼び出しは外部 API 料金が発生します。失敗時のフォールバックやリトライロジックが組み込まれています。

停止・強制停止
---------------
- 正常停止（監視・実行プロセス両方）: プロジェクトルート/data/stop_requested.flag を作成するとループが検出して停止します。
- Kill Switch: 監視が重大リスクを検知すると data/kill.flag を作成します。ExecutionEngine は起動時や運用中にこのフラグを検出して停止します。
- PID ファイル: data/execution.pid に書かれます（プロセス監視や外部システムとの連携に利用可）。

ログ
---
- ログはデフォルトで logs/ ディレクトリに日次ローテートで出力されます（logs/<app_name>.log）。
- LOG_DIR 環境変数で出力先を変更できます。
- setup_logging ユーティリティによりルートロガーを統一設定します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数読み込み・Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

- src/kabusys/execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- src/kabusys/monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py

- src/kabusys/tools/
  - paper_verification_report.py

重要なファイル・パス（デフォルト）
---------------------------------
- data/kabusys.duckdb          — DuckDB（分析用）
- data/monitoring.db           — SQLite（監視ログ: system_status, trade_logs, positions, risk_logs, dashboard）
- data/paper_trading.db        — Paper trading 用 SQLite（paper_trading モード）
- data/execution.pid           — ExecutionEngine の PID（起動時に作成）
- data/kill.flag               — Kill Switch が書き込む停止フラグ
- data/stop_requested.flag     — ユーザが作成してプロセスを停止するためのフラグ

開発・テストのヒント
--------------------
- 自動環境変数ロードは Settings モジュール内で .env / .env.local をプロジェクトルートから検出して行います。テスト時に自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しは学習・テスト中にコストがかかるため、テストでは関数 _call_openai_api をモックしてください（モジュール内に直接 import しているため patch のパスに注意）。
- DuckDB を使った関数群は外部 API にアクセスせず DB のみを参照する設計です（ローカルで分析を再現しやすい）。

補足
----
- 本 README はコードベースの主要機能と運用フローを要約したものです。個別のモジュール（ExecutionEngineやOrderManager 等）はさらに詳細な実装・使用方法がそれぞれの docstring に書かれています。初めて運用する際は必ず validate_config と paper_trading モードでの動作確認を行ってください。
- 本番運用時は KABUSYS_ENV=live 設定や LOG_LEVEL 等を慎重に設定し、Kill Switch の動作や LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を確認してください。

以上。README に記載してほしい追加項目（例: 具体的な API キーの取得方法、より詳細な起動例、CI 設定等）があればお知らせください。