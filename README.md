# KabuSys

日本株向け自動売買 / リサーチ基盤ライブラリ群。戦略の研究、ポートフォリオ構築、発注実行（本番・ペーパー）、および監視・アラート機能を含むモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を担う Python パッケージ群です。

- DuckDB / SQLite を用いた価格データ・財務データの集計・ファクター計算（research）
- 銘柄選定・配分・ポジションサイズ計算（portfolio）
- 発注エンジン（ExecutionEngine）と注文管理（実際のブローカー or MockBroker）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュース NLP / 市場レジーム判定（OpenAI を使用するモジュール）
- ペーパートレード検証レポート生成ツール 等

設計方針の特徴:
- 本番 DB と ペーパートレード DB を分離可能
- LLM 呼び出しはフェイルセーフ（失敗時にスコア 0 等で継続）
- ルックアヘッドバイアス対策（target_date を外部から与える、date.today() を直接参照しない等）
- ロギング、プロセス優先度設定、ポーリングループ等のユーティリティを標準化

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 起動前設定検証: python -m kabusys.validate_config

- 実行 / 発注
  - 実行エントリ: python -m kabusys.run_execution
  - 本番 / ペーパー切替（KABUSYS_ENV）
  - BrokerClientFactory による実ブローカー / MockBroker 分岐
  - RiskManager / Reconciler / OrderManager を含む ExecutionEngine

- 監視・運用
  - 実行プロセス監視 (SystemMonitor)
  - 注文滞留や約定異常監視 (TradeMonitor)
  - ドローダウン・ポジション上限監視 (RiskMonitor)
  - Kill Switch（data/kill.flag）で ExecutionEngine 停止
  - 監視エンジン起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）

- 研究・因子計算
  - ファクター計算: momentum / volatility / value（duckdb 経由）
  - 将来リターン計算、IC 計算、ファクター統計

- AI / NLP
  - ニュースのセンチメント算出（OpenAI）: kabusys.ai.score_news
  - 市場レジーム判定（MA200 + LLM）

- 運用ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## セットアップ

前提
- Python 3.10+（`from __future__ import annotations` を利用）
- DuckDB, psutil, openai 等の外部パッケージ

推奨インストール例（プロジェクトルートで実行）:
- requirements.txt が無い場合は最低限下記をインストールしてください。

pip install duckdb psutil openai

（必要に応じて PyYAML を入れると validate_config の YAML 検証が有効になります）
pip install pyyaml

初期設定:
1. プロジェクトルートに .env を作成する（.env.example を参考にするか、ウィザードを使用）
   - 対話式ウィザード:
     python -m kabusys.config_setup

2. 設定検証:
   python -m kabusys.validate_config
   - `--strict` を指定すると警告も失敗扱いになります。

データディレクトリ:
- デフォルトの DB / ファイルは `data/` 配下に作られます（必要に応じて環境変数で上書き）。
- 例:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

ログ:
- デフォルトは logs/<app_name>.log に日次ローテートで保存。
- 環境変数: LOG_DIR, LOG_LEVEL

注意:
- OpenAI を利用する機能（news_nlp / regime_detector）を使う場合は環境変数 OPENAI_API_KEY を設定してください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 推奨（自動クリアは危険）。

---

## 使い方（主要コマンド例）

1. 環境を作る / .env を用意する
   - 対話式:
     python -m kabusys.config_setup
   - 内容を確認・検証:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict

2. 監視プロセスの起動
   - デフォルトポーリング間隔 60 秒。環境変数で変更:
     export MONITOR_POLL_INTERVAL=30
   - 起動:
     python -m kabusys.run_monitoring
   - 停止:
     - run_monitoring は data/stop_requested.flag の存在を検知するとループを抜けます。
     - 監視から KillSwitch を書き込ませると ExecutionEngine に停止指示（data/kill.flag）を送ります。

3. 実行エンジンの起動（Execution）
   - KABUSYS_ENV によって挙動が変わります。
     - paper_trading: MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用
     - live / development: 本番 sqlite_path を使用
   - 起動:
     python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成すると run_execution は自動で停止を試みます。
     - KillSwitch が data/kill.flag を書き込むとエンジン側で停止処理が走ります。
   - PID ファイル: data/execution.pid（設定は Settings.pid_file_path で変更可能）

