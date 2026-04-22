KabuSys — 日本株自動売買システム / README
========================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのシステムです。本リポジトリは以下の主要機能群を含みます:
- 発注エンジン（ExecutionEngine）とブローカー抽象化（実取引 / ペーパートレード対応）
- 監視サブシステム（System / Trade / Risk の定期チェック、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、株数決定、リスク調整）
- リサーチモジュール（ファクター計算、特徴量探索、IC計算）
- AI モジュール（ニュース NLP による銘柄センチメント、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

主な特徴
--------
- 環境別分離: KABUSYS_ENV により development / paper_trading / live を切替。ペーパートレード時は専用 SQLite DB を使用して本番 DB と分離。
- フェイルセーフ: LLM/API 呼び出し失敗時は安全なフォールバックを行い、システムを停止させない設計。
- ロギング: 統一的なログ設定 (console + 日次ローテーション)。
- 監視と Kill Switch: ドローダウンやポジション上限などの条件で自動的に発注エンジンの停止フラグを立てる。
- DuckDB を利用した分析用ストレージ（prices_daily / raw_financials 等想定）。
- 純粋関数中心のポートフォリオ構成・サイズ計算（テストしやすい実装）。

セットアップ手順
----------------
前提: Python 3.9+（推奨）。以下はローカル開発向けの例です。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   代表的な必要モジュール:
   - duckdb
   - psutil
   - openai
   - PyYAML（config YAML の検証に任意）
   例:
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本リポジトリに含まれていない場合があるため、上記を手動でインストールしてください。

4. 環境変数設定
   - .env を作成（./config_setup.py のウィザードを推奨）
     - python -m kabusys.config_setup
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - 推奨: KABUSYS_ENV（development / paper_trading / live）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も許容しない厳密チェック:
     - python -m kabusys.validate_config --strict

6. データディレクトリとログディレクトリ
   - デフォルトでは data/ と logs/ を使用します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。

基本的な環境変数（主なもの）
------------------------------
（デフォルト値は Settings クラスに定義されているものに準拠）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 環境 & ロギング
  - KABUSYS_ENV (default: development) — development / paper_trading / live
  - LOG_LEVEL (default: INFO)

- DB / ファイルパス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db) — 監視 DB（monitoring は常に本番 sqlite_path を参照）
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db) — paper_trading 時に使用
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (default: 0) — 起動時に kill.flag を自動クリアするか

- その他
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、default: 60）
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能使用時必須）

使い方（主要コマンド）
--------------------

1. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   -> .env を生成し、保存後に validate_config を実行することを推奨。

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict  （警告もエラー扱い）

3. Execution エンジン（発注）起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に書き込まれます。
   - 起動後は data/execution.pid が作成される想定。停止させるには data/stop_requested.flag を作成するか、Kill Switch により data/kill.flag が作成されるとエンジンを停止します。

4. Monitoring（監視）起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可（デフォルト: 60）。
   - run_monitoring は monitoring のために常に production 用 sqlite_path を使用します（監視ログを本番 DB に残すため）。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

6. AI 機能（ニュース NLP / レジーム判定）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key="...")  （api_key が None の場合は環境変数 OPENAI_API_KEY を参照）
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key="...")

注意点・運用上のポイント
-----------------------
- monitoring は常に本番 sqlite_path を参照します（環境に依らない）。監視データを別に保ちたい場合は sqlite_path を変更してください。
- run_execution は KABUSYS_ENV=paper_trading のとき専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。これにより本番 DB と完全分離されます。
- Kill Switch: risk_monitor/risk_checks がトリガーすると data/kill.flag に理由を書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアしますが、本番では 0 を推奨します。
- OpenAI 呼び出しには API 制限やエラーが発生します。AI モジュールはリトライ・フォールバックを備えていますが、API キーの管理やコストに注意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルト 30 日保持）。

主要ディレクトリ構成
-------------------
（src/kabusys 以下の主要ファイル / モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env ウィザード（対話式）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）

  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status / trade_logs / risk_logs / positions / dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （例: 滞留注文 / 約定異常検出 — 実装ファイルあり）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — フラグファイルを書き込む Kill Switch
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （アラート送信ロジック: LINE など）（実装ファイルあり）

  - execution/
    - execution_engine.py    — ExecutionEngine（エンジン本体: run_session 等）
    - broker_factory.py      — ブローカクライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py     — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ

  - data/
    - pipeline.py            — データパイプライン関連（get_last_price_date など）

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定

  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成

運用・トラブルシューティング
-----------------------------
- PyYAML 未インストール: validate_config は YAML の内容チェックをスキップします（警告）。
- psutil の一部機能（プロセス優先度 / cpu_affinity）は権限が必要です。AccessDenied で警告が出ますが動作は継続します。
- DuckDB の executemany は空リストを受け付けないバージョンがあります（コードはその互換性に配慮しています）。
- OpenAI API の利用に伴うエラー（429 / タイムアウト / 5xx）はリトライロジックがありますが、長時間失敗した場合は AI 機能はスキップされます。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期版）。

最後に
------
この README はリポジトリ内の主要モジュールと実行フローの概要、基本的なセットアップ・運用手順をまとめたものです。細かい設計や API の使い方は各モジュール内の docstring / コメントを参照してください。必要であれば、README に追記すべき項目（例: 実行例、systemd ユニット、CI 設定、詳細な .env.example）を教えてください。