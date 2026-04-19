# KabuSys — 日本株自動売買システム（README）

このリポジトリは日本株自動売買システム「KabuSys」の一部実装です。戦略・ポートフォリオ構築、監視・キルスイッチ、ペーパートレード検証、AI（ニュースNLP / レジーム判定）等のモジュールを含みます。

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（よく使うコマンド）
- 環境変数（主要設定）
- ファイル / ディレクトリ構成（概要）
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主要コンポーネントとして以下を備えます。

- ExecutionEngine（発注・注文管理・リスク管理） — run_execution.py
- Monitoring（システム状態・注文・リスク監視） — run_monitoring.py / MonitoringEngine
- Portfolio 構築（候補選定・重み付け・ポジションサイズ計算）
- Research（ファクター計算・特徴量探索）
- AI（ニュースセンチメントのスコアリング、レジーム判定） — OpenAI を利用
- ツール（ペーパートレードの検証レポート生成など）
- 設定ウィザード / 設定検証 CLI

この README はローカルでのセットアップと主要スクリプトの実行方法をまとめたものです。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成・更新）: kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml 検証）: kabusys.validate_config
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
- 監視ループ起動スクリプト: run_monitoring.py
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（デフォルト 60 秒）
- 監視 DB 管理（SQLite）: monitoring_db モジュール
- リスク監視（ドローダウン、ポジション上限）: RiskMonitor
- キルスイッチ（kill.flag を書き込んで Execution を停止）: KillSwitch
- AI モジュール
  - news_nlp: ニュースを OpenAI でセンチメント解析 → ai_scores に書き込み
  - regime_detector: マクロニュース + ETF MA から市場レジームを判定、market_regime に書き込み
- ペーパートレード検証レポート生成: kabusys.tools.paper_verification_report
- Portfolio 構築（候補選定、重み計算、ポジションサイズ計算、セクター制限など）
- Research（モメンタム / ボラティリティ / バリュー / IC 計算 等）

---

## セットアップ手順（開発 / ローカル実行）

1. Python 仮想環境を作成して有効化（例: venv / poetry 等）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 依存パッケージをインストール
   - このリポジトリに requirements.txt は含まれていませんが、最低限以下が必要です:
     - duckdb
     - psutil
     - openai
     - そのほか通常の Python 標準ライブラリ（sqlite3 等は標準）
   - 例:
     - pip install duckdb psutil openai
   - YAML の検証を行う場合は PyYAML を追加:
     - pip install pyyaml

3. .env を作成する
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - ウィザード後、設定を検証:
     - python -m kabusys.validate_config
     - 本番検証を厳密に行う場合は --strict を付与

4. データディレクトリの準備（必要に応じて）
   - デフォルトの DB / PID / ログ等はプロジェクトルート直下の `data/` / `logs/` を使用します。自動的に作成されることが多いですが権限等に注意してください。

---

## 使い方（コマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - すべての警告を失敗扱いにする: python -m kabusys.validate_config --strict

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB（環境変数 PAPER_TRADING_SQLITE_PATH で指定）を使います。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=...) — OpenAI API キーが必要
  - regime_detector.score_regime(conn, target_date, api_key=...) — OpenAI API キーが必要
  - OPENAI_API_KEY を環境変数で渡すことも可能

停止 / キル操作:
- 実行ループ（run_monitoring / run_execution）はプロジェクトルートの data/stop_requested.flag の存在を検知して安全に停止します（手動で作成すると停止処理が行われます）。
- KillSwitch（自動的に書き込まれる場合）: data/kill.flag が作成されると ExecutionEngine に対する「即時停止シグナル」相当となります。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされます（本番では推奨しません）。

ログ:
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（logs ディレクトリ）。
- ログレベルは環境変数 LOG_LEVEL または .env の設定で調整できます（デフォルト INFO）。

---

## 主要環境変数（要点）

（Settings クラスと config_setup の内容に基づく主要項目）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
  - paper_trading: 実環境 DB と分離してペーパートレードを行う
  - live: 本番（注意喚起が出ます）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使用する AI モジュールの API キー（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） — デフォルト INFO
- LOG_DIR: ログディレクトリ（デフォルト: logs）
- PID_FILE_PATH: Execution の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject、デフォルト instant）

必須の環境変数は validate_config により事前チェックできます。

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置されています。ここでは主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — （注文系監視ロジック）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込み・管理
    - monitoring_engine.py   — 各 Monitor を束ねる
    - alert_manager.py       — （LINE などのアラート送信管理）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py      — ブローカークライアント生成（実/Mock 切替）
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 注文株数決定・上限/丸め処理
    - risk_adjustment.py     — セクター制限・レジーム乗数
  - research/
    - factor_research.py     — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — レジーム判定（MA + マクロニュース）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## 運用上の注意 / ベストプラクティス

- .env は機密情報を含む可能性があるため絶対に VCS にコミットしないでください（config_setup でも注意書きあり）。
- KABUSYS_ENV を `live` に設定すると本番運用になります。LINE 通知や Kill Switch の設定を含め、慎重に設定を確認してください（validate_config が警告を出します）。
- run_monitoring は監視用 DB として sqlite_path（デフォルト data/monitoring.db）を使用します。paper_trading 環境でも監視は本番 sqlite_path を参照します（設計上の仕様）。
- run_execution は paper_trading 環境時に paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全に分離します。
- OpenAI を使う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API 呼び出しの失敗時はフェイルセーフ（スコアを 0 にフォールバックしたり処理をスキップ）する実装になっていますが、コストとレート制限に注意してください。
- ログディレクトリ・DB ファイルの所有者と権限を監査し、定期的にバックアップしてください。
- 停止操作:
  - 手動でプロセスを停止する場合は data/stop_requested.flag を作成すると run_* スクリプトが検知して安全に停止します。
  - KillSwitch（自動判定で作成される data/kill.flag）は慎重に扱ってください。KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動クリアされますが、本番では推奨されません。

---

README は以上です。追加で以下が必要であれば対応できます:
- 実際の requirements.txt / dockerfile / systemd サービスユニットの例
- run_execution/run_monitoring の systemd / supervisor 用のサンプルユニット
- 各モジュール（AI / Execution / Monitoring）の詳細ドキュメント（関数仕様・シーケンス図 等）

必要でしたらどれを優先するか教えてください。