4. Paper Trading 検証レポート
   - 期間を指定してレポートを出力:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5. AI 関連（ニュース NLP / レジーム判定）
   - プログラムから直接呼ぶ:
     from kabusys.ai import score_news
     score_news(conn, target_date, api_key="...")

   - 環境変数 OPENAI_API_KEY を設定しておけば api_key を省略できます。
   - 失敗時はフェイルセーフ（スコア 0 等）で継続する設計です。

---

## 主要な環境変数（代表）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレードの約定挙動）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ出力先ディレクトリ
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

.env を作る際は必ずバイナリな機密情報（API トークン等）を適切に管理し、リポジトリにコミットしないでください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 全体の環境設定読み出しロジックを提供
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py           : ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py    : MA200 + LLM で市場レジーム判定
  - portfolio/
    - portfolio_builder.py  : 候補選定・重み（等重・スコア重み）
    - position_sizing.py    : 株数決定・キャップ・lot 単位丸め
    - risk_adjustment.py    : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    : momentum / volatility / value 等の計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC・統計
  - monitoring/
    - monitoring_db.py      : SQLite の schema 初期化・永続化 API（MonitoringDB）
    - system_monitor.py     : システム状態・データ鮮度チェック
    - risk_monitor.py       : ドローダウン・ポジション上限監視
    - trade_monitor.py      : （注文関連の監視、コードベースで参照あり）
    - monitoring_engine.py  : 各 Monitor を束ねる Polling Engine
    - kill_switch.py        : data/kill.flag 書込ロジック
    - alert_manager.py      : （アラート送信ロジック）
  - execution/
    - execution_engine.py   : ExecutionEngine（run_session 等）
    - broker_factory.py     : BrokerClientFactory（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/monitoring_db.py
  - tools/
    - paper_verification_report.py : Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py      : 共通ロギング設定（Stream + TimedRotatingFile）
    - process_priority.py   : プロセス優先度 / CPU affinity ユーティリティ

data/（実行時に利用するファイル・データ）
- data/kabusys.duckdb (デフォルト)
- data/monitoring.db (監視ログ SQLite)
- data/paper_trading.db (ペーパートレード用 SQLite)
- data/kill.flag (Kill Switch による Execution 停止指示)
- data/stop_requested.flag (運用用の停止フラグ—run_* スクリプトで参照)
- data/execution.pid (ExecutionEngine の PID ファイル)

logs/
- <app_name>.log（日次ローテート）

---

## 運用上の注意・ヒント

- 監視（monitoring）は常に本番の sqlite_path を使って監視テーブルに書き込みます（KABUSYS_ENV に依存しません）。これにより監視ログは環境にかかわらず一元化されます。
- 実行エンジンは KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使い、実 DB とは分離されます。
- Kill Switch は監視が発火させることで data/kill.flag に理由を書き込みます。ExecutionEngine は起動時・実行中にこのフラグを検出して安全停止します。
- MONITOR_POLL_INTERVAL の値は正の整数にしてください。不正値はデフォルト（60 秒）にフォールバックされます。
- OpenAI API 呼び出しを行うコードはリトライ / バックオフ、レスポンス検証を行う設計です。ただし API キー漏洩等には注意してください。
- ログディレクトリの作成に失敗した場合、ファイル出力はスキップされコンソール出力のみとなります。LOG_DIR の書き込み権限を確認してください。
- DB マイグレーションが一部自動で行われます（例: monitoring_db が新列を必要とする場合の ALTER）。運用前にバックアップを推奨します。

---

## さらに詳しく / 開発者向け

- DuckDB を用いたファクター処理は、prices_daily / raw_financials 等のテーブルを前提としています。データ投入スクリプトは別途用意してください。
- テストや CI を組む場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- LLM 呼び出し部分をモックしたい場合は、該当モジュール内の API 呼び出しラッパー（_call_openai_api 等）をパッチしてください（ユニットテスト設計を想定しています）。

---

問題や補足してほしい箇所があれば教えてください。README をプロジェクトの慣習（追加の実行スクリプト、requirements.txt、デプロイ手順等）に合わせて調整できます。