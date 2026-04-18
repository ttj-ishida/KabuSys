README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の軽量実装です。  
主な目的は以下:

- 日次/リアルタイムの監視（System / Trade / Risk）
- 注文実行エンジン（本番 / ペーパートレード切替）
- ポートフォリオ構築（シグナル選定・重み付け・株数決定）
- リサーチ（ファクター計算、特徴量解析）
- AI を使ったニュースセンチメント評価・レジーム判定
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

機能一覧
--------
- 設定管理
  - .env / 環境変数の自動読み込み（.env.local 優先）
  - 対話式ウィザードで .env を生成する CLI（kabusys.config_setup）
  - 起動前に設定の整合性を検証する CLI（kabusys.validate_config）
- 実行関連
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に分離
    - プロセス優先度設定、PID ファイル出力、停止フラグ対応
- 監視関連
  - System / Trade / Risk をまとめてポーリングする MonitoringEngine
  - run_monitoring スクリプトで監視ループを常駐実行（MONITOR_POLL_INTERVAL で間隔変更可）
  - kill.flag による ExecutionEngine 停止（Kill Switch）
  - monitoring DB（SQLite）によるログ永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- ポートフォリオ構築
  - 候補選定・スコア重み付け・等重み計算
  - セクター制約、レジーム乗数
  - 株数計算（単元丸め、Risk-based / equal / score 方式）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いて prices_daily 等を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュースを OpenAI（gpt-4o-mini 等）でセンチメント評価して ai_scores に書き込む
  - ETF（1321）MA とマクロニュースの組合せで市場レジーム判定し market_regime に書き込む
  - API 呼び出しはリトライ、フォールバックを実装（フェイルセーフ設計）
- ツール
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）

前提要件（主な依存）
-------------------
- Python 3.10+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証時に任意）

セットアップ手順
----------------

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  # (Windows は .venv\Scripts\activate)

2. 必要なパッケージをインストールします（例）。
   - pip install duckdb psutil openai pyyaml

3. .env を用意します。推奨は対話式ウィザード:
   - python -m kabusys.config_setup
   ウィザードは .env を生成し、J-Quants / kabuAPI 等の必須項目を入力できます。

4. 設定検証（任意／推奨）:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

主要な環境変数（代表）
----------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨/任意:
  - KABUSYS_ENV: execution 環境。development / paper_trading / live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時の DB）
  - PAPER_FILL_MODE: ペーパートレードでの約定モード ("instant" / "partial" / "never" / "reject")
  - OPENAI_API_KEY: OpenAI を使う場合の API キー
  - LOG_LEVEL, LOG_DIR
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、本番は 0 推奨）

使い方
------

- 実行エンジン（ExecutionEngine）起動（常駐は内部でスレッド実行）:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録され、本番 DB とは分離されます。

- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path を使用（環境に依存せず logging/monitoring は本番 DB に記録される設計）

- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （環境変数 PAPER_TRADING_SQLITE_PATH が優先される）

停止・Kill Switch
-----------------
- 実行中のエンジン/監視の停止:
  - プロジェクト内 data/stop_requested.flag を作成すると run_monitoring / run_execution のループは検知して終了します。
  - Kill Switch: リスク監視がトリガーすると data/kill.flag が書き込まれ、ExecutionEngine はこれを検知して停止します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では推奨しません）。

ログ
---
- ログはデフォルトで logs/ に出力され、日次ローテーション（30日保持）されます。
- LOG_DIR と LOG_LEVEL 環境変数で変更可。
- コンソール出力は stdout に送られます。

主なファイル / ディレクトリ構成
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数・Settings 管理（.env 自動読み込み含む）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 起動前設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリングスクリプト

サブパッケージ（主要モジュール）
- ai/
  - news_nlp.py             — ニュースの LLM センチメント処理
  - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（テーブル定義・CRUD ユーティリティ）
  - system_monitor.py       — システム状態・データ鮮度監視
  - trade_monitor.py        — （取引監視ロジック）
  - risk_monitor.py         — ドローダウン・ポジション上限監視
  - kill_switch.py          — kill.flag 書込みロジック
  - monitoring_engine.py    — 各モニターを束ねるエンジン
  - alert_manager.py        — （アラート送信ロジック）
- execution/
  - execution_engine.py     — 実行エンジン本体（EngineConfig を受け取る）
  - broker_factory.py       — ブローカークライアント生成（本番 / mock 切替）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py    — 候補選定・重み付け
  - position_sizing.py      — 株数・投下金額決定
  - risk_adjustment.py      — セクター上限・レジーム乗数
- research/
  - factor_research.py      — ファクター計算（momentum / volatility / value）
  - feature_exploration.py  — 将来リターン・IC・統計サマリー
- data/
  - pipeline.py (参照される想定) — prices_daily 取得等（DuckDB 周り）
  - stats.py (zscore_normalize 等)
- utils/
  - logging_setup.py        — ログ設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

注意事項 / 運用上のポイント
-------------------------
- .env は機密情報を含むため決してリポジトリにコミットしないでください。
- KABUSYS_ENV が live の場合は本番設定になります。LINE 通知などの設定漏れがないか validate_config で確認してください。
- ペーパートレードは本番 DB から完全に分離される設計（PAPER_TRADING_SQLITE_PATH）。
- AI（OpenAI）呼び出しはレート制限や失敗に対するリトライを実装していますが、API キーやコスト管理は運用者が行ってください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（run 環境の権限に注意）。

サンプルコマンドまとめ
---------------------
- .env 作成（ウィザード）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - export MONITOR_POLL_INTERVAL=60
  - python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
この README はリポジトリ内のドキュメントやソースコードの docstring を基に要点をまとめたものです。各モジュール内の docstring／コメントに設計意図や制約が記載されていますので、実装や拡張時には併せて参照してください。質問や改善点があればお知らせください。