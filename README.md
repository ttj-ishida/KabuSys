README
======

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリには、注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI（ニュース NLP / レジーム判定）など、売買システム運用に必要な主要コンポーネントが含まれます。設計方針としては「本番と分析を分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に制御する」ことを重視しています。

主な機能
--------
- Execution（run_execution.py）
  - ブローカークライアントの抽象化（本番 / ペーパートレードの分離）
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）を使用

- Monitoring（run_monitoring.py / monitoring/*）
  - システム状態（CPU/メモリ/ディスク）やデータ鮮度の監視
  - 注文ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch（閾値超過時に data/kill.flag を書き込み、ExecutionEngine を停止）
  - MonitoringEngine による定期ポーリング（ポーリング間隔は環境変数で調整可能）

- Portfolio（portfolio/*）
  - 候補選定（スコア順）・重み計算（等配分 / スコア加重）
  - セクター集中制限の適用、レジーム乗数の計算
  - ポジションサイズ計算（リスクベース、ロット丸め、集約キャップ適用）

- Research（research/*）
  - DuckDB を用いたファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
  - DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルのみ参照

- AI（ai/*）
  - ニュース NLP（OpenAI を用いた銘柄別センチメント評価）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
  - API レート制限やエラーへエクスポネンシャルバックオフで対処

- ユーティリティ
  - 環境設定ウィザード（config_setup.py）: .env の対話的作成・更新
  - 設定検証 CLI（validate_config.py）: .env と config/*.yaml の事前チェック
  - ロギング設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度・CPU affinity 設定（utils/process_priority.py）
  - Paper Trading レポート生成ツール（tools/paper_verification_report.py）

前提・依存
----------
（プロジェクト側で requirements.txt がないため、主要依存を記載します）
- Python 3.9+（型注釈や一部ライブラリの利用を想定）
- duckdb
- psutil
- openai (AI 機能使用時)
- PyYAML（config/*.yaml の内容検証を行う場合に任意）
- sqlite3（標準ライブラリ）

セットアップ手順
----------------
1. レポジトリをクローンし、仮想環境を作成・有効化します:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストールします（例）:
   - pip install duckdb psutil openai pyyaml

   ※ 本番で AI 機能を使わない場合は openai は不要です。PyYAML は optional（validate_config の YAML 検証用）。

3. .env を作成します（推奨手順）:
   - python -m kabusys.config_setup
     - 対話形式で .env を生成します（.env は絶対に Git にコミットしないでください）。
   - 設定の検証:
     - python -m kabusys.validate_config
     - 必須環境変数やファイルパスの基本チェックを行います。

4. データディレクトリ準備:
   - デフォルトでは data/ 下に DB ファイル・フラグファイル等を置きます。必要に応じてディレクトリを作成してください。ログは logs/ に保存されます（LOG_DIR 環境変数で変更可）。

主要環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: execution 動作モード（development|paper_trading|live、デフォルト: development）
  - paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite を使います
- OPENAI_API_KEY: AI 機能を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ロギング設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）

使い方（起動・主要スクリプト）
-----------------------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）として扱う

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB を使用し MockBrokerClient が使われます
    - 実行中に data/stop_requested.flag を作成するとエンジンは安全に停止します
    - 実行時には data/execution.pid が生成されます（pid ファイルパスは Settings を参照）

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用する点に注意

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で別パス指定可。

- AI モジュールの利用方法（プログラム的呼び出し例）:
  - from kabusys.ai.news_nlp import score_news
  - duckdb_conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(duckdb_conn, target_date=date(2026, 4, 10), api_key=os.environ["OPENAI_API_KEY"])

停止・Kill Switch
-----------------
- Kill Switch: リスク条件（ドローダウンやポジション上限超過）に応じて data/kill.flag が書き込まれます。ExecutionEngine 起動時にこれがあると起動を回避、または起動後に検知すると停止を行います。
- 手動停止: run_execution/run_monitoring はそれぞれ data/stop_requested.flag の存在を監視しているため、このファイルを作成するとループを抜けて終了します（安全停止）。

ディレクトリ構成（概要）
----------------------
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 & 設定読み込みロジック（.env 自動ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py       — 統一ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（monitoring 用テーブル定義・API）
    - system_monitor.py      — システム状態 & データ鮮度監視
    - trade_monitor.py       — （注文関連監視: 滞留・約定異常 等）※実装ファイルを参照
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — 通知管理（LINE など）※実装ファイルを参照
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（セッション管理）
    - order_manager.py       — 発注管理
    - order_repository.py    — 注文履歴操作
    - reconciler.py          — ブローカーとリポジトリ整合処理
    - broker_factory.py      — BrokerClient 作成（本番 / モック切替）
    - risk_manager.py        — リスク管理ロジック
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・ラウンド処理
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム / ボラティリティ / バリュー等計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・集約・書き込み）
    - regime_detector.py     — レジーム判定（MA + マクロセンチメント）
  - data/ (実行時に使用・生成されることが想定)
    - monitoring.db (default)
    - paper_trading.db (paper mode)
    - kill.flag, stop_requested.flag, execution.pid, ...
  - logs/ (デフォルトロギングディレクトリ)

注意事項・運用上のポイント
--------------------------
- .env はセキュアに管理してください（API キーやパスワードが含まれます）。絶対に Git にコミットしないでください。
- KABUSYS_ENV=live のときは本番資金での発注が行われます。validate_config の警告を特に確認してください（LINE 通知や Kill Switch 設定等）。
- Monitoring は監視 DB（SQLITE_PATH）を使用します。run_monitoring は KABUSYS_ENV に関わらず sqlite_path を参照する設計になっています（監視は本番 DB を想定）。
- AI 機能（news_nlp, regime_detector）は OpenAI API の利用制約に従います。API キーの管理と料金に注意してください。API 呼び出しエラーはフェイルセーフ（無視・フォールバック）される設計ですが、想定外のケースに備えてログを監視してください。
- DuckDB テーブル（prices_daily, raw_financials, raw_news, ai_scores, market_regime など）は事前に ETL / データパイプラインで充足しておく必要があります。research / ai モジュールはこれらのテーブルを前提に動作します。

貢献・拡張
----------
- 新しいブローカー実装は execution/broker_factory.py の拡張で対応できます。
- 追加のモニタリングルールや通知チャネルは monitoring/ 以下に AlertManager 実装を追加してください。
- DuckDB スキーマの変更や新しいリサーチ関数の追加は research/ に機能を追加することで拡張可能です。

ライセンス
----------
- 本リポジトリにはライセンスファイルが含まれていないため、社内利用や配布の前にライセンス方針を確認してください。

お問い合わせ
-------------
実行やセットアップで不明点があれば、ソース内の docstring（各モジュール冒頭）やログ出力を参照してください。特定の機能についての詳しいドキュメントが必要であれば、どのモジュール（例: ai.news_nlp / portfolio.position_sizing / monitoring.monitoring_db）についてのドキュメントを拡張したいかを教えてください。