KabuSys — 日本株自動売買システム
=================================

このリポジトリは、日本株の自動売買 / 研究 / モニタリングを目的とした軽量フレームワークです。  
README はコードベース（src/kabusys 以下）を参照して作成しています。以下ではプロジェクト概要、機能、セットアップ手順、利用方法、主要ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下の目的を持つコンポーネント群から構成されます。

- ExecutionEngine：発注ロジックおよびブローカークライアントとのやり取り（本番/ペーパートレード対応）
- Monitoring：システム稼働状態、注文ログ、リスク監視、Kill Switch（停止フラグ）管理
- Research：DuckDB を用いたファクター計算・探索
- AI モジュール：ニュースの NLP（OpenAI）を用いたセンチメント／レジーム判定
- ユーティリティ：設定管理、ログ設定、プロセス優先度調整、環境セットアップウィザード等

このコードベースは「実運用を想定した設計方針（フェイルセーフ性、冪等性、ログ/監視強化）」を重視しています。

主な機能一覧
-------------
- 環境設定ウィザード (.env の対話式生成) — kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の存在/基本整合性チェック） — kabusys.validate_config
- Execution エントリポイント（本番 / paper_trading 切替、専用 SQLite への書き込み） — run_execution.py
- Monitoring エントリポイント（ポーリング監視、DB に system_status / trade_logs / risk_logs / dashboard を記録） — run_monitoring.py
- Kill Switch（条件に応じて data/kill.flag を書き込み ExecutionEngine を安全停止）
- Paper Trading 検証レポート生成ツール（SQLite DB を読み取り PASS/FAIL 判定） — tools.paper_verification_report
- ポートフォリオ構築（候補選定 / 重み計算 / 単元丸め / リスク調整）
- 研究用ファクター計算（momentum / volatility / value 等） — research.factor_research
- ニュース NLP による銘柄センチメント（OpenAI 経由）および市場レジーム判定（LLM + MA） — ai.news_nlp / ai.regime_detector

セットアップ手順
----------------

前提
- Python 3.9+
- 推奨依存（最低限のもの）:
  - duckdb
  - psutil
  - openai (AI 関連機能を使う場合)
  - PyYAML（設定ファイルの検証を行う場合）
- SQLite（標準ライブラリに含まれます）

インストール例（仮想環境推奨）
- 仮想環境作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージをインストール（例）
  - pip install duckdb psutil openai pyyaml

.env の準備（推奨）
1. 対話式ウィザードで初期作成
   - python -m kabusys.config_setup
   - 対話に従って必須値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD など）を入力します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションをつけると警告も失敗扱いになります。

自動環境変数ロードの挙動
- プロジェクトルート（.git または pyproject.toml）を探索し、.env（優先度低）→ .env.local（優先度高）を自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要環境変数（抜粋・デフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用、default: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（任意、アラート通知用）
- OPENAI_API_KEY（AI 機能を利用する場合必須）

重要なファイル/フラグ
- data/kill.flag — Kill Switch が発動したことを示すフラグ（ExecutionEngine が停止を検知）
- data/stop_requested.flag — run_execution / run_monitoring の外部停止（デーモン停止）用フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（管理用）
- logs/<app>.log — ログ（setup_logging により自動ローテート）

使い方（実行例）
----------------

1) 環境を整える
- .env を作る:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config

2) モニタリング（デーモン的に稼働）
- デフォルトのポーリング間隔は 60 秒。環境変数で上書き可:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は monitoring DB（Settings.sqlite_path）に system_status 等を書き込みます。
- run_monitoring はプロセス優先度を high に設定し、data/stop_requested.flag が作成されるとループを終了します。

3) 実行エンジン起動（発注）
- 本番 or paper_trading を切り替える:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- paper_trading モードでは MockBrokerClient を使用し、設定された PAPER_TRADING_SQLITE_PATH に記録します。
- 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。実行中に stop_requested.flag が生成されると内部で stop() が呼び出され停止処理を行います。

4) Paper Trading 検証レポート出力
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB パスは --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH で指定できます。

5) Kill Switch の運用
- Monitoring が RiskMonitor の判定等で KillSwitch を発動すると data/kill.flag を書き込みます。ExecutionEngine は起動時や定期チェックでこのフラグを参照して安全に停止できます。
- 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは開発時のみ）。

ログとローテーション
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を各プロセスで呼び出しており、ログは stdout と logs/<app>.log に日次ローテーションで出力されます（30 日保持）。
- ログディレクトリは LOG_DIR 環境変数で変更可能。

アーキテクチャ上の注記
- 設定は Settings クラス（kabusys.config）でラップしており、アプリケーション全体で統一して参照します。
- MonitoringDB（monitoring/monitoring_db.py）は SQLite への永続化層で、必要に応じてスキーママイグレーション（既存カラムの追加）を自動で行います。
- DuckDB は分析・研究用途の高速クエリ用 DB（prices_daily / raw_financials 等のテーブルを想定）。
- OpenAI を使う AI モジュールは API 呼び出しの失敗時にフェイルセーフ（デフォルト値にフォールバック）する設計になっています。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールの一覧（抜粋）と簡単な説明です。

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - Settings クラス（環境変数の取得・検証）、自動 .env ロード実装

- config_setup.py
  - .env を対話式に作成するウィザード

- validate_config.py
  - 起動前チェック CLI（必須環境変数、パス、YAML の基本検証）

- run_execution.py
  - ExecutionEngine 起動スクリプト（本番/ペーパートレード切替、PID/stop フラグ処理）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整）

- utils/
  - logging_setup.py — ログ設定（stdout + 日次ファイルローテーション）
  - process_priority.py — プロセス優先度 & CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite のスキーマ初期化・アクセスラッパ
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - trade_monitor.py — 発注ログの監視（滞留注文、約定異常など）
  - risk_monitor.py — ドローダウン / ポジション上限チェック
  - kill_switch.py — Kill Switch 実装（flag ファイル操作）
  - monitoring_engine.py — 各 Monitor を束ねるエンジン

- execution/ (発注関連：OrderManager, Reconciler, RiskManager 等)
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py
  - （発注フローとブローカー抽象化）

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - ポートフォリオ構築・株数算出・セクター制約等の純粋関数群

- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター計算、IC や統計サマリー

- ai/
  - news_nlp.py — ニュースを LLM でセンチメント化して ai_scores に書き込む
  - regime_detector.py — ETF MA と LLM を組み合わせた市場レジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

追加の運用メモ
----------------
- デーモン化 / サービス化：systemd / supervisor / docker 等で run_monitoring/run_execution を管理する想定です。ログは stdout とファイル両方に出ますのでリダイレクト / journalctl 監視が可能です。
- アクセス権限：process_priority の設定はプラットフォームと実行権限に依存します。AccessDenied が発生した場合は警告が出て続行します。
- DB バックアップ/保持：monitoring DB（SQLite）はローカルファイルです。長期保存・分析を行う際は定期的にバックアップしてください。
- 本番注意点：KABUSYS_ENV=live の場合、LINE 通知や kill flag の設定など本番向け警告が出ます。JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD は絶対に Git 等に保存しないでください。

問い合わせ・貢献
----------------
コードの改善提案・バグ報告は issue を作成してください。Pull Request は歓迎します。README での記載漏れや不明点があればお知らせください。

以上で README の概要になります。必要であれば、ここに「.env.example」のサンプル、より詳細な systemd ユニット例、Dockerfile / docker-compose の例などを追加で作成できます。どのドキュメントを優先的に追加したいか教えてください。