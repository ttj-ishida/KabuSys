README — KabuSys（日本語）
=======================

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームの骨組みを提供するプロジェクトです。  
主な機能は次の通りです。

- 約定・注文管理を行う ExecutionEngine（本番／ペーパートレード対応）
- システム稼働性・取引状態・リスクを監視する Monitoring サブシステム
- ファクター計算・特徴量探索などの Research ツール（DuckDB 経由）
- ニュースの自然言語処理（OpenAI）を使ったセンチメントスコアリング（AI モジュール）
- ポートフォリオ構築ロジック（候補選定・重み付け・サイズ計算）
- .env 対話式ウィザード、設定検証 CLI、検証レポートなどのユーティリティ

主な設計方針
- 本番用コードとペーパートレードを明確に分離（DB も別ファイルに記録）
- DuckDB を分析向けに利用、SQLite を稼働監視・注文ログに利用
- OpenAI を利用した NLP 処理はフェイルセーフ（API 失敗時はスキップあるいは保守的フォールバック）
- datetime.today()/date.today() を安易に参照しない設計（ルックアヘッドバイアス防止）

機能一覧
----------
- Execution
  - ExecutionEngine: 発注・注文管理・リスク管理・約定整合処理
  - BrokerClientFactory: 環境に応じて実ブローカー／モックを切り替え
- Monitoring
  - SystemMonitor: CPU/Mem/Disk、データ鮮度、プロセス生存チェック
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs 参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）生成
  - MonitoringEngine: 各モニタの定期実行、アラート連携
- Research / Portfolio
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - 銘柄選定、重み付け（等配分・スコア配分）、ポジションサイズ計算、セクターキャップ、レジーム乗数
- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを ai_scores に書込
  - regime_detector: ETF MA とマクロニュースを組み合わせて市場レジーム判定
- ツール
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env / config/*.yaml の起動前チェック CLI
  - paper_verification_report: ペーパートレード DB の検証レポート生成

セットアップ手順
----------------

前提
- Python 3.10+
- システムに duckdb, psutil, openai, PyYAML（任意: config.yml 検証用）などが必要

例: 仮想環境作成と依存関係インストール
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使う）
   - pip install duckdb psutil openai PyYAML

.env の作成
1. 対話式ウィザードを使う（推奨）
   - python -m kabusys.config_setup
   - 表示に従って必須項目 JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD を入力してください。
2. 手動で作成する場合は .env.example を参照して .env を作成してください（.env.example は本リポジトリに含まれている想定）。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

代表的な設定（デフォルト値）
- KABUSYS_ENV: execution モード。値: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時のみ使用）
- LOG_LEVEL: INFO（または DEBUG 等）
- OPENAI_API_KEY: OpenAI を使う機能で必要

設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗 (exit 1) 扱いになります。

使い方
-------

ログ設定
- 起動スクリプト内で setup_logging(app_name="...") を呼んでおり、デフォルトは logs/<app_name>.log に日次ローテートで出力されます。LOG_DIR 環境変数でログディレクトリを上書きできます。

Execution Engine（エンジン）起動
- 本番・開発・ペーパーの切替は KABUSYS_ENV による。
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、発注記録は PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に保存されます（本番 DB と完全に分離）。
- 起動:
  - python -m kabusys.run_execution
- 停止制御:
  - data/stop_requested.flag（停止フラグ）や data/kill.flag（KillSwitch）が利用されます。
  - 実行中の PID ファイルは data/execution.pid（デフォルト）に書き込まれます。

Monitoring 起動
- 監視ループを開始:
  - python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）。
- Monitoring は環境にかかわらず Settings.sqlite_path（本番 monitoring DB）を使用して監視ログを記録します（設定上の意図）。

AI / レジーム / ニューススコア
- OpenAI API を利用するため OPENAI_API_KEY が必要です。
- ニューススコアリング:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - コマンドラインラッパーはありませんが、スクリプトやジョブから呼び出して利用します。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

Research / レポート生成ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH と同等）
- ファクター計算等は kabusys.research モジュールの関数を直接インポートして使用できます（DuckDB 接続を引数に渡す）。

運用上のファイル・フラグ
- data/kill.flag: KillSwitch によって書き込まれる停止フラグ（Execution 停止要求）
- data/stop_requested.flag: run_* スクリプトがループを抜けるための停止フラグ
- data/execution.pid: ExecutionEngine の PID（デフォルトの pid_file_path）
- DB デフォルト:
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb

ディレクトリ構成
-----------------

以下は主要なパッケージ・ファイルの概要（src/kabusys 以下）。

- __init__.py
  - パッケージ初期化、__version__ を定義

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV に応じて挙動が変わる（paper_trading の場合はモックブローカー）。

- run_monitoring.py
  - SystemMonitor を定期実行する監視スクリプト。MONITOR_POLL_INTERVAL で間隔を指定可能。

- config.py
  - Settings クラス。環境変数の読み込み、デフォルト値、検証ロジックを提供。
  - 自動でプロジェクトルートの .env/.env.local を読み込みます（無効化可）。

- config_setup.py
  - 対話式 .env 作成ウィザード。

- validate_config.py
  - 起動前の設定検証 CLI（必須環境変数・パス・YAML 構文等のチェック）。

- utils/
  - logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite に対する永続化レイヤ（テーブル作成・アップサート等）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: （取引監視ロジック）
  - risk_monitor.py: ドローダウン / ポジション数監視
  - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
  - kill_switch.py: Kill Switch 実装
  - alert_manager.py: （アラート送信ロジック）

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager などの実装（発注・リスク管理・約定整合）

- portfolio/
  - portfolio_builder.py: 銘柄選定・重み付け
  - position_sizing.py: 株数決定ロジック（単元丸め・aggregate cap）
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum/Value/Volatility ファクター計算
  - feature_exploration.py: 将来リターン・IC 計算・統計サマリー

- ai/
  - news_nlp.py: OpenAI を用いたニュースセンチメント評価（ai_scores へ書込）
  - regime_detector.py: ETF MA + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py: ペーパートレードの検証レポート生成ツール

実運用上の注意
----------------
- 本リポジトリには実際の証券ブローカー接続情報が含まれていません。KABUSYS_ENV=live を使用する際は十分にレビューし、LINE 通知などアラート設定を必ず確認してください（validate_config はこの点で警告を出します）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup.py のヘッダにも注記あり）。
- OpenAI を利用する機能は API 利用料金・レート制限に注意してください。API キーは安全に保管してください。
- monitoring の DB スキーマは init_monitoring_db() で冪等に作成／マイグレーションされますが、運用時はバックアップを行ってください。

よく使うコマンド例
------------------
- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスと貢献方法を記載してください）

補足
----
- ここに記載した内容はコードベース（src/kabusys/*.py）を基にまとめたもので、実際のリポジトリに含まれるファイル・追加ドキュメントに合わせて適宜更新してください。
- 追加で欲しいドキュメント（API リファレンス、設計ドキュメント、運用手順書など）があれば指定してください。