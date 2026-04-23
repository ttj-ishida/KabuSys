KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システム／研究ライブラリ群です。  
このリポジトリには、実行（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・ファクター計算・AI（ニュースセンチメント／レジーム判定）・運用支援ツール（設定ウィザード・検証レポート等）が含まれます。

主要な設計方針（抜粋）
- 本番／ペーパートレードを切り替え可能（KABUSYS_ENV）。
- DuckDB を分析用データベース、SQLite を監視／発注ログ保存用に利用。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント／レジーム判定機能を備える（API キー必須）。
- ロギングは統一的に設定（logs/ 日次ローテーション）し、プロセス優先度等も制御可能。
- .env を用いた環境設定、対話式ウィザード・事前検証 CLI を提供。

主な機能
-------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB を利用。
  - 停止フラグ（data/stop_requested.flag）で安全にシャットダウン可能。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - システムリソース監視、データ鮮度チェック、取引ログ監視、リスク監視、Kill Switch など。
  - 監視結果・ログは SQLite（デフォルト data/monitoring.db）へ永続化。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等重・スコア加重、セクター上限適用、レジーム乗数、発注株数決定（ロット丸め、aggregate cap 対応）。
- 研究用モジュール（research パッケージ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン、IC 計算、統計サマリー。
  - DuckDB 接続を受け、prices_daily / raw_financials テーブル等を参照して計算。
- AI 機能（ai パッケージ）
  - news_nlp: ニュース記事を LLM でセンチメント評価し ai_scores を書き込み。
  - regime_detector: MA200 乖離 + マクロニュースセンチメントを合成して日次レジーム判定を行い market_regime に書き込み。
  - OpenAI API 呼び出し時のリトライ・バリデーション実装あり（失敗時はフェイルセーフで継続）。
- 運用支援ツール
  - 対話式 .env ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成スクリプト（tools/paper_verification_report.py）

セットアップ手順
----------------
前提
- Python 3.9+（コードは型注釈・モジュール構成を前提）
- system の前提パッケージ: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定検証で YAML を解析する場合）

推奨手順（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （オプション）pip install pyyaml

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参考にしてください）。
   - 重要: .env は機密情報を含むため Git にコミットしないでください。

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番前に --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

5. DB の確認
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db (KABUSYS_ENV=paper_trading 時)
   - 必要に応じてディレクトリ data/ を作成してください（logging_setup が自動作成する場合あり）。

使い方
------
主要スクリプトの実行例（プロジェクトルートで実行することを想定）

- ExecutionEngine を起動
  - 環境変数で実行モードを切替:
    - 開発（発注なし）: export KABUSYS_ENV=development
    - ペーパートレード: export KABUSYS_ENV=paper_trading
    - 本番: export KABUSYS_ENV=live
  - 実行:
    - python -m kabusys.run_execution
  - ペーパートレード時は PAPER_TRADING_SQLITE_PATH（または .env の PAPER_TRADING_SQLITE_PATH）で DB を指定可能。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中に stop flag を作成すると安全に停止します（data/stop_requested.flag）。

- Monitoring を起動
  - ポーリング間隔を指定（秒）:
    - export MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依存せず本番監視 DB を使用する設計）。
  - 監視プロセスは process priority を high に設定し、ログは logs/ に出力されます。

- .env の作成/更新ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗扱いにできます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH も使用可能）。

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してください。
  - 例（レジーム判定）:
    - python -c "from datetime import date; import duckdb; from kabusys.ai.regime_detector import score_regime; conn = duckdb.connect('data/kabusys.duckdb'); score_regime(conn, date(2026,4,1), api_key=None)"
  - news_nlp と regime_detector は DuckDB 上の raw_news / news_symbols / prices_daily 等を参照します。

運用上のファイル・フラグ
- data/stop_requested.flag
  - run_execution / run_monitoring が監視する停止フラグ（存在すると起動しないか停止処理を行います）。
- data/execution.pid
  - 実行エンジンが書き込む PID ファイルパス（Settings.pid_file_path が参照）。
- data/kill.flag
  - KillSwitch が書き込む停止フラグ（本番停止のために使用）。
- logs/
  - 日次ローテート（30日保持）でログファイルを出力。

ディレクトリ構成
----------------
以下は主要なディレクトリ / ファイルの概略（src/kabusys 以下）。実際のリポジトリはこの構成を反映します。

- src/kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor 起動スクリプト
  - config.py                  — 環境変数 / Settings 管理（.env 自動読み込み含む）
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート生成スクリプト
  - utils/
    - logging_setup.py         — ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py         — SQLite 永続化層（監視ログ）
    - system_monitor.py        — システム監視（CPU / メモリ / データ鮮度）
    - trade_monitor.py         — 取引監視（滞留注文・約定異常など）※実装参照
    - risk_monitor.py          — ドローダウン / ポジション上限チェック
    - kill_switch.py           — Kill switch フラグ制御
    - monitoring_engine.py     — 各 Monitor を束ねる実行ループ
    - alert_manager.py         — アラート送信管理（LINE 等）※実装参照
  - execution/
    - execution_engine.py      — ExecutionEngine（発注ループ等）※実装参照
    - order_manager.py         — 注文管理
    - order_repository.py      — 注文永続化
    - reconciler.py            — ブローカー状態差分解消
    - broker_factory.py        — ブローカークライアントの生成（Mock を含む）
    - risk_manager.py          — 発注リスク制御
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・スケーリング・ロット丸め
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py              — ニュース NLP（センチメント評価）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/                      — (運用時に使用) DB・フラグ・PID 保存ディレクトリ（デフォルト）
  - logs/                      — ログ出力先（デフォルト）

注意事項 / ベストプラクティス
-----------------------------
- .env には API キー・パスワード等の機密が含まれます。決してリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨します（自動クリアは危険）。
- OpenAI を使う機能は API 利用料が発生します。テスト環境ではモックや少量のバッチで確認してください。
- DuckDB / SQLite ファイルはバックアップや取り扱いに注意してください（特に本番データ）。
- ロギング・PID・フラグファイルのパスは Settings でカスタマイズできます。

サポート / 追加情報
-------------------
- コード内ドキュメント（各モジュールの docstring）に設計意図・入力/出力仕様が詳述されています。実装参照を推奨します。
- テスト・CI の実装に合わせて KABUSYS_DISABLE_AUTO_ENV_LOAD を使い .env の自動ロードを回避できます（テスト用）。

---
この README はリポジトリ内の主要モジュール群に基づいて作成しています。実際に利用する際は各モジュールの docstring と設定ファイル（config/*.yaml が存在する場合）を併せてご確認ください。