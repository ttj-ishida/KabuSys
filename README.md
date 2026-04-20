# KabuSys

日本株自動売買システム（KabuSys）のコードベース README（日本語）

このドキュメントはリポジトリ内の主要スクリプト／モジュールの概要、セットアップ方法、起動方法、およびディレクトリ構成をまとめたものです。

注意: 実行には Python 3.9+（型注釈の表記などに依存）と外部ライブラリ（duckdb, psutil, openai など）が必要です。実環境での運用は十分に注意して行ってください（特に KABUSYS_ENV=live の場合は実売買が行われます）。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ基盤です。主な機能は以下の通りです。

- シグナル生成・ポートフォリオ構築・ポジションサイズ計算（portfolio モジュール）
- 市場レジーム判定・ニュース NLP を用いたマクロ／銘柄センチメント評価（ai モジュール）
- DuckDB を使ったファクター計算・探索（research モジュール）
- 実行エンジン（ExecutionEngine）による発注管理・リスク管理（execution パッケージ）
- 監視（Monitoring）: システム状態、オーダー／リスク監視、Kill Switch（monitoring パッケージ）
- ペーパートレード用検証レポート生成ツール（tools）
- 環境設定ウィザード・設定検証 CLI（config_setup / validate_config）

---

## 主な機能一覧

- ポートフォリオ構築
  - 候補選定（スコア降順）、等分配・スコア加重配分
  - セクター上限フィルタ、レジーム乗数
  - 各種発注株数計算（単元丸め、risk-based 等）
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI）連携
  - ニュース記事から銘柄センチメントを算出して ai_scores に保存
  - マクロニュース + ETF MA200 を使った市場レジーム判定
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を実装
- 実行・監視
  - ExecutionEngine（発注・注文管理・リスク）起動スクリプト
  - Monitoring サービス（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch）
  - kill.flag による外部停止シグナル、stop_requested.flag によるプロセス終了
- 運用支援
  - .env 対話的作成ツール（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート（tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストールします。
   - 要件ファイルがプロジェクトに含まれている場合:
     - pip install -r requirements.txt
   - 最低限必要なパッケージ（例）:
     - pip install duckdb psutil openai PyYAML

   注: 実行に必要なパッケージは機能によって異なります（AI 機能は openai、YAML 検証は PyYAML 等）。

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   - ウィザードは J-Quants のリフレッシュトークンや kabuステーション API パスワード、DB パス等を設定します。
   - 生成された .env は絶対に Git にコミットしないでください。

4. 設定を検証します。
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. 必要に応じて data/ ディレクトリを作成してください（SQLite / pid / flag 等のファイル用）。
   - 例: mkdir -p data logs

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録
  - live: 実際の発注が実行される
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用データベースのパス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 DB（デフォルト: data/paper_trading.db）
- LOG_LEVEL — デフォルト INFO
- OPENAI_API_KEY — OpenAI API を使用する機能で必要
- PAPER_FILL_MODE — paper_trading 時のモック約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- その他: LOG_DIR, PID_FILE_PATH, KILL_FLAG_PATH など（Settings クラスを参照）

---

## 使い方（主なコマンド）

各スクリプトはパッケージモジュールとして実行可能です。

- 環境設定ウィザード（.env の作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動を中止
    - 停止は stop_requested.flag を作成するか、KillSwitch による data/kill.flag でトリガーされます

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
    - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存しない）
    - stop_requested.flag が存在すると監視ループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を使用）

- AI / レジーム判定・ニューススコアリング（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key 引数または環境変数 OPENAI_API_KEY が必要

ログ:
- ログは logs/<app_name>.log に日次ローテーションで出力されます（utils.logging_setup.setup_logging を使用）。
- コンソール出力は stdout に流れます。

フラグ／PID ファイル:
- 停止要求: data/stop_requested.flag（run_execution/run_monitoring が監視）
- Kill Switch: data/kill.flag（KillSwitch が作成）
- 実行エンジン PID: data/execution.pid

kill.flag を手動で削除する場合:
- rm data/kill.flag（または Windows なら del）

---

## 運用上の注意

- KABUSYS_ENV=live の場合は実際に発注が行われるので、必ず設定（API トークン・LINE 通知等）を確認してください。
- .env は機密情報を含むため絶対にリポジトリに含めないでください。
- OPENAI 呼び出しはコストとレート制限に注意してください（リトライ・バッチ処理の実装あり）。
- Monitoring は監視ログ用の SQLite（Settings.sqlite_path）に書き込みます。ペーパートレードとは分離して運用してください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下のおもなファイル・パッケージの概要です（完全なツリーではありません）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定読み込みロジック（Settings クラス）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で銘柄スコア算出
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
    - __init__.py
  - research/
    - factor_research.py     — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
    - __init__.py
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み計算
    - position_sizing.py     — 発注株数計算（単元丸め・aggregate cap 等）
    - risk_adjustment.py     — セクター上限・レジーム乗数
    - __init__.py
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化 / 永続化層（MonitoringDB）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （trade 監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — モニタリングの統合実行ループ
    - alert_manager.py       — （アラート通知の管理）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig, ExecutionEngine）
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py       — 共通ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定
    - __init__.py

（上記は主要ファイルのみ抜粋。細かいユーティリティや補助モジュールも含まれます。）

---

## よく使う開発フロー（例）

1. .env を作成: python -m kabusys.config_setup
2. 設定を検証: python -m kabusys.validate_config
3. 開発時（データ作成・分析）:
   - DuckDB を準備し、research モジュールでファクター計算を行う
4. ペーパートレード実行:
   - KABUSYS_ENV=paper_trading を設定し、python -m kabusys.run_execution を起動
   - 別ターミナルで python -m kabusys.run_monitoring を起動して監視
5. レポート生成:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

---

## 参考事項 / 開発メモ

- Settings クラスによりデフォルトパスが決まっています（DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db、PAPER_TRADING_SQLITE_PATH=data/paper_trading.db）。
- monitoring::init_monitoring_db はスキーマ作成を冪等に行います（既存 DB に対するマイグレーションも一部含む）。
- utils.logging_setup.setup_logging を各起動スクリプトで呼び出すことでログ出力が統一されます。
- process_priority.set_process_priority はプラットフォーム差分（Windows / POSIX）を吸収して優先度設定を試行します（権限不足時は警告でスキップ）。

---

必要であれば README に「実行例」「.env の雛形」「詳細な設定項目一覧（config_setup の項目に基づく）」や、unit テストの実行方法、CI の設定例などを追加します。どの内容を深掘りしたいか教えてください。