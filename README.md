README — KabuSys（日本株自動売買システム）
==================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なフレームワークです。
主な機能として、シグナル → ポートフォリオ構築 → 発注の実行パイプライン（paper/live 対応）、
実行中の監視・アラート・Kill Switch、ファクター計算やリサーチ用ユーティリティ、LLM を用いたニュースセンチメント評価を備えます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - KABUSYS_ENV による切替: development / paper_trading / live
  - paper_trading モードでは MockBroker を使用し本番 DB と完全分離（data/paper_trading.db）
  - リスク管理・注文管理・再整合（reconciler）機能を備える

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - 定期ポーリングでシステム状態、注文滞留、ドローダウン等を監視
  - Kill Switch（条件成立時に data/kill.flag を書き込み ExecutionEngine を停止）

- Portfolio モジュール（純粋関数）
  - 候補選定、等分配・スコア加重、リスク調整（セクター上限）、ポジションサイジング（単元丸め）
  - 再利用しやすい API（テスト容易）

- Research（DuckDB 利用）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ

- AI （OpenAI 連携）
  - news_nlp: ニュース記事を LLM（gpt-4o-mini）で評価し ai_scores に保存
  - regime_detector: ETF（1321）MA200 とマクロニュースを組み合わせて市場レジーム判定

- 運用ユーティリティ
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env / config/*.yaml の起動前検証 CLI
  - tools.paper_verification_report: Paper Trading 検証レポート生成

必要条件
--------
- Python 3.10+
- 推奨ライブラリ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証用、任意）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（kabuステーション API / OpenAI を利用する場合）

例:
pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作る:
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール:
   pip install duckdb psutil openai PyYAML

3. .env を作成（対話式ウィザード推奨）:
   python -m kabusys.config_setup
   - ウィザードが .env を生成します（デフォルト: プロジェクトルート/.env）
   - .env を絶対に Git 管理しないこと

4. 設定検証:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. データディレクトリの確認/作成:
   デフォルトでは data/ 配下のファイルを利用します（SQLite / PID / kill.flag 等）。
   必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を設定してください。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定振る舞い（instant / partial / never / reject）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が必要な場合）
- LOG_LEVEL / LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動・ツール）
--------------------
- ExecutionEngine 起動（デーモンではなくプロセス実行）:
  python -m kabusys.run_execution

  注意:
  - 起動時に data/stop_requested.flag があると開始せず終了します。
  - 実行中は data/execution.pid に PID が書き込まれます。
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading DB（data/paper_trading.db）へ記録します。

- Monitoring 起動（ポーリング）:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更できます。
  - 監視は本番の sqlite_path を参照（KABUSYS_ENV に依存せず同じ監視 DB を使用します）。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB パス指定可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先的に参照します。

運用メモ / 注意点
----------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では Kill Switch（KILL_FLAG）やログ設定を慎重に扱ってください。
- OpenAI 使用部分は API キーと利用料が発生します。API レスポンスに依存する処理はフォールバックを実装済みですが、運用時は監視を強化してください。
- ログはデフォルト logs/ に日次ローテートで出力されます（TimedRotatingFileHandler、30日保持）。

ディレクトリ構成（主なファイル）
------------------------------
以下は主要モジュールの一覧（src/kabusys 配下）です。実際のリポジトリではさらに細分化されたファイルが含まれます。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・自動 .env ロード・Settings クラス
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

  - execution/                 — 発注エンジン関連（OrderManager, BrokerFactory, ExecutionEngine 等）
    - (execution_engine, order_manager, order_repository, risk_manager, reconciler, broker_factory など)

  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         — 通知ロジック（LINE などの通知を担う想定）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py       — モメンタム / ボラティリティ / バリュー計算（DuckDB 利用）
    - feature_exploration.py   — forward returns, IC, summary 等
    - __init__.py

  - ai/
    - news_nlp.py              — ニュースを LLM でスコア化して ai_scores に保存
    - regime_detector.py       — 市場レジーム判定（1321 MA200 + マクロセンチメント）
    - __init__.py

  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成ツール
    - __init__.py

  - utils/
    - logging_setup.py         — ログ設定ユーティリティ（Stream + RotatingFile）
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
    - __init__.py

- data/                        — デフォルトの DB / PID / flag ファイルを配置（実行時に生成される）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid

追加情報（開発者向け）
--------------------
- duckdb 接続を受け取る設計のため、研究コードは本番 DB に対して読み取り専用で動作する想定です。
- モジュール設計は単体テストが容易となるよう副作用を抑えています（純粋関数や外部依存の注入）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス・貢献
----------------
- 本 README 内の実装説明はコードベースに基づく概要です。実際のライセンス情報や貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

問題報告・質問
--------------
不具合や質問は issue を立ててください。簡単な再現手順やログ、使用環境（Python バージョン・OS・env 設定）を併せて記載いただけると早く対応できます。