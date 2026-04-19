README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。取引実行（ExecutionEngine）、監視（Monitoring）、リサーチ、ポートフォリオ構築、AI を用いたニュース解析などのコンポーネントを含みます。設計方針として「本番・ペーパートレードの分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API 失敗時は安全にフォールバック）」を重視しています。

主な特徴
--------
- ExecutionEngine：kabuステーション（またはペーパートレード用の MockBroker）と連携して発注を行う。
- Monitoring：システム状態（CPU/メモリ/ディスク・プロセス稼働）／注文ログ／リスク（ドローダウン・ポジション上限）を定期的に記録・監視し、Kill Switch により自動的に Execution を停止可能。
- Portfolio モジュール：候補銘柄選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数等の純粋関数群を提供。
- Research モジュール：DuckDB を使ったファクター計算（モメンタム・バリュー・ボラティリティ等）、将来リターンや IC の計算。
- AI モジュール：OpenAI（gpt-4o-mini）を用いたニュースセンチメント集約（ai_scores）や市場レジーム判定（market_regime）。
- ユーティリティ：.env 対話式ウィザード、設定検証ツール、ログ設定、プロセス優先度設定等。
- ツール：ペーパートレード検証レポート生成スクリプト（paper_verification_report）。

必要条件
--------
- Python 3.10+
- 推奨依存パッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証を有効にする場合）
- SQLite を使います（組み込み）。ログはデフォルトで logs/ に出力します。

セットアップ手順
----------------
1. リポジトリをクローン／取得
   - 例: git clone <repo>

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
   - ※ requirements.txt がある場合は pip install -r requirements.txt を推奨

4. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - 環境: KABUSYS_ENV を development / paper_trading / live のいずれかで指定
   - ウィザードで生成された .env は決して Git にコミットしないでください。

5. 設定の検証
   - python -m kabusys.validate_config
   - オプション --strict を付けると警告も失敗扱いになります。

6. データディレクトリ（logs/、data/ など）は自動作成されますが、必要に応じて事前に作成してください。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development / paper_trading / live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — AI モジュール利用時に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

使い方（実行例）
----------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と完全分離）。

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する例:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止・Kill Switch
----------------
- 監視ループ・エンジン停止用のフラグ:
  - data/stop_requested.flag : run_monitoring / run_execution が監視する「停止要求」フラグ。作成されるとループが終了します。
  - data/kill.flag : KillSwitch が書き込む「強制停止」フラグ（設定に応じて使用）。既定のパスは Settings.kill_flag_path（デフォルト: data/kill.flag）。
- Execution 起動時に kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START=1）があるため、本番では 0 を推奨します。

ログ
----
- デフォルトで logs/ にアプリケーションごとのログファイルを日次ローテーション（30日保持）で出力します。
- コンソール出力は stdout へ送られます（ジョブスケジューラ等で stdout をリダイレクトしやすくするため）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に構成されます。

重要な設計注意点
----------------
- 本プロジェクトはルックアヘッドバイアスを避ける設計（target_date 未満のデータのみを利用）を意識しています。AI / 日付処理は date.today() を直接参照しない実装方針です。
- Paper trading と Live（本番）は DB を分離して運用するようになっています（PAPER_TRADING_SQLITE_PATH）。
- AI（OpenAI）連携はフェイルセーフ：API 失敗時はフォールバックして処理を継続しますが、API キーが未設定だと明示的な例外を返す設計です。

ディレクトリ構成（主要ファイル）
----------------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — 監視 DB 永続化（SQLite）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 注文関連の監視（滞留注文・約定異常等）※（実装ファイルがある前提）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 monitor を束ねるエンジン
    - alert_manager.py       — アラート送信管理（LINE 等を想定）※（実装ファイルがある前提）
  - execution/                — Execution に関するモジュール群（broker, engine, order_manager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - data/                    — 実行時生成データ・DB・flag 等（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag 等）

追加情報・運用上のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では LINE 通知等が適切に設定されているか必ず validate_config で確認してください。
- Kill Switch（データ/kill.flag）や停止フラグの扱いは慎重に：KILL_FLAG_CLEAR_ON_START を誤って 1 にすると本番で kill.flag が自動的にクリアされるため危険です。
- DuckDB は分析用の高速ストレージとして想定されています。prices_daily / raw_financials / raw_news 等のテーブルを用いてリサーチ・AI 処理を行います。

貢献・開発
----------
- 新しい依存を追加した場合は requirements.txt を更新してください。
- コードのスタイル・型チェックはプロジェクト内の方針に従って行ってください（pyproject.toml 等がある場合はそちらを参照）。

ライセンス
---------
- 本ドキュメントにライセンス記述がないため、リポジトリの LICENSE ファイルを参照してください。

以上。必要に応じて README の補足（使用例のスクリーンショット、エンドツーエンドのセットアップ手順、CI/CD 用のコマンド等）を追記できます。質問や特定セクションの拡張を希望すれば教えてください。