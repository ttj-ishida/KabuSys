KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究用ライブラリ群です。  
主な目的は以下です。

- 取引エンジン（ExecutionEngine）の起動・管理（実際の発注 or ペーパートレード）
- システム監視（SystemMonitor / MonitoringEngine）と自動停止（Kill Switch）
- ポートフォリオ構築（銘柄選定、重み付け、株数決定）
- リサーチ（ファクター計算、将来リターン、IC 等）
- AI を用いたニュースセンチメント（OpenAI 経由）のスコアリング
- ペーパートレード検証レポート生成ツール

本リポジトリは「実行スクリプト」「監視」「ポートフォリオ構築」「リサーチ」「AI ニュース処理」など複数のモジュールで構成されています。

主な機能一覧
--------------
- 実行エンジン起動:
  - run_execution.py — ExecutionEngine を起動。KABUSYS_ENV に応じて本番／ペーパートレードを切り替え。
- 監視:
  - run_monitoring.py — SystemMonitor のポーリングループを起動。監視ログを SQLite に永続化。
  - MonitoringEngine — SystemMonitor / TradeMonitor / RiskMonitor を束ねてアラート・Kill Switch を評価。
- 設定管理:
  - config_setup.py — .env を対話的に作成・更新するウィザード。
  - validate_config.py — 起動前の環境変数・config/*.yaml の簡易検証ツール。
- ポートフォリオ:
  - portfolio.* — 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数など。
- リサーチ:
  - research.* — モメンタム / ボラティリティ / バリューファクター、将来リターン計算、IC・要約統計など（DuckDB を利用）。
- AI:
  - ai.news_nlp — OpenAI を使ったニュース記事の銘柄別センチメント評価・ai_scores への書き込み。
  - ai.regime_detector — ETF の MA 乖離とマクロニュースを組み合わせて日次レジーム判定（market_regime テーブルに書き込み）。
- ツール:
  - tools.paper_verification_report — ペーパートレード DB を読み取り検証レポートを出力。
- ユーティリティ:
  - utils.logging_setup — 統一ログ設定（コンソール + 日次ローテーションファイル）。
  - utils.process_priority — プロセス優先度・CPU affinity 設定ユーティリティ。
- 永続層:
  - monitoring/monitoring_db.py — 監視ログ用 SQLite スキーマ初期化と CRUD。

セットアップ手順
--------------
前提
- Python 3.9+（型注釈の構文を利用）
- OS: Linux / macOS / Windows（ただし一部の機能は POSIX 固有の挙動あり）

推奨手順（ローカル）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   本コードベースで利用している外部パッケージ:
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証を使う場合、任意）
   例:
   - pip install duckdb psutil openai PyYAML

   補足:
   - sqlite3 は標準ライブラリ
   - 実際のプロジェクトでは requirements.txt を作成して pip install -r でインストールしてください。

3. データディレクトリの用意（任意、起動時に自動作成される箇所もあります）
   - mkdir -p data logs

4. .env の作成
   - まずはウィザードで作成するのが簡単です:
     - python -m kabusys.config_setup
   - あるいは手動で .env に下記の必須項目を設定してください（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=...（AI 機能を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い:
     - python -m kabusys.validate_config --strict

使い方（主な実行コマンド）
------------------------
以下はパッケージのルートから実行する想定（src を PYTHONPATH に含めるか package としてインストール）。

- 実行エンジン（ExecutionEngine）を起動:
  - 本番モード例:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（Mock Broker）を使う例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 注意:
    - ペーパートレード時はデフォルトで data/paper_trading.db に記録され、本番 DB と分離されます。

- 監視ループを起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL は秒数。無効な値や 0 以下はデフォルト 60 秒にフォールバックします。

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（スクリプト化されている場合・手動実行）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date を渡して呼び出す関数です。実行には OPENAI_API_KEY の設定が必要です。

停止方法（監視・実行）
- run_execution/run_monitoring の両スクリプトはプロジェクトの data/stop_requested.flag（および kill.flag）を監視しています。
  - 強制停止や制御用に stop ファイルを作成すると安全にループが終了します。
  - KillSwitch は条件に応じて data/kill.flag を作成し、ExecutionEngine 停止を促します。
- PID ファイル:
  - 実行エンジンは data/execution.pid を使用します（Settings.pid_file_path で変更可能）。

主要な環境変数（抜粋）
---------------------
必須（起動に必要）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings は未設定だと例外を出す）
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（挙動に影響）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用、紙上の DB に記録
  - live: 本番実行（注意が必要）
- OPENAI_API_KEY — OpenAI API を用いる AI 機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレード時の約定振る舞い（instant/partial/never/reject）

ログ
----
- ログはデフォルトでコンソール出力（stdout）と logs/<app_name>.log（日次ローテーション）に出力されます。
- setup_logging() でログ出力先やレベルを上書き可能です。

ディレクトリ構成（主要ファイル説明）
-----------------------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数/設定読み込みロジック（.env 自動読み込み、Settings クラス）
- config_setup.py
  - .env を対話的に作成するウィザード CLI
- validate_config.py
  - 起動前チェック CLI（必須 env の確認、config/*.yaml の存在確認等）
- run_execution.py
  - ExecutionEngine 起動スクリプト。環境により本番/ペーパートレードを切替。
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔指定可。

サブパッケージ・モジュール
- ai/
  - news_nlp.py — OpenAI を使ったニュースセンチメント取得と ai_scores への書込
  - regime_detector.py — マクロ + ETF MA で市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システムリソース、プロセス生存、データ鮮度をチェック
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag 書込みによる Execution 停止シグナル
  - monitoring_engine.py — 複数 Monitor を束ねて実行・アラート処理
- portfolio/
  - portfolio_builder.py — 候補選定・スコアソート
  - position_sizing.py — 株数計算・キャッシュ配分・ロット丸め
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- tools/
  - paper_verification_report.py — ペーパートレード DB から検証レポート生成
- utils/
  - logging_setup.py — 統一ログ設定
  - process_priority.py — プロセス優先度設定（Windows/Linux の違いを吸収）
- その他
  - monitoring/…、execution/…（本リストに含めていない詳細な実装ファイルが存在する想定）

運用上の注意
------------
- KABUSYS_ENV=live のときは本番口座へ実際に発注が行われます。設定・環境変数を慎重に確認してください。
- .env は機密情報（API トークン等）を含むため、決して Git へコミットしないでください。
- Kill Switch（kill.flag）の挙動は重要です。KILL_FLAG_CLEAR_ON_START の設定を本番で 1 にするのは危険です（自動でクリアされるため）。
- OpenAI を利用する処理は API コストが発生します。テスト時はモック化して実行してください。
- DuckDB / SQLite のファイルパスは設定で変更できます。運用前にバックアップ方針を検討してください。

よくあるコマンドまとめ
---------------------
- 仮想環境作成:
  - python -m venv .venv && source .venv/bin/activate
- 依存インストール:
  - pip install duckdb psutil openai PyYAML
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレード検証:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張
---------------
- 新しいデータソースや broker クライアントを追加する場合は factory パターン（BrokerClientFactory）に従って実装してください。
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news など）は research/ai モジュールで参照されているため、互換性を保って更新してください。
- テストでは OpenAI 呼び出しや外部 API をモックすることを推奨します（モジュール内の API 呼出しは専用関数に集約されています）。

最後に
------
この README はコードベースの主要コンポーネントと基本的な運用手順をまとめたものです。実稼働前に必ず python -m kabusys.validate_config で設定を検証し、低リスクな環境で総合テストを行ってください。質問や改善提案があればお知らせください。